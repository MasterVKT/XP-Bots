"""Implémentation de la couche 2a (validation_bougies). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from dataclasses import dataclass

from xpbots.donnees.c0a_types import ChangementTrou, ErreurDonneesTemps, NatureTrou, StatutCouverture
from xpbots.donnees.c1a_constructeur import BougieBrute
from xpbots.donnees.c1c_couverture import SourceCouverture, classer_intervalle
from xpbots.noyau.c1a_marche import Bougie
from xpbots.noyau.c1b_instrument import HorairesCotation

AUCUN_BID = 'AUCUN_BID'
MARCHE_FERME = 'MARCHE_FERME'
TROU_DONNEES = 'TROU_DONNEES'
HORAIRES_INCONNUS = 'HORAIRES_INCONNUS'
_MOTIFS = {StatutCouverture.FERMETURE_OFFICIELLE: MARCHE_FERME, StatutCouverture.TROU: TROU_DONNEES,
           StatutCouverture.INCONNU: HORAIRES_INCONNUS}


@dataclass(frozen=True)
class ResultatValidation:
    bougie: Bougie
    statut: StatutCouverture
    changement: ChangementTrou | None = None


class ValidateurBougies:
    """Bougie brute + couverture → bougie du noyau, valide ou invalide motivée, et état de trou."""

    def __init__(self, symbole: str, en_trou: bool = False) -> None:
        if not isinstance(symbole, str) or not symbole or not isinstance(en_trou, bool):
            raise ErreurDonneesTemps('symbole non vide et état de trou booléen attendus')
        self.symbole = symbole
        self._en_trou = en_trou

    @property
    def en_trou(self) -> bool:
        return self._en_trou

    def valider(self, brute: BougieBrute, horaires: HorairesCotation, couverture: SourceCouverture) -> ResultatValidation:
        if not isinstance(brute, BougieBrute) or brute.symbole != self.symbole:
            raise ErreurDonneesTemps(f'bougie brute du symbole {self.symbole} attendue')
        statut = classer_intervalle(brute.debut_ms, brute.fin_ms, horaires, couverture)
        prix = (brute.ouverture, brute.haut, brute.bas, brute.cloture)
        if statut is StatutCouverture.COUVERT:
            valide = not brute.vide
            motif = None if valide else AUCUN_BID
        else:
            valide, motif = False, _MOTIFS[statut]
        bougie = Bougie(self.symbole, brute.debut_ms, brute.duree_ms, *prix, brute.nombre_evenements, valide, motif,
                        brute.instant_disponibilite_ms)
        changement = None
        if statut in (StatutCouverture.TROU, StatutCouverture.INCONNU) and not self._en_trou:
            self._en_trou = True
            changement = ChangementTrou(self.symbole, NatureTrou.DEBUT, brute.debut_ms, brute.instant_disponibilite_ms)
        elif statut is StatutCouverture.COUVERT and self._en_trou:
            self._en_trou = False
            changement = ChangementTrou(self.symbole, NatureTrou.FIN, brute.debut_ms, brute.instant_disponibilite_ms)
        return ResultatValidation(bougie, statut, changement)
