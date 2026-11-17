"""Valeurs de la frontière native ; aucune horloge ni accès au terminal."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import operator
from typing import Protocol, Any
from xpbots.noyau.c0a_temps import verifier_instant, instant_depuis_iso


class ErreurInfra(ValueError):
    """Contrat physique incomplet : ENVIRONMENT_NOT_READY."""


class ErreurNative(ErreurInfra):
    def __init__(self, fonction, code):
        self.fonction = fonction
        self.code = entier_natif(code)
        super().__init__('ENVIRONMENT_NOT_READY '+fonction+' code='+str(self.code))


def _instant(v):
    try:
        return verifier_instant(v)
    except ValueError as e:
        raise ErreurInfra('instant natif hors contrat') from e


def entier_natif(v):
    if isinstance(v, bool) or getattr(getattr(v, 'dtype', None), 'kind', None) == 'b':
        raise ErreurInfra('entier natif requis')
    try:
        return operator.index(v)
    except TypeError as e:
        raise ErreurInfra('entier natif requis') from e


def nombre_decimal(v):
    if isinstance(v, (str, bytes, bool)) or getattr(getattr(v, 'dtype', None), 'kind', None) == 'b':
        raise ErreurInfra('nombre natif requis')
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ErreurInfra('nombre natif illisible') from e
    if not d.is_finite():
        raise ErreurInfra('nombre natif non fini')
    return d


def champ_natif(objet, nom):
    noms = getattr(getattr(objet, 'dtype', None), 'names', None)
    if isinstance(noms, tuple) and nom in noms:
        try:
            return objet[nom]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ErreurInfra('champ natif absent : '+nom) from e
    try:
        return getattr(objet, nom)
    except AttributeError:
        try:
            return objet[nom]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise ErreurInfra('champ natif absent : '+nom) from e


@dataclass(frozen=True)
class SegmentServeur:
    debut_utc_ms: int
    fin_utc_ms: int
    decalage_secondes: int

    def __post_init__(self):
        _instant(self.debut_utc_ms)
        _instant(self.fin_utc_ms)
        if self.fin_utc_ms <= self.debut_utc_ms or type(self.decalage_secondes) is not int:
            raise ErreurInfra('segment serveur invalide')


@dataclass(frozen=True)
class TableHeureServeur:
    serveur: str
    version: int
    date_releve: str
    mesures: tuple
    segments: tuple

    def __post_init__(self):
        if type(self.serveur) is not str or not self.serveur.strip() or type(self.version) is not int or self.version <= 0:
            raise ErreurInfra('serveur et version qualifiés requis')
        try:
            instant_depuis_iso(self.date_releve)
        except ValueError as e:
            raise ErreurInfra('date du relevé invalide') from e
        if not isinstance(self.mesures, (tuple, list)) or not isinstance(self.segments, (tuple, list)):
            raise ErreurInfra('mesures et segments explicites requis')
        mesures, segments = tuple(self.mesures), tuple(self.segments)
        if not mesures or any(type(m) is not str or not m.strip() for m in mesures):
            raise ErreurInfra('mesures S01 explicites requises')
        if (not segments or any(not isinstance(s, SegmentServeur) for s in segments)
                or any(b.debut_utc_ms < a.fin_utc_ms for a, b in zip(segments, segments[1:]))):
            raise ErreurInfra('segments UTC non ordonnés ou chevauchants')
        object.__setattr__(self, 'mesures', mesures)
        object.__setattr__(self, 'segments', segments)

    def utc_de_serveur(self, ms):
        _instant(ms)
        candidats = tuple(ms-s.decalage_secondes*1000 for s in self.segments
                          if s.debut_utc_ms <= ms-s.decalage_secondes*1000 < s.fin_utc_ms)
        if len(candidats) != 1:
            raise ErreurInfra('ENVIRONMENT_NOT_READY conversion serveur absente ou ambiguë')
        return candidats[0]

    def serveur_de_utc(self, ms):
        _instant(ms)
        for s in self.segments:
            if s.debut_utc_ms <= ms < s.fin_utc_ms:
                return ms+s.decalage_secondes*1000
        raise ErreurInfra('ENVIRONMENT_NOT_READY heure UTC hors table')

    @classmethod
    def depuis_document(cls, d):
        if type(d) is not dict or set(d) != {'schema', 'serveur', 'version', 'date_releve', 'mesures', 'segments'} or d['schema'] != 'xp-heure-serveur-v1':
            raise ErreurInfra('document de conversion invalide')
        if type(d['segments']) is not list or type(d['mesures']) is not list:
            raise ErreurInfra('liste de segments requise')
        segments = []
        for s in d['segments']:
            if type(s) is not dict or set(s) != {'debut_utc', 'fin_utc', 'decalage_secondes'}:
                raise ErreurInfra('champs de segment invalides')
            segments.append(SegmentServeur(instant_depuis_iso(s['debut_utc']), instant_depuis_iso(s['fin_utc']), s['decalage_secondes']))
        return cls(d['serveur'], d['version'], d['date_releve'], d['mesures'], tuple(segments))


class ProtocoleMT5(Protocol):
    """Surface utilisée ; constantes et structures restent celles de l’objet injecté."""
    __version__: str
    def initialize(self, *args, **kwargs) -> bool: ...
    def shutdown(self) -> None: ...
    def version(self) -> Any: ...
    def last_error(self) -> Any: ...
    def account_info(self) -> Any: ...
    def terminal_info(self) -> Any: ...
    def symbols_get(self, *args, **kwargs) -> Any: ...
    def symbol_select(self, symbol, enable) -> bool: ...
    def symbol_info(self, symbol) -> Any: ...
    def symbol_info_tick(self, symbol) -> Any: ...
    def copy_ticks_from(self, symbol, date_from, count, flags) -> Any: ...
    def copy_ticks_range(self, symbol, date_from, date_to, flags) -> Any: ...
    def order_calc_profit(self, action, symbol, volume, price_open, price_close) -> Any: ...
    def order_calc_margin(self, action, symbol, volume, price) -> Any: ...
    def order_check(self, request) -> Any: ...
    def order_send(self, request) -> Any: ...
    def positions_get(self, *args, **kwargs) -> Any: ...
    def orders_get(self, *args, **kwargs) -> Any: ...
    def history_orders_get(self, *args, **kwargs) -> Any: ...
    def history_deals_get(self, *args, **kwargs) -> Any: ...
