"""Implémentation de la couche 3 (flux_bougies). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Union

from xpbots.donnees.c0a_types import (AnomalieDonnees, BougieEnrichie, ChangementTrou, ErreurDonneesTemps,
                                      IdentitePrechargement, IndicateursBougie, UniteTemps)
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.donnees.c1a_constructeur import ConstructeurBougies
from xpbots.donnees.c1c_couverture import JournalConnexions, SourceCouverture
from xpbots.donnees.c2a_validation import ValidateurBougies
from xpbots.donnees.c2b_etat_indicateurs import ChaineIndicateurs
from xpbots.noyau.c0c_configuration import ExportTechnique
from xpbots.noyau.c1a_marche import Bougie, Tick
from xpbots.noyau.c1b_instrument import HorairesCotation

SCHEMA_FLUX = 'xp-flux-bougies-v1'
EvenementFlux = Union[BougieEnrichie, ChangementTrou, AnomalieDonnees]
_ORDRE = (UniteTemps.H1, UniteTemps.M15)  # rang à fin égale : la H1 avant la M15
_CLES = {'schema', 'symbole', 'empreinte_configuration', 'unites'}
_CLES_UNITE = {'constructeur', 'chaine', 'en_trou'}


@dataclass
class _Unite:
    constructeur: ConstructeurBougies
    validateur: ValidateurBougies
    chaine: ChaineIndicateurs


class FluxBougies:
    """Ticks d'un symbole → bougies M15 et H1 validées et enrichies, changements de trou et anomalies."""

    def __init__(self, symbole: str, technique: ExportTechnique, horaires: HorairesCotation,
                 couverture: SourceCouverture) -> None:
        if not isinstance(symbole, str) or not symbole:
            raise ErreurDonneesTemps('symbole : texte non vide attendu')
        if not isinstance(technique, ExportTechnique):
            raise ErreurDonneesTemps('export technique figé du noyau attendu')
        if not callable(getattr(couverture, 'periodes', None)):
            raise ErreurDonneesTemps('source de couverture attendue')
        self.actualiser_horaires(horaires)
        commun = technique.commun
        self.symbole = symbole
        self._technique = technique
        self._couverture = couverture
        self._calendrier = CalendrierLondres.depuis_parametres(commun)
        self._unites = {u: _Unite(ConstructeurBougies(symbole, u.duree_ms(commun)), ValidateurBougies(symbole),
                                  ChaineIndicateurs(commun.atr_period)) for u in _ORDRE}

    @property
    def calendrier(self) -> CalendrierLondres:
        return self._calendrier

    @property
    def en_trou(self) -> bool:
        return self._unites[UniteTemps.M15].validateur.en_trou

    def identite(self, unite: UniteTemps) -> IdentitePrechargement:
        try:
            return self._unites[UniteTemps(unite)].chaine.identite
        except ValueError as erreur:
            raise ErreurDonneesTemps(f'unité de temps inconnue : {unite!r}') from erreur

    def actualiser_horaires(self, horaires: HorairesCotation) -> None:
        if not isinstance(horaires, HorairesCotation):
            raise ErreurDonneesTemps('horaires de cotation du noyau attendus')
        self._horaires = horaires

    def sur_connexion(self, connecte: bool, instant_ms: int) -> None:
        if not isinstance(self._couverture, JournalConnexions) or not isinstance(connecte, bool):
            raise ErreurDonneesTemps('connexion booléenne et journal de connexions attendus')
        (self._couverture.connecter if connecte else self._couverture.deconnecter)(instant_ms)

    def _enrichir(self, bougie: Bougie, unite: UniteTemps, indicateurs: IndicateursBougie | None) -> BougieEnrichie:
        calendrier = self._calendrier
        return BougieEnrichie(bougie, unite, indicateurs, calendrier.jour_local(bougie.debut_ms),
                              calendrier.datetime_local(bougie.debut_ms), calendrier.datetime_local(bougie.fin_ms),
                              calendrier.jour_utc(bougie.debut_ms))

    def sur_tick(self, tick: Tick) -> tuple[EvenementFlux, ...]:
        if not isinstance(tick, Tick):
            raise ErreurDonneesTemps('tick du noyau attendu')
        m15 = self._unites[UniteTemps.M15].constructeur.ajouter(tick)
        if m15.anomalie is not None:
            return (m15.anomalie,)
        h1 = self._unites[UniteTemps.H1].constructeur.ajouter(tick)
        if h1.anomalie is not None:  # exclu tant que la M15 n'est pas en retard sur la H1 (état du flux)
            raise ErreurDonneesTemps('état incohérent entre unités')
        brutes = sorted([(b.fin_ms, 0, UniteTemps.H1, b) for b in h1.bougies]
                        + [(b.fin_ms, 1, UniteTemps.M15, b) for b in m15.bougies], key=lambda e: e[:2])
        evenements: list[EvenementFlux] = []
        for _, _, unite, brute in brutes:
            etat = self._unites[unite]
            resultat = etat.validateur.valider(brute, self._horaires, self._couverture)
            if unite is UniteTemps.M15 and resultat.changement is not None:
                evenements.append(resultat.changement)
            evenements.append(self._enrichir(resultat.bougie, unite, etat.chaine.ajouter(resultat.bougie)))
        return tuple(evenements)

    def exporter_etat(self) -> dict[str, Any]:
        empreinte = self._technique.empreinte_canonique
        return {'schema': SCHEMA_FLUX, 'symbole': self.symbole, 'empreinte_configuration': empreinte,
                'unites': {u.value: {'constructeur': e.constructeur.exporter(), 'chaine': e.chaine.exporter(empreinte),
                                     'en_trou': e.validateur.en_trou} for u, e in self._unites.items()}}

    @classmethod
    def reprendre(cls, donnees: Mapping[str, Any], technique: ExportTechnique, horaires: HorairesCotation,
                  couverture: SourceCouverture) -> 'FluxBougies':
        if not isinstance(donnees, Mapping) or set(donnees) != _CLES or donnees['schema'] != SCHEMA_FLUX:
            raise ErreurDonneesTemps('état de flux incomplet, inconnu ou d\'un autre schéma')
        flux = cls(donnees['symbole'], technique, horaires, couverture)
        if donnees['empreinte_configuration'] != technique.empreinte_canonique:
            raise ErreurDonneesTemps('état de flux exporté sous une autre configuration')
        unites = donnees['unites']
        if not isinstance(unites, Mapping) or set(unites) != {u.value for u in _ORDRE}:
            raise ErreurDonneesTemps('état de flux : unités M15 et H1 attendues')
        for unite in _ORDRE:
            etat = unites[unite.value]
            if not isinstance(etat, Mapping) or set(etat) != _CLES_UNITE:
                raise ErreurDonneesTemps(f'état de l\'unité {unite.value} incomplet ou inconnu')
            constructeur = ConstructeurBougies.importer(etat['constructeur'])
            if constructeur.symbole != flux.symbole or constructeur.duree_ms != unite.duree_ms(technique.commun):
                raise ErreurDonneesTemps(f'constructeur {unite.value} d\'un autre symbole ou d\'une autre durée')
            flux._unites[unite] = _Unite(constructeur, ValidateurBougies(flux.symbole, etat['en_trou']),
                                         ChaineIndicateurs.importer(etat['chaine'], technique.empreinte_canonique))
        h1, m15 = (flux._unites[u].constructeur.derniere_fin_ms for u in _ORDRE)
        if h1 is not None and (m15 is None or not h1 <= m15 < h1 + UniteTemps.H1.duree_ms(technique.commun)):
            raise ErreurDonneesTemps('état incohérent entre unités')
        return flux
