"""D-12 et fenêtres C05, sans lecture réelle ni déduction d'un fuseau serveur."""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import re

from xpbots.fondamental.c0_types import (Annonce, ErreurFondamental, TableImportance, VersionCalendrier,
    decoder_json_strict, devises_pour, entier, instant, millisecondes)
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import DecisionFondamentale, Motif

_CLES = frozenset({'schema', 'version', 'export_serveur', 'export_gmt', 'fenetre_debut_serveur',
    'fenetre_fin_serveur', 'evenements'})
_EVENEMENT = frozenset({'id_valeur', 'id_evenement', 'code', 'nom', 'devise', 'importance',
    'type', 'secteur', 'heure_serveur', 'revision'})
_HEURE = re.compile(r'[0-9]{4}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}')


def _heure(texte):
    if type(texte) is not str or _HEURE.fullmatch(texte) is None:
        raise ErreurFondamental('heure native invalide')
    return datetime.strptime(texte, '%Y.%m.%d %H:%M:%S')


def _identite(annonce):
    return replace(annonce, known_at_ms=0)


@dataclass(frozen=True)
class EtatCalendrier:
    versions: tuple[VersionCalendrier, ...] = ()

    def __post_init__(self):
        try:
            versions = tuple(self.versions)
        except TypeError as erreur:
            raise ErreurFondamental('collection de versions requise') from erreur
        if any(not isinstance(v, VersionCalendrier) for v in versions):
            raise ErreurFondamental('versions réelles requises')
        object.__setattr__(self, 'versions', versions)


@dataclass(frozen=True)
class ReceptionCalendrier:
    acceptee: bool
    ignoree: bool
    raison: str | None = None
    version: VersionCalendrier | None = None

    def __post_init__(self):
        if type(self.acceptee) is not bool or type(self.ignoree) is not bool or self.acceptee and self.ignoree:
            raise ErreurFondamental('résultat de réception incohérent')
        if self.acceptee or self.ignoree:
            if not isinstance(self.version, VersionCalendrier) or self.raison is not None:
                raise ErreurFondamental('version acceptée ou relue requise')
        elif type(self.raison) is not str or not self.raison or self.version is not None:
            raise ErreurFondamental('raison de rejet requise')


class GardeAnnonces:
    def __init__(self, commun, convertir_serveur, etat=None):
        if not isinstance(commun, ParametresCommuns) or not callable(convertir_serveur):
            raise ErreurFondamental('paramètres et conversion serveur explicite requis')
        if etat is not None and not isinstance(etat, EtatCalendrier):
            raise ErreurFondamental('état calendrier réel requis')
        self._commun = commun
        self._convertir = convertir_serveur
        self._etat = etat if etat is not None else EtatCalendrier()
        precedent = None
        for v in self._etat.versions:
            self._verifier_histoire(v, precedent)
            precedent = v

    @property
    def etat(self):
        return self._etat

    def _verifier_histoire(self, version, precedente):
        if precedente is not None and (version.version <= precedente.version
                or version.reception_ms < precedente.reception_ms or version.export_ms < precedente.export_ms):
            raise ErreurFondamental('historique de calendrier en recul')
        anciennes = {a.id_valeur: a for a in precedente.annonces} if precedente is not None else {}
        meme_source = precedente is not None and precedente.table.fournisseur == version.table.fournisseur
        for a in version.annonces:
            if a.importance not in version.table.hautes or not version.couverture.debut_ms <= a.instant_ms < version.couverture.fin_ms:
                raise ErreurFondamental('annonce hors couverture ou importance haute non qualifiée')
            ancienne = anciennes.get(a.id_valeur)
            connue = (ancienne.known_at_ms if meme_source and ancienne is not None and _identite(ancienne) == _identite(a)
                      else version.reception_ms)
            if a.known_at_ms != connue:
                raise ErreurFondamental('heure de connaissance incohérente')

    def _serveur(self, valeur):
        _heure(valeur)
        return instant(self._convertir(valeur))

    def _decoder(self, octets, reception_ms, table, precedente):
        if not isinstance(table, TableImportance):
            raise ErreurFondamental('table d’importance versionnée requise')
        p = decoder_json_strict(octets)
        if set(p) != _CLES or p['schema'] != 'xp-export-calendrier-v1' or type(p['evenements']) is not list:
            raise ErreurFondamental('format xp-export-calendrier-v1 invalide')
        version = entier(p['version'], 1)
        export = instant_depuis_datetime(_heure(p['export_gmt']).replace(tzinfo=timezone.utc))
        if self._serveur(p['export_serveur']) != export:
            raise ErreurFondamental('conversion serveur et GMT contradictoires')
        couverture = Intervalle(self._serveur(p['fenetre_debut_serveur']), self._serveur(p['fenetre_fin_serveur']))
        anciennes = {a.id_valeur: a for a in precedente.annonces} if precedente is not None else {}
        meme_source = precedente is not None and precedente.table.fournisseur == table.fournisseur
        annonces = []
        for e in p['evenements']:
            if type(e) is not dict or set(e) != _EVENEMENT:
                raise ErreurFondamental('champs natifs d’événement invalides')
            a = Annonce(e['id_valeur'], e['id_evenement'], e['code'], e['nom'], e['devise'],
                e['importance'], e['type'], e['secteur'], e['heure_serveur'], self._serveur(e['heure_serveur']),
                e['revision'], reception_ms)
            ancienne = anciennes.get(a.id_valeur)
            if meme_source and ancienne is not None and _identite(ancienne) == _identite(a):
                a = replace(a, known_at_ms=ancienne.known_at_ms)
            annonces.append(a)
        empreinte = hashlib.sha256(json.dumps(p, ensure_ascii=False, sort_keys=True,
            separators=(',', ':')).encode('utf-8')).hexdigest()
        return VersionCalendrier(version, export, reception_ms, couverture, tuple(annonces), table, empreinte)

    def recevoir(self, octets, reception_ms, table):
        instant(reception_ms)
        precedente = self._etat.versions[-1] if self._etat.versions else None
        if precedente is not None and reception_ms < precedente.reception_ms:
            return ReceptionCalendrier(False, False, 'RECEPTION_EN_RECUL')
        try:
            v = self._decoder(octets, reception_ms, table, precedente)
            if precedente is not None:
                if v.version < precedente.version:
                    return ReceptionCalendrier(False, False, 'VERSION_ANTERIEURE')
                if v.version == precedente.version:
                    if v.empreinte == precedente.empreinte and v.table == precedente.table:
                        return ReceptionCalendrier(False, True, version=precedente)
                    return ReceptionCalendrier(False, False, 'VERSION_REECRITE')
            self._verifier_histoire(v, precedente)
        except Exception:
            return ReceptionCalendrier(False, False, 'INVALIDE')
        self._etat = EtatCalendrier(self._etat.versions + (v,))
        return ReceptionCalendrier(True, False, version=v)

    def version_connue(self, instant_ms):
        instant(instant_ms)
        return next((v for v in reversed(self._etat.versions) if v.reception_ms <= instant_ms), None)

    def _fenetre(self, a):
        return (a.instant_ms - millisecondes(self._commun.news_before_seconds),
                a.instant_ms + millisecondes(self._commun.news_after_seconds))

    def evaluer(self, symbole, instant_ms):
        devises = devises_pour(symbole)
        v = self.version_connue(instant_ms)
        if v is None:
            return DecisionFondamentale(False, Motif.NEWS_WINDOW, 'CALENDRIER_PERIME')
        if any(a.devise in devises and a.known_at_ms <= instant_ms and self._fenetre(a)[0] <= instant_ms < self._fenetre(a)[1]
               for a in v.annonces):
            return DecisionFondamentale(False, Motif.NEWS_WINDOW, 'ANNONCE_HIGH', True)
        age = millisecondes(self._commun.news_calendar_max_age_seconds)
        if instant_ms - v.export_ms > age or instant_ms - v.reception_ms > age:
            return DecisionFondamentale(False, Motif.NEWS_WINDOW, 'CALENDRIER_PERIME')
        if (v.couverture.debut_ms > instant_ms
                or v.couverture.fin_ms < instant_ms + millisecondes(self._commun.news_forward_coverage_seconds)):
            return DecisionFondamentale(False, Motif.NEWS_WINDOW, 'COUVERTURE_INSUFFISANTE')
        return DecisionFondamentale(True)

    def prochaine_echeance_ms(self, instant_ms):
        v = self.version_connue(instant_ms)
        if v is None:
            return None
        age = millisecondes(self._commun.news_calendar_max_age_seconds)
        horizon = millisecondes(self._commun.news_forward_coverage_seconds)
        dates = [v.export_ms + age + 1, v.reception_ms + age + 1, v.couverture.debut_ms,
                 v.couverture.fin_ms - horizon + 1]
        devises = {d for s in self._commun.universe_priority for d in devises_pour(s)}
        dates.extend(t for a in v.annonces if a.devise in devises and a.known_at_ms <= instant_ms for t in self._fenetre(a))
        return min((t for t in dates if t > instant_ms), default=None)
