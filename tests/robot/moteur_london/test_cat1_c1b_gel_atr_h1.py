"""Catégorie 1, couche 1b (gel_atr_h1) : S02.6-2, L-07, P-09 et P-10."""
from datetime import date
import unittest

from robot.outils.london import JOUR, bougie, parametres
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.london.c0b_types import ErreurLondon
from xpbots.london.c1b_gel_atr_h1 import construire_gel


class TestGelATR(unittest.TestCase):
    def setUp(self):
        self.p = parametres()

    def h1(self, **kwargs):
        return bougie(p=self.p, unite=UniteTemps.H1, **kwargs)

    def test_derniere_h1_close_a_f_et_age_exact_d_une_heure_admis(self):
        precedente = self.h1(heure='05:00:00', atr=2)
        derniere = self.h1(heure='06:00:00', atr=1)
        self.assertEqual(construire_gel(JOUR, [derniere, precedente], self.p).atr, derniere.indicateurs.atr)
        self.assertEqual(construire_gel(JOUR, [precedente], self.p).atr, precedente.indicateurs.atr)
        self.assertIsNone(construire_gel(JOUR, [self.h1(heure='04:00:00')], self.p))

    def test_h1_apres_le_gel_exclue_et_pas_de_m15_partielle(self):
        self.assertIsNone(construire_gel(JOUR, [self.h1(heure='07:00:00')], self.p))
        with self.assertRaises(ErreurLondon):
            construire_gel(JOUR, [bougie(heure='06:45:00')], self.p)

    def test_h1_invalide_de_7h_repli_sur_la_valide_de_6h(self):
        valide = self.h1(heure='05:00:00', atr=2)
        invalide = self.h1(heure='06:00:00', valide=False, motif='AUCUN_BID')
        gel = construire_gel(JOUR, [valide, invalide], self.p)
        self.assertEqual((gel.atr, gel.fin_h1_ms), (2, valide.bougie.fin_ms))

    def test_prechargement_inclusif_299_contre_300_et_atr_non_positive(self):
        seuil = self.p.commun.warmup_closed_h1_bars - 1
        for rang, atr, admis in ((seuil-1, 1, False), (seuil, 1, True), (seuil, 0, False), (seuil, None, False)):
            with self.subTest(rang=rang, atr=atr):
                self.assertEqual(construire_gel(JOUR, [self.h1(heure='06:00:00', rang=rang, atr=atr)], self.p)
                                 is not None, admis)

    def test_valide_recente_non_initialisee_ne_fait_pas_revenir_a_une_autre(self):
        self.assertIsNone(construire_gel(JOUR, [self.h1(heure='05:00:00'),
                                               self.h1(heure='06:00:00', atr=0)], self.p))

    def test_disponibilite_tardive_conservee_sans_anticipation(self):
        h1 = self.h1(heure='06:00:00', retard_ms=80*60000)
        gel = construire_gel(JOUR, [h1], self.p)
        self.assertEqual(gel.disponible_ms, h1.bougie.instant_disponibilite_ms)
        self.assertGreater(gel.disponible_ms, bougie().bougie.fin_ms)

    def test_melange_de_symboles_refuse(self):
        with self.assertRaises(ErreurLondon):
            construire_gel(JOUR, [self.h1(heure='05:00:00'), self.h1(heure='06:00:00', symbole='GBPUSD')], self.p)
