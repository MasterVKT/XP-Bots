"""Catégorie 1, couche 1d (stop_local) : L-11, chacune des composantes et maximum inclusif."""
from dataclasses import replace
from decimal import Decimal
import math
import unittest

from robot.outils.london import TICK, bougie, dyadiques, miroir, parametres, range_connu
from xpbots.london.c0b_types import ErreurLondon, RefusLondon, StopLocal
from xpbots.london.c1d_stop import calculer_stop
from xpbots.noyau.c1c_domaine import Motif, Sens


class TestStopLondon(unittest.TestCase):
    def setUp(self):
        self.p = dyadiques()

    def test_formule_exacte_et_composantes_contraignantes_achat_et_vente(self):
        cas = [(bougie(p=self.p, l=99.5), 'BOUGIE'),
               (bougie(p=self.p, l=100), 'FRONTIERE'),
               (bougie(p=self.p, o=100.0625, h=100.25, l=100.0625, c=100.125), 'PLANCHER_ATR')]
        for b, nom in cas:
            for sens, enrichie, r in ((Sens.ACHAT, b, range_connu()),
                                      (Sens.VENTE, miroir(b), range_connu(haut=102, bas=100))):
                with self.subTest(nom=nom, sens=sens):
                    stop = calculer_stop(enrichie, r, sens, TICK, self.p)
                    a, bar = enrichie.indicateurs.a, enrichie.bougie
                    guard = max(float(TICK), self.p.commun.structural_buffer_atr * a)
                    attendues = ((bar.bas-guard, r.haut-self.p.boundary_stop_inside_atr*a,
                                  bar.cloture-self.p.commun.minimum_chart_stop_atr*a) if sens is Sens.ACHAT else
                                 (bar.haut+guard, r.bas+self.p.boundary_stop_inside_atr*a,
                                  bar.cloture+self.p.commun.minimum_chart_stop_atr*a))
                    self.assertEqual(stop.composantes, attendues)
                    self.assertEqual(stop.niveau, min(attendues) if sens is Sens.ACHAT else max(attendues))
                    self.assertEqual(stop.distance, sens.signe*(bar.cloture-stop.niveau))
                    self.assertEqual(stop.contraignantes, (nom,))

    def test_distance_maximale_exacte_admise_puis_depassee_sans_plafonnement(self):
        limite = self.p.commun.maximum_chart_stop_atr
        # c=101 ; bas=98.625 ; guard=0.125 : distance=2.5, exactement représentable.
        b = bougie(p=self.p, o=100, h=101, l=101-limite+self.p.commun.structural_buffer_atr, c=101)
        for sens, e, r in ((Sens.ACHAT, b, range_connu()),
                            (Sens.VENTE, miroir(b), range_connu(haut=102, bas=100))):
            stop = calculer_stop(e, r, sens, TICK, self.p)
            self.assertEqual(stop.distance, limite)
        au_dela = replace(b, bougie=replace(b.bougie, bas=math.nextafter(b.bougie.bas, -math.inf)))
        refus = calculer_stop(au_dela, range_connu(), Sens.ACHAT, TICK, self.p)
        self.assertEqual((refus.motif, refus.detail), (Motif.STOP_TOO_WIDE, None))

    def test_tick_contraignant_et_toutes_les_valeurs_lues(self):
        b, r = bougie(p=self.p), range_connu()
        original = calculer_stop(b, r, Sens.ACHAT, TICK, self.p)
        self.assertNotEqual(calculer_stop(b, r, Sens.ACHAT, Decimal('0.5'), self.p).niveau, original.niveau)
        for p in (replace(self.p, boundary_stop_inside_atr=1),
                  replace(self.p, commun=replace(self.p.commun, structural_buffer_atr=1)),
                  replace(self.p, commun=replace(self.p.commun, minimum_chart_stop_atr=2))):
            self.assertNotEqual(calculer_stop(b, r, Sens.ACHAT, TICK, p).niveau, original.niveau)
        p = replace(self.p, commun=replace(self.p.commun, maximum_chart_stop_atr=1))
        self.assertIsInstance(calculer_stop(b, r, Sens.ACHAT, TICK, p), RefusLondon)
        p = replace(self.p, take_profit_gross_price_r=self.p.take_profit_gross_price_r+1)
        self.assertEqual(calculer_stop(b, r, Sens.ACHAT, TICK, p).multiple_objectif, p.take_profit_gross_price_r)

    def test_entrees_incoherentes_refusees(self):
        for b, sens, tick in ((bougie(a=0), Sens.ACHAT, TICK), (bougie(a=None), Sens.ACHAT, TICK),
                               (bougie(), 'ACHAT', TICK), (bougie(), Sens.ACHAT, 0.1),
                               (bougie(valide=False, motif='AUCUN_BID'), Sens.ACHAT, TICK)):
            with self.assertRaises(ErreurLondon):
                calculer_stop(b, range_connu(), sens, tick, self.p)
