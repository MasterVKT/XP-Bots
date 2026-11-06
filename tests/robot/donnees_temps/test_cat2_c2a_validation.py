"""Catégorie 2, couche 2a : ticks → constructeur → classement → validation, avec intervalles vides et trou déclaré."""
import unittest

from xpbots.donnees.c0a_types import NatureTrou
from xpbots.donnees.c1a_constructeur import ConstructeurBougies
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c2a_validation import ValidateurBougies
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

D = 900_000
H = 3_600_000


class TestJonctionValidation(unittest.TestCase):
    def test_vide_couvert_p02_et_trou_declare(self):
        horaires = HorairesCotation((Intervalle(0, 24 * H),), (), 0, 24 * H)
        couverture = RegistreCouverture.depuis_registre_de_trous(0, 24 * H, [Intervalle(3 * D + 10, 3 * D + 20)])
        constructeur, validateur = ConstructeurBougies('EURUSD', D), ValidateurBougies('EURUSD')
        resultats = []
        for i, instant in enumerate((0, D, 3 * D + 5, 4 * D, 5 * D)):
            for b in constructeur.ajouter(Tick('EURUSD', 'EURUSD', instant, instant, i, 1.1, 1.1001)).bougies:
                resultats.append(validateur.valider(b, horaires, couverture))
        self.assertEqual([(r.bougie.debut_ms, r.bougie.motif_invalidite) for r in resultats],
                         [(0, None), (D, None), (2 * D, 'AUCUN_BID'), (3 * D, 'TROU_DONNEES'), (4 * D, None)])
        self.assertEqual([r.changement.nature for r in resultats if r.changement], [NatureTrou.DEBUT, NatureTrou.FIN])


if __name__ == '__main__':
    unittest.main()
