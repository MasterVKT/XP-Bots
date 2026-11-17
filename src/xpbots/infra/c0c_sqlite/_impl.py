"""Durabilité C08 : transaction unique et journal autoritaire pour la reprise."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import sqlite3


def _json(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _paires(ps):
    r = {}
    for k, v in ps:
        if k in r:
            raise ValueError('clé JSON en double')
        r[k] = v
    return r


def _canonique(b):
    if type(b) is not bytes:
        raise ValueError('octets JSON requis')
    def interdit(_):
        raise ValueError('nombre JSON non fini')
    v = json.loads(b.decode('utf-8'), object_pairs_hook=_paires, parse_constant=interdit)
    if _json(v) != b:
        raise ValueError('JSON canonique requis')
    return b


def _naturel(v):
    if type(v) is not int or v < 0:
        raise ValueError('entier naturel requis')
    return v


def _texte(v):
    if type(v) is not str or not v.strip():
        raise ValueError('texte non vide requis')
    return v


class DepotSQLite:
    def __init__(self, chemin, meta):
        if type(meta) is not dict or not meta:
            raise ValueError('métadonnées de déploiement requises')
        contenu = _json(dict(schema='xp-etat-sqlite-v1', deploiement=meta))
        self.chemin = Path(chemin)
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.connexion = sqlite3.connect(self.chemin, timeout=1, isolation_level=None)
        try:
            self.connexion.execute('PRAGMA journal_mode=WAL')
            self.connexion.execute('PRAGMA synchronous=FULL')
            self.connexion.execute('PRAGMA foreign_keys=ON')
            self.connexion.executescript('''
CREATE TABLE IF NOT EXISTS meta(cle TEXT PRIMARY KEY, valeur BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS etat(espace TEXT NOT NULL, cle TEXT NOT NULL, valeur BLOB NOT NULL, instant INTEGER NOT NULL, PRIMARY KEY(espace,cle));
CREATE TABLE IF NOT EXISTS evenements(numero INTEGER PRIMARY KEY, instant INTEGER NOT NULL, empreinte TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entrees(numero INTEGER PRIMARY KEY, evenement INTEGER NOT NULL REFERENCES evenements(numero), valeur BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS decisions(evenement INTEGER NOT NULL REFERENCES evenements(numero), ordinal INTEGER NOT NULL, valeur BLOB NOT NULL, PRIMARY KEY(evenement,ordinal));
CREATE TABLE IF NOT EXISTS intentions(cle TEXT PRIMARY KEY, etat TEXT NOT NULL, contenu BLOB NOT NULL, instant INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS reservations(cle TEXT PRIMARY KEY, risque TEXT NOT NULL, volume TEXT NOT NULL, instant INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS arrets(bras TEXT NOT NULL, type TEXT NOT NULL, actif INTEGER NOT NULL, depuis INTEGER NOT NULL, decision BLOB, PRIMARY KEY(bras,type));
''')
            self.connexion.execute('BEGIN IMMEDIATE')
            ancien = self.connexion.execute("SELECT valeur FROM meta WHERE cle='identite'").fetchone()
            if ancien is None:
                if self.connexion.execute('SELECT COUNT(*) FROM evenements').fetchone()[0]:
                    raise ValueError('métadonnées absentes d’une base non vide')
                self.connexion.execute("INSERT INTO meta VALUES('identite',?)", (contenu,))
            elif ancien[0] != contenu:
                raise ValueError('métadonnées incompatibles : reprise refusée')
            self.connexion.execute('COMMIT')
        except BaseException:
            if self.connexion.in_transaction:
                self.connexion.execute('ROLLBACK')
            self.connexion.close()
            raise

    @property
    def dernier_numero(self):
        return self.connexion.execute('SELECT COALESCE(MAX(numero),0) FROM evenements').fetchone()[0]

    def charger(self):
        r = self.connexion.execute("SELECT valeur FROM etat WHERE espace='session' AND cle='courant'").fetchone()
        return None if r is None else _canonique(r[0])

    def entrees(self):
        return tuple(_canonique(r[0]) for r in self.connexion.execute('SELECT valeur FROM entrees ORDER BY numero'))

    def evenements(self):
        resultat = []
        for n, t in self.connexion.execute('SELECT numero,instant FROM evenements ORDER BY numero'):
            d = tuple(_canonique(r[0]) for r in self.connexion.execute('SELECT valeur FROM decisions WHERE evenement=? ORDER BY ordinal', (n,)))
            e = tuple(_canonique(r[0]) for r in self.connexion.execute('SELECT valeur FROM entrees WHERE evenement=? ORDER BY numero', (n,)))
            resultat.append((n, t, d, e))
        return tuple(resultat)

    def arrets(self):
        return tuple((b, t, bool(a), depuis, None if d is None else json.loads(d))
                     for b, t, a, depuis, d in self.connexion.execute('SELECT bras,type,actif,depuis,decision FROM arrets ORDER BY bras,type'))

    def persister(self, numero, instant_ms, etat, *, entrees=(), decisions=(), intentions=(), reservations=(), arrets=()):
        _naturel(numero); _naturel(instant_ms); _canonique(etat)
        if numero == 0:
            raise ValueError('numérotation des événements à partir de un')
        entrees = tuple((_naturel(n), _canonique(b)) for n, b in entrees)
        decisions = tuple(_canonique(b) for b in decisions)
        intentions = tuple((_texte(c), _texte(s), _canonique(b)) for c, s, b in intentions)
        reserves = []
        for cle, risque, volume in reservations:
            _texte(cle)
            if any(not isinstance(v, Decimal) or not v.is_finite() or v < 0 for v in (risque, volume)):
                raise ValueError('réservation décimale finie positive ou nulle requise')
            reserves.append((cle, str(risque), str(volume)))
        arr = []
        for bras, nature, actif, decision in arrets:
            _texte(bras); _texte(nature)
            if type(actif) is not bool:
                raise ValueError('arrêt booléen requis')
            if decision is not None:
                if (type(decision) is not dict or set(decision) != {'decision_id', 'instant_utc_ms', 'motif'}
                        or _naturel(decision['instant_utc_ms']) > instant_ms):
                    raise ValueError('décision datée requise')
                _texte(decision['decision_id']); _texte(decision['motif'])
            arr.append((bras, nature, actif, None if decision is None else _json(decision)))
        preuve = _json([numero, instant_ms, etat.hex(), [(n, b.hex()) for n, b in entrees],
                        [b.hex() for b in decisions], [(c, s, b.hex()) for c, s, b in intentions],
                        reserves, [(b, t, a, None if d is None else d.hex()) for b, t, a, d in arr]])
        empreinte = hashlib.sha256(preuve).hexdigest()
        self.connexion.execute('BEGIN IMMEDIATE')
        try:
            deja = self.connexion.execute('SELECT empreinte FROM evenements WHERE numero=?', (numero,)).fetchone()
            if deja is not None:
                if deja[0] != empreinte:
                    raise ValueError('répétition différente d’un événement durable')
                self.connexion.execute('COMMIT')
                return numero
            if numero != self.dernier_numero+1:
                raise ValueError('trou dans le journal durable')
            dernier_entree = self.connexion.execute('SELECT COALESCE(MAX(numero),0) FROM entrees').fetchone()[0]
            if tuple(n for n, _ in entrees) != tuple(range(dernier_entree+1, dernier_entree+1+len(entrees))):
                raise ValueError('delta d’entrées non successif')
            self.connexion.execute('INSERT INTO evenements VALUES(?,?,?)', (numero, instant_ms, empreinte))
            self.connexion.execute("INSERT OR REPLACE INTO etat VALUES('session','courant',?,?)", (etat, instant_ms))
            self.connexion.executemany('INSERT INTO entrees VALUES(?,?,?)', ((n, numero, b) for n, b in entrees))
            self.connexion.executemany('INSERT INTO decisions VALUES(?,?,?)', ((numero, i, b) for i, b in enumerate(decisions)))
            self.connexion.executemany('INSERT OR REPLACE INTO intentions VALUES(?,?,?,?)', ((c, s, b, instant_ms) for c, s, b in intentions))
            self.connexion.execute('DELETE FROM reservations')
            self.connexion.executemany('INSERT INTO reservations VALUES(?,?,?,?)', ((c, r, v, instant_ms) for c, r, v in reserves))
            for bras, nature, actif, decision in arr:
                ancien = self.connexion.execute('SELECT actif,depuis FROM arrets WHERE bras=? AND type=?', (bras, nature)).fetchone()
                if ancien is not None and ancien[0] and not actif and decision is None:
                    raise ValueError('arrêt persistant : décision de reprise requise')
                depuis = ancien[1] if ancien is not None and bool(ancien[0]) == actif else instant_ms
                self.connexion.execute('INSERT OR REPLACE INTO arrets VALUES(?,?,?,?,?)', (bras, nature, int(actif), depuis, decision))
            self.connexion.execute('COMMIT')
        except BaseException:
            if self.connexion.in_transaction:
                self.connexion.execute('ROLLBACK')
            raise
        return numero

    def fermer(self):
        self.connexion.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fermer()
