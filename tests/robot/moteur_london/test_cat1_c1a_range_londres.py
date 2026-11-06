"""Catégorie 1, couche 1a (range_londres) : S02.6-1, L-02 à L-05, L-08 et L-09."""
from dataclasses import replace
from datetime import date, timedelta
import unittest

from robot.outils.london import JOUR, bougie, bougies_range, parametres
from xpbots.london.c0b_types import ErreurLondon, RangeLondon
from xpbots.london.c1a_range import construire_range
from xpbots.noyau.c1c_domaine import Motif


class TestRangeLondon(unittest.TestCase):
    def setUp(self):
        self.p = parametres()

    def test_exactement_les_ouvertures_attendues_ete_hiver_et_apres_changement(self):
        for jour in (JOUR, date(2026, 7, 1), date(2026, 3, 30), date(2026, 10, 26)):
            suite = bougies_range(self.p, jour)
            r = construire_range(jour, suite, self.p)
            with self.subTest(jour=jour):
                self.assertEqual(len(suite), self.p.expected_range_m15_bars)
                self.assertEqual((r.haut, r.bas, r.largeur), (100, 98, 2))
                self.assertEqual(r.disponible_ms, suite[-1].bougie.fin_ms)

    def test_ouverture_de_fin_et_suivantes_ne_modifient_pas_le_range(self):
        suite = bougies_range(self.p)
        attendu = construire_range(JOUR, suite, self.p)
        extreme = bougie(p=self.p, heure=self.p.range_end_local_exclusive.isoformat(), h=200, l=1)
        self.assertEqual(construire_range(JOUR, [*suite, extreme], self.p), attendu)

    def test_extremes_heterogenes_exacts_en_toute_position_du_range(self):
        """Mutation réelle survivante : des bougies toutes identiques ne distinguaient pas max de min."""
        for index in range(self.p.expected_range_m15_bars):
            suite = bougies_range(self.p)
            oppose = len(suite)-1-index
            suite[index] = replace(suite[index], bougie=replace(suite[index].bougie, haut=101))
            suite[oppose] = replace(suite[oppose], bougie=replace(suite[oppose].bougie, bas=97))
            r = construire_range(JOUR, suite, self.p)
            with self.subTest(index=index):
                self.assertEqual((r.haut, r.bas, r.largeur), (101, 97, 4))

    def test_une_absence_et_chaque_bougie_invalide_refusent_le_jour(self):
        suite = bougies_range(self.p)
        self.assertEqual(construire_range(JOUR, suite[:-1], self.p).detail, 'RANGE_INCOMPLET')
        for index in range(len(suite)):
            for motif, code in (('AUCUN_BID', Motif.NO_SETUP), ('TROU_DONNEES', Motif.DATA_GAP),
                                ('HORAIRES_INCONNUS', Motif.DATA_GAP)):
                invalide = replace(suite[index], bougie=replace(suite[index].bougie, valide=False,
                                                              motif_invalidite=motif), indicateurs=None)
                modifiee = [*suite[:index], invalide, *suite[index+1:]]
                with self.subTest(index=index, motif=motif):
                    refus = construire_range(JOUR, modifiee, self.p)
                    self.assertEqual((refus.motif, refus.detail), (code, 'RANGE_BOUGIE_INVALIDE'))

    def test_disponibilite_maximale_ne_perd_pas_un_message_anterieur_tardif(self):
        suite = bougies_range(self.p)
        tardive = replace(suite[0], bougie=replace(suite[0].bougie,
                         instant_disponibilite_ms=suite[-1].bougie.fin_ms + 1))
        self.assertEqual(construire_range(JOUR, [tardive, *suite[1:]], self.p).disponible_ms,
                         tardive.bougie.instant_disponibilite_ms)

    def test_range_plat_et_jour_inactif(self):
        suite = [replace(e, bougie=replace(e.bougie, ouverture=99, haut=99, bas=99, cloture=99))
                 for e in bougies_range(self.p)]
        self.assertEqual(construire_range(JOUR, suite, self.p).detail, 'RANGE_HORS_BORNES')
        for jour in (date(2026, 7, 4), date(2026, 7, 5)):
            r = construire_range(jour, bougies_range(self.p, jour), self.p)
            self.assertEqual((r.motif, r.detail), (Motif.OUTSIDE_SESSION, 'JOUR_INACTIF'))

    def test_doublon_melange_de_symboles_et_type_refuses(self):
        suite = bougies_range(self.p)
        autre = replace(suite[-1], bougie=replace(suite[-1].bougie, symbole='GBPUSD'))
        for entrees in ([*suite, suite[0]], [*suite[:-1], autre], [None]):
            with self.assertRaises(ErreurLondon):
                construire_range(JOUR, entrees, self.p)

    def test_horaires_et_effectif_viennent_des_parametres(self):
        p = parametres(lambda j: j['london'].update(range_start_local='03:00:00', expected_range_m15_bars=16))
        r = construire_range(JOUR, bougies_range(p), p)
        self.assertIsInstance(r, RangeLondon)
        self.assertEqual(construire_range(JOUR, bougies_range(p)[1:], p).detail, 'RANGE_INCOMPLET')
