"""Catégorie 1, couche 1c (couverture_flux) : P-01 en historique et en direct, fermetures et horaires inconnus."""
import unittest

from xpbots.donnees.c0a_types import ErreurDonneesTemps, StatutCouverture
from xpbots.donnees.c1c_couverture import JournalConnexions, RegistreCouverture, classer_intervalle, parties_ouvertes
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

H = 3_600_000
D = 900_000
HORAIRES = HorairesCotation((Intervalle(H, 10 * H), Intervalle(12 * H, 20 * H)), (Intervalle(15 * H, 16 * H),), 0, 24 * H)


class TestPartiesOuvertes(unittest.TestCase):
    def test_seances_moins_fermetures(self):
        self.assertEqual(parties_ouvertes(HORAIRES, 9 * H, 13 * H), (Intervalle(9 * H, 10 * H), Intervalle(12 * H, 13 * H)))
        self.assertEqual(parties_ouvertes(HORAIRES, 15 * H, 16 * H), ())
        self.assertEqual(parties_ouvertes(HORAIRES, 15 * H + D, 16 * H + D), (Intervalle(16 * H, 16 * H + D),))

    def test_refus(self):
        with self.assertRaises(ErreurDonneesTemps):
            parties_ouvertes(HORAIRES, 23 * H, 25 * H)
        with self.assertRaises(ErreurDonneesTemps):
            parties_ouvertes(HORAIRES, 5 * H, 5 * H)
        with self.assertRaises(ErreurDonneesTemps):
            parties_ouvertes('horaires', 0, H)


class TestClassement(unittest.TestCase):
    def test_historique_avec_registre_de_trous(self):
        registre = RegistreCouverture.depuis_registre_de_trous(0, 24 * H, [Intervalle(5 * H + 60_000, 5 * H + 120_000)])
        self.assertEqual(classer_intervalle(2 * H, 2 * H + D, HORAIRES, registre), StatutCouverture.COUVERT)
        self.assertEqual(classer_intervalle(5 * H, 5 * H + D, HORAIRES, registre), StatutCouverture.TROU)
        self.assertEqual(classer_intervalle(11 * H, 11 * H + D, HORAIRES, registre), StatutCouverture.FERMETURE_OFFICIELLE)
        self.assertEqual(classer_intervalle(23 * H + D * 3, 24 * H + D * 3, HORAIRES, registre), StatutCouverture.INCONNU)

    def test_trou_pendant_une_fermeture_n_est_pas_un_trou(self):
        registre = RegistreCouverture.depuis_registre_de_trous(0, 24 * H, [Intervalle(10 * H, 12 * H)])
        self.assertEqual(classer_intervalle(11 * H, 11 * H + D, HORAIRES, registre), StatutCouverture.FERMETURE_OFFICIELLE)
        self.assertEqual(classer_intervalle(9 * H + 3 * D, 10 * H + 3 * D, HORAIRES, registre), StatutCouverture.COUVERT)

    def test_source_sans_registre_ne_couvre_rien(self):
        self.assertEqual(classer_intervalle(2 * H, 2 * H + D, HORAIRES, RegistreCouverture([])), StatutCouverture.TROU)

    def test_direct_avec_connexions(self):
        journal = JournalConnexions()
        self.assertEqual(classer_intervalle(2 * H, 2 * H + D, HORAIRES, journal), StatutCouverture.TROU)
        journal.connecter(2 * H)
        self.assertEqual(classer_intervalle(2 * H, 2 * H + D, HORAIRES, journal), StatutCouverture.COUVERT, 'connexion ouverte')
        journal.deconnecter(2 * H + D + 5)
        self.assertEqual(classer_intervalle(2 * H + D, 2 * H + 2 * D, HORAIRES, journal), StatutCouverture.TROU)
        journal.connecter(2 * H + D + 5)
        self.assertEqual(classer_intervalle(2 * H + D, 2 * H + 2 * D, HORAIRES, journal), StatutCouverture.COUVERT,
                         'reconnexion immédiate : périodes fusionnées')

    def test_refus_du_journal_et_du_registre(self):
        journal = JournalConnexions()
        with self.assertRaises(ErreurDonneesTemps):
            journal.deconnecter(0)
        journal.connecter(10)
        with self.assertRaises(ErreurDonneesTemps):
            journal.connecter(20)
        with self.assertRaises(ErreurDonneesTemps):
            journal.deconnecter(5)
        with self.assertRaises(ErreurDonneesTemps):
            RegistreCouverture([Intervalle(0, 10), Intervalle(5, 20)])
        with self.assertRaises(ErreurDonneesTemps):
            classer_intervalle(10, 5, HORAIRES, RegistreCouverture([]))


if __name__ == '__main__':
    unittest.main()
