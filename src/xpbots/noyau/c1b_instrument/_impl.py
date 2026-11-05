"""Implémentation de la couche 1b (instrument). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping

from xpbots.noyau.c0a_temps import ErreurInstant, verifier_instant
from xpbots.noyau.c0b_nombres import ErreurNombre, decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns


class ErreurInstrument(ValueError):
    """Horaires, champs ou question sur un profil refusés."""


class _Invalide(Exception):
    """Valeur d'un champ refusée (convertie en champ non prêt)."""


@dataclass(frozen=True, order=True)
class Intervalle:
    debut_ms: int
    fin_ms: int

    def __post_init__(self) -> None:
        try:
            verifier_instant(self.debut_ms)
            verifier_instant(self.fin_ms)
        except ErreurInstant as erreur:
            raise ErreurInstrument(f'intervalle : {erreur}') from erreur
        if self.fin_ms <= self.debut_ms:
            raise ErreurInstrument('intervalle vide ou inversé')


def _sans_chevauchement(intervalles: tuple[Intervalle, ...], nom: str) -> None:
    if not all(isinstance(i, Intervalle) for i in intervalles):
        raise ErreurInstrument(f'{nom} : intervalles attendus')
    for precedent, suivant in zip(intervalles, intervalles[1:]):
        if suivant.debut_ms < precedent.fin_ms:
            raise ErreurInstrument(f'{nom} : intervalles non triés ou chevauchants')


def _soustraire(seances: tuple[Intervalle, ...], fermetures: tuple[Intervalle, ...],
                debut: int, fin: int) -> tuple[Intervalle, ...]:
    morceaux = [(max(s.debut_ms, debut), min(s.fin_ms, fin)) for s in seances]
    for fermeture in fermetures:
        decoupes = []
        for a, b in morceaux:
            if fermeture.fin_ms <= a or fermeture.debut_ms >= b:
                decoupes.append((a, b))
                continue
            if a < fermeture.debut_ms:
                decoupes.append((a, fermeture.debut_ms))
            if fermeture.fin_ms < b:
                decoupes.append((fermeture.fin_ms, b))
        morceaux = decoupes
    return tuple(Intervalle(a, b) for a, b in morceaux if b > a)


@dataclass(frozen=True)
class HorairesCotation:
    seances: tuple[Intervalle, ...]
    fermetures: tuple[Intervalle, ...]
    debut_validite_ms: int
    fin_validite_ms: int

    def __post_init__(self) -> None:
        object.__setattr__(self, 'seances', tuple(self.seances))
        object.__setattr__(self, 'fermetures', tuple(self.fermetures))
        _sans_chevauchement(self.seances, 'séances')
        _sans_chevauchement(self.fermetures, 'fermetures')
        Intervalle(self.debut_validite_ms, self.fin_validite_ms)
        object.__setattr__(self, '_effectives', _soustraire(self.seances, self.fermetures, self.debut_validite_ms,
                                                            self.fin_validite_ms))

    def _verifier(self, instant_ms: int) -> int:
        try:
            verifier_instant(instant_ms)
        except ErreurInstant as erreur:
            raise ErreurInstrument(str(erreur)) from erreur
        if not self.debut_validite_ms <= instant_ms < self.fin_validite_ms:
            raise ErreurInstrument('instant hors de la période de validité des horaires')
        return instant_ms

    def _seance_en_cours(self, instant_ms: int) -> Intervalle | None:
        self._verifier(instant_ms)
        return next((i for i in self._effectives if i.debut_ms <= instant_ms < i.fin_ms), None)

    def ouvert_a(self, instant_ms: int) -> bool:
        return self._seance_en_cours(instant_ms) is not None

    def prochaine_fermeture_apres(self, instant_ms: int) -> int | None:
        seance = self._seance_en_cours(instant_ms)
        if seance is None:
            return None
        if seance.fin_ms >= self.fin_validite_ms:
            raise ErreurInstrument('heure de fermeture inconnue au-delà de la période de validité')
        return seance.fin_ms


# ---------------------------------------------------------------- convertisseurs de champs

def _texte(v):
    if not isinstance(v, str) or not v:
        raise _Invalide
    return v


def _decimal(minimum: Decimal | None, strict: bool = False) -> Callable[[Any], Decimal]:
    def convertir(v):
        try:
            d = decimal_depuis(v)
        except ErreurNombre as erreur:
            raise _Invalide from erreur
        if minimum is not None and (d <= minimum if strict else d < minimum):
            raise _Invalide
        return d
    return convertir


def _entier(minimum: int) -> Callable[[Any], int]:
    def convertir(v):
        if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
            raise _Invalide
        return v
    return convertir


def _booleen(v):
    if not isinstance(v, bool):
        raise _Invalide
    return v


def _modes(v):
    if isinstance(v, (str, bytes)) or not hasattr(v, '__iter__'):
        raise _Invalide
    modes = frozenset(v)
    if not modes or not all(isinstance(m, str) and m for m in modes):
        raise _Invalide
    return modes


def _horaires(v):
    if not isinstance(v, HorairesCotation):
        raise _Invalide
    return v


def _instant(v):
    try:
        return verifier_instant(v)
    except ErreurInstant as erreur:
        raise _Invalide from erreur


_ZERO = Decimal(0)
_POSITIF, _NATUREL, _RELATIF = _decimal(_ZERO, strict=True), _decimal(_ZERO), _decimal(None)

_SPEC_INSTRUMENT: dict[str, Callable[[Any], Any]] = {
    'symbole': _texte, 'symbole_courtier': _texte, 'sous_jacent': _texte, 'devise_base': _texte,
    'devise_cotation': _texte, 'devise_marge': _texte, 'mode_calcul': _texte, 'taille_contrat': _POSITIF,
    'tick_size': _POSITIF, 'point': _POSITIF, 'digits': _entier(0), 'valeur_tick': _POSITIF,
    'volume_min': _POSITIF, 'volume_max': _POSITIF, 'volume_pas': _POSITIF, 'volume_limite': _NATUREL,
    'distance_stops_min_points': _entier(0), 'niveau_gel_points': _entier(0), 'mode_negociation': _texte,
    'mode_execution': _texte, 'modes_remplissage': _modes, 'protections_a_l_entree': _booleen,
    'convention_declenchement_verifiee': _booleen, 'commission_par_lot_par_cote': _NATUREL,
    'commission_minimum_par_ordre': _NATUREL, 'commission_nulle_confirmee': _booleen, 'devise_frais': _texte,
    'swap_achat': _RELATIF, 'swap_vente': _RELATIF, 'marge_initiale': _NATUREL, 'marge_maintenance': _NATUREL,
    'horaires': _horaires, 'releve_ms': _instant,
}
_SPEC_COMPTE: dict[str, Callable[[Any], Any]] = {
    'entite': _texte, 'serveur': _texte, 'plateforme': _texte, 'type_compte': _texte, 'devise': _texte,
    'levier': _entier(1), 'mode_marge': _texte, 'mode_stop_out': _texte, 'niveau_appel_marge': _NATUREL,
    'niveau_stop_out': _NATUREL, 'releve_ms': _instant,
}
CHAMPS_INSTRUMENT = tuple(_SPEC_INSTRUMENT)
CHAMPS_COMPTE = tuple(_SPEC_COMPTE)


@dataclass(frozen=True)
class ProfilInstrument:
    symbole: str
    symbole_courtier: str
    sous_jacent: str
    devise_base: str
    devise_cotation: str
    devise_marge: str
    mode_calcul: str
    taille_contrat: Decimal
    tick_size: Decimal
    point: Decimal
    digits: int
    valeur_tick: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_pas: Decimal
    volume_limite: Decimal
    distance_stops_min_points: int
    niveau_gel_points: int
    mode_negociation: str
    mode_execution: str
    modes_remplissage: frozenset[str]
    protections_a_l_entree: bool
    convention_declenchement_verifiee: bool
    commission_par_lot_par_cote: Decimal
    commission_minimum_par_ordre: Decimal
    commission_nulle_confirmee: bool
    devise_frais: str
    swap_achat: Decimal
    swap_vente: Decimal
    marge_initiale: Decimal
    marge_maintenance: Decimal
    horaires: HorairesCotation
    releve_ms: int


@dataclass(frozen=True)
class ProfilCompte:
    entite: str
    serveur: str
    plateforme: str
    type_compte: str
    devise: str
    levier: int
    mode_marge: str
    mode_stop_out: str
    niveau_appel_marge: Decimal
    niveau_stop_out: Decimal
    releve_ms: int


@dataclass(frozen=True)
class ResultatProfil:
    profil: ProfilInstrument | ProfilCompte | None
    non_prets: tuple[str, ...]


def _convertir(champs: Mapping[str, object], spec: dict[str, Callable[[Any], Any]]) -> tuple[dict, list[str]]:
    if not isinstance(champs, Mapping):
        raise ErreurInstrument('correspondance de champs attendue')
    inconnus = sorted(set(champs) - set(spec))
    if inconnus:
        raise ErreurInstrument(f'champs inconnus : {inconnus}')
    valeurs, non_prets = {}, []
    for nom, convertir in spec.items():
        brut = champs.get(nom)
        try:
            if brut is None:
                raise _Invalide
            valeurs[nom] = convertir(brut)
        except _Invalide:
            non_prets.append(nom)
    return valeurs, non_prets


def _ordonner(non_prets: list[str], ordre: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(nom for nom in ordre if nom in set(non_prets))


def construire_profil_instrument(champs: Mapping[str, object], commun: ParametresCommuns) -> ResultatProfil:
    valeurs, non_prets = _convertir(champs, _SPEC_INSTRUMENT)
    if 'symbole' in valeurs and valeurs['symbole'] not in commun.universe_priority:
        non_prets.append('symbole')
    if ('commission_par_lot_par_cote' in valeurs and 'commission_minimum_par_ordre' in valeurs
            and 'commission_nulle_confirmee' in valeurs
            and valeurs['commission_par_lot_par_cote'] == 0 and valeurs['commission_minimum_par_ordre'] == 0
            and not valeurs['commission_nulle_confirmee']):
        non_prets.append('commission_par_lot_par_cote')
    if 'volume_min' in valeurs and 'volume_max' in valeurs and valeurs['volume_max'] < valeurs['volume_min']:
        non_prets.append('volume_max')
    ordre = _ordonner(non_prets, CHAMPS_INSTRUMENT)
    return ResultatProfil(None if ordre else ProfilInstrument(**valeurs), ordre)


def construire_profil_compte(champs: Mapping[str, object], commun: ParametresCommuns) -> ResultatProfil:
    valeurs, non_prets = _convertir(champs, _SPEC_COMPTE)
    if 'devise' in valeurs and valeurs['devise'] != commun.account_currency:
        non_prets.append('devise')
    if 'levier' in valeurs and valeurs['levier'] != commun.account_leverage:
        non_prets.append('levier')
    ordre = _ordonner(non_prets, CHAMPS_COMPTE)
    return ResultatProfil(None if ordre else ProfilCompte(**valeurs), ordre)
