"""Catégorie 2, couche 1b (instrument) : jonction sur le bloc réel {0a, 0b, 0c, 1b}, par chemins représentatifs."""
from decimal import Decimal
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.profils import champs_compte, champs_instrument
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c0b_nombres import Arrondi, arrondir_sur_grille
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle, construire_profil_compte, construire_profil_instrument


class TestJonctionInstrument(unittest.TestCase):
    def setUp(self):
        self.commun = configuration_figee().technique.commun

    def test_chaque_symbole_de_l_univers_charge_est_admis(self):
        for symbole in self.commun.universe_priority:
            with self.subTest(symbole=symbole):
                self.assertEqual(construire_profil_instrument(champs_instrument(symbole=symbole), self.commun).non_prets, ())

    def test_compte_confronte_a_la_configuration_chargee(self):
        champs = champs_compte(devise=self.commun.account_currency, levier=self.commun.account_leverage)
        self.assertEqual(construire_profil_compte(champs, self.commun).non_prets, ())

    def test_profil_decimal_utilise_par_un_arrondi_de_volume(self):
        profil = construire_profil_instrument(champs_instrument(volume_pas=0.01), self.commun).profil
        self.assertEqual(arrondir_sur_grille(Decimal('0.1379'), profil.volume_pas, Arrondi.BAS), Decimal('0.13'))

    def test_horaires_bornes_par_instants_iso(self):
        debut = instant_depuis_iso('2026-12-24T00:00:00Z')
        seance = Intervalle(debut, instant_depuis_iso('2026-12-24T22:00:00Z'))
        reduite = Intervalle(instant_depuis_iso('2026-12-24T19:00:00Z'), seance.fin_ms)
        horaires = HorairesCotation((seance,), (reduite,), debut, instant_depuis_iso('2026-12-25T00:00:00Z'))
        self.assertEqual(horaires.prochaine_fermeture_apres(instant_depuis_iso('2026-12-24T10:00:00Z')),
                         instant_depuis_iso('2026-12-24T19:00:00Z'))


if __name__ == '__main__':
    unittest.main()
