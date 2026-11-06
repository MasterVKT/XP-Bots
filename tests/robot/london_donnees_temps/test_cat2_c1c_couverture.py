"""Catégorie 2, couche 1c : classement des M15 d'une semaine synthétique avec horaires du noyau et registre de trous."""
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.profils import horaires_semaine
from xpbots.donnees.c0a_types import StatutCouverture, UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture, classer_intervalle
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c1b_instrument import Intervalle

COMMUN = configuration_figee().technique.commun


class TestJonctionCouverture(unittest.TestCase):
    def test_semaine_avec_un_trou_declare(self):
        duree = UniteTemps.M15.duree_ms(COMMUN)
        horaires = horaires_semaine()
        trou = Intervalle(instant_depuis_iso('2026-07-14T10:05:00Z'), instant_depuis_iso('2026-07-14T10:20:00Z'))
        registre = RegistreCouverture.depuis_registre_de_trous(horaires.debut_validite_ms, horaires.fin_validite_ms, [trou])
        statuts = {}
        for debut in range(instant_depuis_iso('2026-07-13T00:00:00Z'), instant_depuis_iso('2026-07-18T00:00:00Z'), duree):
            statuts.setdefault(classer_intervalle(debut, debut + duree, horaires, registre), []).append(debut)
        self.assertEqual(statuts[StatutCouverture.TROU],
                         [instant_depuis_iso('2026-07-14T10:00:00Z'), instant_depuis_iso('2026-07-14T10:15:00Z')])
        self.assertEqual(len(statuts.get(StatutCouverture.FERMETURE_OFFICIELLE, [])), 0, 'séances de 00:05 à 23:55 : M15 partiellement ouvertes')
        self.assertEqual(len(statuts[StatutCouverture.COUVERT]), 5 * 96 - 2)


if __name__ == '__main__':
    unittest.main()
