"""Catégorie 2, couche 2b : ticks → bougies → validation → chaîne, avec bougie sans tick (P-02) et trou (P-03)."""
import unittest

from robot.outils.configuration import configuration_figee
from xpbots.donnees.c1a_constructeur import ConstructeurBougies
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c2a_validation import ValidateurBougies
from xpbots.donnees.c2b_etat_indicateurs import ChaineIndicateurs
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

COMMUN = configuration_figee().technique.commun
D = COMMUN.timeframe_seconds * 1000
H = 3_600_000


class TestJonctionEtat(unittest.TestCase):
    def test_bougies_invalides_hors_de_la_chaine_et_tr_sur_derniere_cloture_valide(self):
        horaires = HorairesCotation((Intervalle(0, 24 * H),), (), 0, 24 * H)
        couverture = RegistreCouverture.depuis_registre_de_trous(0, 24 * H, [Intervalle(4 * D + 1, 4 * D + 2)])
        constructeur, validateur, chaine = ConstructeurBougies('EURUSD', D), ValidateurBougies('EURUSD'), ChaineIndicateurs(COMMUN.atr_period)
        prix = {0: 1.10, 1: 1.11, 3: 1.13, 4: 1.14, 5: 1.20, 6: 1.16}
        sorties = []
        for i, bid in sorted(prix.items()):
            for b in constructeur.ajouter(Tick('EURUSD', 'EURUSD', i * D, i * D, i, bid, bid + 0.0001)).bougies:
                v = validateur.valider(b, horaires, couverture).bougie
                sorties.append((v.debut_ms // D, v.motif_invalidite, chaine.ajouter(v)))
        self.assertEqual([(i, motif) for i, motif, _ in sorties],
                         [(0, None), (1, None), (2, 'AUCUN_BID'), (3, None), (4, 'TROU_DONNEES'), (5, None)])
        indicateurs = {i: ind for i, _, ind in sorties}
        self.assertIsNone(indicateurs[2])
        self.assertIsNone(indicateurs[4])
        self.assertAlmostEqual(indicateurs[5].tr, 1.20 - 1.13, places=12)
        self.assertEqual(indicateurs[5].rang, 3)


if __name__ == '__main__':
    unittest.main()
