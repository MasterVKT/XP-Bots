"""Catégorie 1, couche 1c (bougie_cassure) : L-09, L-10 et bornes exactes de S02.3."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import math
import unittest

from robot.outils.london import JOUR, TICK, bougie, dyadiques, miroir, parametres, range_connu
from xpbots.london.c0b_types import Cassure, ErreurLondon, RefusLondon
from xpbots.london.c1c_cassure import evaluer_cassure
from xpbots.noyau.c1c_domaine import Sens


class TestCassureLondon(unittest.TestCase):
    def setUp(self):
        self.p = dyadiques()
        self.r = range_connu(p=self.p)

    def evaluer(self, **kwargs):
        return evaluer_cassure(bougie(p=self.p, **kwargs), self.r, TICK, self.p)

    def test_cassure_longue_et_miroir_vendeur_sans_croisement_precedent(self):
        b = bougie(p=self.p)
        hit = evaluer_cassure(b, self.r, TICK, self.p)
        self.assertEqual(hit.sens, Sens.ACHAT)
        self.assertEqual(hit.buffer, self.p.breakout_buffer_atr * b.indicateurs.a)
        self.assertEqual(hit.fraction_corps, abs(b.bougie.cloture-b.bougie.ouverture)/(b.bougie.haut-b.bougie.bas))
        r = range_connu(p=self.p, haut=102, bas=100)
        self.assertEqual(evaluer_cassure(miroir(b), r, TICK, self.p).sens, Sens.VENTE)
        # Aucun paramètre de clôture précédente : toute nouvelle bougie peut être étudiée.
        self.assertEqual(evaluer_cassure(b, self.r, TICK, self.p), hit)

    def test_egalite_au_buffer_refusee_dans_les_deux_sens(self):
        c = self.r.haut + self.p.breakout_buffer_atr
        b = bougie(p=self.p, o=100, h=c, l=100, c=c)
        self.assertEqual(evaluer_cassure(b, self.r, TICK, self.p).detail, 'PAS_DE_CASSURE')
        self.assertEqual(evaluer_cassure(miroir(b), range_connu(haut=102, bas=100), TICK, self.p).detail,
                         'PAS_DE_CASSURE')

    def test_tick_contraignant_et_buffer_parametre_sont_effectifs(self):
        b = bougie(p=self.p, o=100, h=100.5, l=100, c=100.5)
        self.assertIsInstance(evaluer_cassure(b, self.r, TICK, self.p), Cassure)
        self.assertEqual(evaluer_cassure(b, self.r, Decimal('0.5'), self.p).detail, 'PAS_DE_CASSURE')
        self.assertEqual(evaluer_cassure(b, self.r, TICK, replace(self.p, breakout_buffer_atr=0.5)).detail,
                         'PAS_DE_CASSURE')

    def test_corps_exact_admis_et_juste_sous_refuse(self):
        b = bougie(p=self.p, o=100.125, h=101, l=99.75, c=100.75)
        self.assertEqual(evaluer_cassure(b, self.r, TICK, self.p).fraction_corps, self.p.signal_body_fraction_min)
        presque = replace(b, bougie=replace(b.bougie, ouverture=math.nextafter(100.125, math.inf)))
        self.assertEqual(evaluer_cassure(presque, self.r, TICK, self.p).detail, 'CORPS_INSUFFISANT')

    def test_cloture_exacte_admise_et_juste_sous_refusee(self):
        b = bougie(p=self.p, o=100, h=101, l=100, c=100.75)
        self.assertEqual(evaluer_cassure(b, self.r, TICK, self.p).fraction_cloture, self.p.signal_close_location_min)
        presque = replace(b, bougie=replace(b.bougie, cloture=math.nextafter(100.75, -math.inf)))
        self.assertEqual(evaluer_cassure(presque, self.r, TICK, self.p).detail, 'CLOTURE_ELOIGNEE')

    def test_tr_exact_admis_et_juste_au_dessus_refuse(self):
        limite = self.p.commun.maximum_signal_true_range_atr
        self.assertIsInstance(self.evaluer(tr=limite), Cassure)
        self.assertEqual(self.evaluer(tr=math.nextafter(limite, math.inf)).detail, 'TR_EXCESSIF')

    def test_doji_bougie_plate_et_corps_oppose(self):
        self.assertEqual(self.evaluer(o=100.875).detail, 'CORPS_INSUFFISANT')
        self.assertEqual(self.evaluer(o=100, h=100, l=100, c=100).detail, 'BOUGIE_PLATE')
        self.assertEqual(self.evaluer(o=101.875, h=102, l=100).detail, 'PAS_DE_CASSURE')

    def test_atr_absent_non_positif_et_bougie_invalide(self):
        self.assertEqual(self.evaluer(a=None).detail, 'ATR_M15_INDISPONIBLE')
        self.assertEqual(self.evaluer(a=0).detail, 'ATR_NON_POSITIF')
        self.assertEqual(self.evaluer(valide=False, motif='AUCUN_BID').detail, 'PAS_DE_CASSURE')

    def test_contrats_de_jour_et_tick_refuses(self):
        for b, tick in ((bougie(jour=JOUR+timedelta(days=1)), TICK), (bougie(), 0.1)):
            with self.assertRaises(ErreurLondon):
                evaluer_cassure(b, self.r, tick, self.p)

    def test_corps_cloture_et_tr_changent_avec_les_parametres(self):
        b = bougie(p=self.p)
        for p in (replace(self.p, signal_body_fraction_min=1), replace(self.p, signal_close_location_min=1),
                  replace(self.p, commun=replace(self.p.commun, maximum_signal_true_range_atr=1))):
            with self.subTest(p=p):
                self.assertIsInstance(evaluer_cassure(b, self.r, TICK, p), RefusLondon)
