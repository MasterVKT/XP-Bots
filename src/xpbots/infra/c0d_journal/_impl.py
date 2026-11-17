"""Projection JSONL du dépôt durable ; reprise atomique et delta en marche."""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import json
import os
import sys
from xpbots.noyau.c2_journal import serialiser, Enveloppe, enregistrement, VERSION_SCHEMA

_MODE_DOUBLE_COMPTE = 'PAPER_AB'  # Variante de l'enveloppe, pas un mode par défaut.


def _paires(ps):
    r = {}
    for k, v in ps:
        if k in r:
            raise ValueError('clé JSON en double')
        r[k] = v
    return r


def _interdit(_):
    raise ValueError('nombre JSON non fini')


def _decoder(b):
    if type(b) is not bytes:
        raise ValueError('octets requis')
    return json.loads(b.decode('utf-8'), object_pairs_hook=_paires, parse_constant=_interdit)


def _encoder(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _canonique(b):
    if _encoder(_decoder(b)) != b:
        raise ValueError('JSON canonique requis')
    return b


def lire_octets(chemin, max_octets):
    if type(max_octets) is not int or max_octets <= 0:
        raise ValueError('plafond de lecture requis')
    with Path(chemin).open('rb') as f:
        b = f.read(max_octets+1)
    if len(b) > max_octets:
        raise ValueError('fichier trop grand')
    return b


def lire_json(chemin, max_octets):
    return _decoder(lire_octets(chemin, max_octets))


def ecrire_atomique(chemin, octets):
    if type(octets) is not bytes:
        raise ValueError('octets requis')
    p = Path(chemin)
    p.parent.mkdir(parents=True, exist_ok=True)
    temporaire = p.with_name(p.name+'.tmp')
    with temporaire.open('wb') as f:
        f.write(octets)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporaire, p)


def ecrire_json(chemin, document):
    ecrire_atomique(chemin, _encoder(document))


def alerter(code, detail):
    if type(code) is not str or type(detail) is not str:
        raise ValueError('alerte textuelle requise')
    # Le consommateur fournit des descriptions statiques ; aucun objet SDK brut.
    print(_encoder({'code': code, 'detail': detail}).decode('utf-8'), file=sys.stderr, flush=True)


def _nom(v):
    if (type(v) is not str or not v or v in ('.', '..') or v[-1] in ('.', ' ')
            or any(c in v for c in '/\\:\x00<>|?*"')):
        raise ValueError('identifiant de déploiement sûr requis')
    return v


class JournalFichiers:
    def __init__(self, racine, deploiement):
        self.deploiement = _nom(deploiement)
        self.dossier = Path(racine)/'logs'/self.deploiement
        self._dernier = 0
        self._empreintes = {}
        self._reparation_requise = False

    def _valider(self, e):
        n, t, decisions, entrees = e
        if type(n) is not int or n <= 0 or type(t) is not int or t < 0:
            raise ValueError('événement daté et numéroté requis')
        decisions, entrees = tuple(decisions), tuple(entrees)
        for b in decisions:
            d = _decoder(_canonique(b))
            cles = ('deploiement', 'bras', 'mode', 'instant_utc_ms', 'numero', 'empreinte_regles')
            if (type(d) is not dict or not set(cles+('type', 'version_schema')).issubset(d)
                    or d['version_schema'] != VERSION_SCHEMA):
                raise ValueError('enveloppe C09 requise')
            e = Enveloppe(**{k: d[k] for k in cles})
            if not (e.deploiement == self.deploiement or e.mode == _MODE_DOUBLE_COMPTE
                    and e.deploiement == self.deploiement+':'+e.bras):
                raise ValueError('enveloppe C09 d un autre deploiement')
            contenu = {k: v for k, v in d.items() if k not in cles+('type', 'version_schema')}
            if serialiser(enregistrement(d['type'], e, contenu)).encode('utf-8') != b:
                raise ValueError('enregistrement C09 invalide')
        for b in entrees:
            d = _decoder(_canonique(b))
            if type(d) is not dict or set(d) != {'numero', 'instant_reception_utc_ms', 'type_evenement', 'contenu'}:
                raise ValueError('enveloppe du journal d’entrées requise')
            if (type(d['numero']) is not int or d['numero'] <= 0
                    or type(d['instant_reception_utc_ms']) is not int or d['instant_reception_utc_ms'] != t
                    or type(d['type_evenement']) is not str or not d['type_evenement']):
                raise ValueError('entrée non datée ou non numérotée')
        jour = (datetime(1970, 1, 1, tzinfo=timezone.utc)+timedelta(milliseconds=t)).date().isoformat()
        empreinte = hashlib.sha256(_encoder([n, t, [b.hex() for b in decisions], [b.hex() for b in entrees]])).hexdigest()
        return n, jour, decisions, entrees, empreinte

    def publier(self, evenements):
        # Réparation de démarrage seulement ; les append en marche restent bornés.
        fichiers = {}
        empreintes = {}
        dernier = 0
        for evenement in evenements:
            n, jour, ds, es, h = self._valider(evenement)
            if n != dernier+1:
                raise ValueError('journal durable non successif')
            for prefixe, valeurs in (('decisions', ds), ('entrees', es)):
                chemin = self.dossier/(prefixe+'_'+jour+'.jsonl')
                fichiers.setdefault(chemin, bytearray()).extend(b''.join(b+b'\n' for b in valeurs))
            empreintes[n] = h
            dernier = n
        self._reparation_requise = True
        for chemin, contenu in fichiers.items():
            ecrire_atomique(chemin, bytes(contenu))
        self._empreintes = empreintes
        self._dernier = dernier
        self._reparation_requise = False

    def ajouter(self, evenements):
        if self._reparation_requise:
            raise ValueError('réparation du journal depuis SQLite requise')
        valeurs = [self._valider(e) for e in evenements]
        dernier = self._dernier
        for n, _, _, _, h in valeurs:
            if n <= dernier:
                if self._empreintes.get(n) != h:
                    raise ValueError('répétition différente du journal')
            elif n != dernier+1:
                raise ValueError('trou dans le journal physique')
            else:
                dernier = n
        self.dossier.mkdir(parents=True, exist_ok=True)
        try:
            for n, jour, ds, es, h in valeurs:
                if n <= self._dernier:
                    continue
                for prefixe, lignes in (('decisions', ds), ('entrees', es)):
                    with (self.dossier/(prefixe+'_'+jour+'.jsonl')).open('ab') as f:
                        for b in lignes:
                            f.write(b+b'\n')
                        f.flush()
                        os.fsync(f.fileno())
                self._empreintes[n] = h
                self._dernier = n
        except OSError:
            self._reparation_requise = True
            raise

    def decisions(self, enregistrements):
        return tuple(serialiser(e).encode('utf-8') for e in enregistrements)
