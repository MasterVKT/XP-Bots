"""Champs synthétiques de profils C04 pour les tests (valeurs plausibles, jamais des relevés réels de courtier)."""
from __future__ import annotations

from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle


def horaires_semaine(debut_iso='2026-07-13T00:00:00Z', fin_iso='2026-07-18T00:00:00Z', fermetures=()):
    """Séances de 00:05 à 23:55 UTC du lundi au vendredi d'une semaine, validité couvrant la semaine."""
    debut = instant_depuis_iso(debut_iso)
    jour = 86_400_000
    seances = tuple(Intervalle(debut + i * jour + 300_000, debut + (i + 1) * jour - 300_000) for i in range(5))
    return HorairesCotation(seances, tuple(fermetures), debut, instant_depuis_iso(fin_iso) + jour)


def champs_instrument(**changements):
    champs = dict(symbole='EURUSD', symbole_courtier='EURUSDmicro', sous_jacent='EURUSD', devise_base='EUR',
                  devise_cotation='USD', devise_marge='EUR', mode_calcul='FOREX', taille_contrat=1000.0,
                  tick_size=0.00001, point=0.00001, digits=5, valeur_tick=0.01, volume_min=0.1, volume_max=50.0,
                  volume_pas=0.01, volume_limite=0, distance_stops_min_points=0, niveau_gel_points=0,
                  mode_negociation='FULL', mode_execution='MARKET', modes_remplissage={'FOK', 'IOC'},
                  protections_a_l_entree=True, convention_declenchement_verifiee=True,
                  commission_par_lot_par_cote=0.0, commission_minimum_par_ordre=0.0, commission_nulle_confirmee=True,
                  devise_frais='USD', swap_achat=-0.5, swap_vente=0.1, marge_initiale=0.0, marge_maintenance=0.0,
                  horaires=horaires_semaine(), releve_ms=instant_depuis_iso('2026-07-13T06:00:00Z'))
    champs.update(changements)
    return champs


def champs_compte(**changements):
    champs = dict(entite='Courtier de test', serveur='Test-Demo', plateforme='MT5', type_compte='DEMO', devise='USD',
                  levier=100, mode_marge='HEDGING', mode_stop_out='POURCENTAGE', niveau_appel_marge=100,
                  niveau_stop_out=50, releve_ms=instant_depuis_iso('2026-07-13T06:00:00Z'))
    champs.update(changements)
    return champs
