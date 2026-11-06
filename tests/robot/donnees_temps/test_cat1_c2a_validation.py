"""Catégorie 1, couche 2a (validation_bougies) : P-02, fermetures, trous, horaires inconnus et état de trou."""
import unittest

from xpbots.donnees.c0a_types import ErreurDonneesTemps, NatureTrou, StatutCouverture
from xpbots.donnees.c1a_constructeur import BougieBrute
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c2a_validation import ValidateurBougies
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

D = 900_000
H = 3_600_000
HORAIRES = HorairesCotation((Intervalle(0, 10 * H),), (), 0, 12 * H)
TOUT = RegistreCouverture([Intervalle(0, 12 * H)])


def brute(debut, vide=False):
    prix = (None,) * 4 if vide else (1.1, 1.2, 1.0, 1.15)
    return BougieBrute('EURUSD', debut, D, *prix, 0 if vide else 3, debut + D)


class TestValidation(unittest.TestCase):
    def test_couverte_avec_bid(self):
        resultat = ValidateurBougies('EURUSD').valider(brute(0), HORAIRES, TOUT)
        self.assertEqual((resultat.bougie.valide, resultat.statut, resultat.changement), (True, StatutCouverture.COUVERT, None))
        self.assertEqual((resultat.bougie.haut, resultat.bougie.instant_disponibilite_ms), (1.2, D))

    def test_p02_couverte_sans_bid(self):
        resultat = ValidateurBougies('EURUSD').valider(brute(0, vide=True), HORAIRES, TOUT)
        self.assertEqual((resultat.bougie.valide, resultat.bougie.motif_invalidite, resultat.changement),
                         (False, 'AUCUN_BID', None))

    def test_fermeture_officielle_sans_trou(self):
        resultat = ValidateurBougies('EURUSD').valider(brute(10 * H), HORAIRES, TOUT)
        self.assertEqual((resultat.bougie.motif_invalidite, resultat.bougie.haut, resultat.changement), ('MARCHE_FERME', 1.2, None))

    def test_trou_puis_retour_de_la_couverture(self):
        couverture = RegistreCouverture([Intervalle(0, H), Intervalle(2 * H, 12 * H)])
        validateur = ValidateurBougies('EURUSD')
        statuts = []
        for debut in (0, H, H + D, 10 * H, 2 * H):
            resultat = validateur.valider(brute(debut), HORAIRES, couverture)
            statuts.append((resultat.bougie.motif_invalidite, resultat.changement and resultat.changement.nature))
        self.assertEqual(statuts, [(None, None), ('TROU_DONNEES', NatureTrou.DEBUT), ('TROU_DONNEES', None),
                                   ('MARCHE_FERME', None), (None, NatureTrou.FIN)])
        self.assertFalse(validateur.en_trou)

    def test_horaires_inconnus_ouvrent_un_trou(self):
        resultat = ValidateurBougies('EURUSD').valider(brute(12 * H), HORAIRES, TOUT)
        self.assertEqual((resultat.statut, resultat.bougie.motif_invalidite, resultat.changement.nature),
                         (StatutCouverture.INCONNU, 'HORAIRES_INCONNUS', NatureTrou.DEBUT))

    def test_reprise_en_trou_puis_fin(self):
        resultat = ValidateurBougies('EURUSD', en_trou=True).valider(brute(0, vide=True), HORAIRES, TOUT)
        self.assertEqual((resultat.bougie.motif_invalidite, resultat.changement.nature, resultat.changement.instant_ms),
                         ('AUCUN_BID', NatureTrou.FIN, D))

    def test_refus(self):
        with self.assertRaises(ErreurDonneesTemps):
            ValidateurBougies('GBPUSD').valider(brute(0), HORAIRES, TOUT)
        with self.assertRaises(ErreurDonneesTemps):
            ValidateurBougies('EURUSD').valider('brute', HORAIRES, TOUT)
        with self.assertRaises(ErreurDonneesTemps):
            ValidateurBougies('', False)
        with self.assertRaises(ErreurDonneesTemps):
            ValidateurBougies('EURUSD', 'non')


if __name__ == '__main__':
    unittest.main()
