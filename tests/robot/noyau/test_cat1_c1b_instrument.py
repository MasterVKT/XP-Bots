"""Catégorie 1, couche 1b (instrument) : profils C04 sans champ manquant valant zéro, horaires de cotation."""
from decimal import Decimal
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.profils import champs_compte, champs_instrument, horaires_semaine
from xpbots.noyau.c1b_instrument import (CHAMPS_COMPTE, CHAMPS_INSTRUMENT, ErreurInstrument, HorairesCotation,
                                         Intervalle, ProfilInstrument, construire_profil_compte,
                                         construire_profil_instrument)

COMMUN = configuration_figee().technique.commun
H = 3_600_000


class TestProfilInstrument(unittest.TestCase):
    def test_profil_complet(self):
        resultat = construire_profil_instrument(champs_instrument(), COMMUN)
        self.assertEqual(resultat.non_prets, ())
        profil = resultat.profil
        self.assertIsInstance(profil, ProfilInstrument)
        self.assertEqual((profil.tick_size, profil.taille_contrat, profil.volume_pas),
                         (Decimal('0.00001'), Decimal('1000.0'), Decimal('0.01')))
        self.assertEqual(profil.modes_remplissage, frozenset({'FOK', 'IOC'}))

    def test_aucun_champ_manquant_ne_vaut_zero(self):
        for nom in CHAMPS_INSTRUMENT:
            for absent in ('retiré', None):
                with self.subTest(champ=nom, absent=absent):
                    champs = champs_instrument()
                    if absent is None:
                        champs[nom] = None
                    else:
                        del champs[nom]
                    resultat = construire_profil_instrument(champs, COMMUN)
                    self.assertIsNone(resultat.profil)
                    self.assertIn(nom, resultat.non_prets)

    def test_valeurs_invalides_listees_dans_l_ordre(self):
        resultat = construire_profil_instrument(
            champs_instrument(tick_size=0, digits=-1, modes_remplissage=set(), volume_min=float('nan'),
                              protections_a_l_entree='oui'), COMMUN)
        self.assertEqual(resultat.non_prets, ('tick_size', 'digits', 'volume_min', 'modes_remplissage',
                                              'protections_a_l_entree'))

    def test_controles_croises(self):
        cas = {'symbole': champs_instrument(symbole='USDJPY'),
               'commission_par_lot_par_cote': champs_instrument(commission_nulle_confirmee=False),
               'volume_max': champs_instrument(volume_max=0.05)}
        for attendu, champs in cas.items():
            with self.subTest(champ=attendu):
                self.assertEqual(construire_profil_instrument(champs, COMMUN).non_prets, (attendu,))
        confirmee = construire_profil_instrument(champs_instrument(commission_nulle_confirmee=False,
                                                                   commission_par_lot_par_cote=3.5), COMMUN)
        self.assertEqual(confirmee.non_prets, ())

    def test_champ_inconnu(self):
        with self.assertRaises(ErreurInstrument):
            construire_profil_instrument(champs_instrument(levier=100), COMMUN)
        with self.assertRaises(ErreurInstrument):
            construire_profil_instrument([('symbole', 'EURUSD')], COMMUN)


class TestProfilCompte(unittest.TestCase):
    def test_compte_conforme_et_ecarts(self):
        self.assertEqual(construire_profil_compte(champs_compte(), COMMUN).non_prets, ())
        self.assertEqual(construire_profil_compte(champs_compte(devise='EUR', levier=500), COMMUN).non_prets,
                         ('devise', 'levier'))
        for nom in CHAMPS_COMPTE:
            with self.subTest(champ=nom):
                champs = champs_compte()
                del champs[nom]
                self.assertIn(nom, construire_profil_compte(champs, COMMUN).non_prets)


class TestHoraires(unittest.TestCase):
    def setUp(self):
        self.horaires = horaires_semaine()
        self.lundi = self.horaires.debut_validite_ms

    def test_ouverture_et_fermeture(self):
        self.assertFalse(self.horaires.ouvert_a(self.lundi))
        self.assertTrue(self.horaires.ouvert_a(self.lundi + 300_000))
        self.assertEqual(self.horaires.prochaine_fermeture_apres(self.lundi + H), self.lundi + 24 * H - 300_000)
        self.assertIsNone(self.horaires.prochaine_fermeture_apres(self.lundi + 24 * H - 300_000))

    def test_fermeture_exceptionnelle(self):
        fermeture = Intervalle(self.lundi + 10 * H, self.lundi + 12 * H)
        horaires = horaires_semaine(fermetures=(fermeture,))
        self.assertEqual(horaires.prochaine_fermeture_apres(self.lundi + 9 * H), self.lundi + 10 * H)
        self.assertFalse(horaires.ouvert_a(self.lundi + 11 * H))
        self.assertEqual(horaires.prochaine_fermeture_apres(self.lundi + 12 * H), self.lundi + 24 * H - 300_000)

    def test_hors_validite_et_fermeture_inconnue(self):
        with self.assertRaises(ErreurInstrument):
            self.horaires.ouvert_a(self.lundi - 1)
        with self.assertRaises(ErreurInstrument):
            self.horaires.ouvert_a(self.horaires.fin_validite_ms)
        ouverte = HorairesCotation((Intervalle(0, 10 * H),), (), 0, 5 * H)
        with self.assertRaises(ErreurInstrument):
            ouverte.prochaine_fermeture_apres(H)

    def test_intervalles_refuses(self):
        with self.assertRaises(ErreurInstrument):
            Intervalle(10, 10)
        with self.assertRaises(ErreurInstrument):
            HorairesCotation((Intervalle(0, 10), Intervalle(5, 20)), (), 0, 100)
        with self.assertRaises(ErreurInstrument):
            HorairesCotation((Intervalle(20, 30), Intervalle(0, 10)), (), 0, 100)
        with self.assertRaises(ErreurInstrument):
            HorairesCotation(((0, 10),), (), 0, 100)


if __name__ == '__main__':
    unittest.main()
