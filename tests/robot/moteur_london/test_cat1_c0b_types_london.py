"""Catégorie 1, couche 0b (types_london) : valeurs immuables, validations et motifs fermés."""
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal
import unittest

from xpbots.london.c0b_types import (Cassure, ErreurLondon, EtatQuotas, GelATRH1, RangeLondon, RefusLondon,
                                   StopLocal, nombre_fini, tick_flottant, verifier_bougie)
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.noyau.c1c_domaine import CleIntention, Motif, Sens

JOUR = date(2026, 1, 12)


class TestTypesLondon(unittest.TestCase):
    def test_valeurs_nominales_et_immuables(self):
        r = RangeLondon(JOUR, 2, 1, 0)
        self.assertEqual(r.largeur, 1)
        self.assertEqual(GelATRH1(JOUR, 1, 0, 1).atr, 1)
        self.assertEqual(Cassure(Sens.ACHAT, 0.5, 1, 0.125).sens, Sens.ACHAT)
        self.assertEqual(StopLocal(1, 2, 1, (1, 2, 3), ('BOUGIE',)).composantes, (1, 2, 3))
        with self.assertRaises(FrozenInstanceError):
            r.haut = 3

    def test_range_et_gel_refusent_les_entrees_incoherentes(self):
        for args in ((JOUR, 1, 1, 0), (JOUR, float('inf'), 1, 0), (JOUR, 2, 1, True),
                     (datetime(2026, 1, 12), 2, 1, 0)):
            with self.subTest(args=args), self.assertRaises(ErreurLondon):
                RangeLondon(*args)
        for args in ((JOUR, 0, 0, 0), (JOUR, 1, 2, 1), (JOUR, True, 0, 0)):
            with self.subTest(args=args), self.assertRaises(ErreurLondon):
                GelATRH1(*args)

    def test_fractions_stop_et_motifs_refuses(self):
        for args in ((Sens.ACHAT, 1.1, 1, 1), ('ACHAT', 0.5, 1, 1), (Sens.ACHAT, 1, 1, 0)):
            with self.assertRaises(ErreurLondon):
                Cassure(*args)
        for args in ((1, 2, 0, (1, 2, 3), ('BOUGIE',)), (1, 2, 1, (1, 2), ('BOUGIE',)),
                     (1, 2, 1, (1, 2, 3), ('INCONNUE',))):
            with self.assertRaises(ErreurLondon):
                StopLocal(*args)
        self.assertEqual(RefusLondon(Motif.NO_SETUP, 'PAS_DE_CASSURE').motif, Motif.NO_SETUP)
        with self.assertRaises(ErreurLondon):
            RefusLondon(Motif.NO_SETUP, 'FAUX')

    def test_etat_quotas_restaure_des_cles_uniques(self):
        cle = CleIntention('test', 'LONDON_V3', 'EURUSD', 0, Sens.ACHAT)
        self.assertEqual(EtatQuotas(JOUR, (cle,)).remplissages, (cle,))
        for args in ((None, (cle,)), (JOUR, (cle, cle)), (JOUR, ['cle'])):
            with self.assertRaises(ErreurLondon):
                EtatQuotas(*args)

    def test_tick_decimal_explicite_fini_et_representable(self):
        self.assertEqual(tick_flottant(Decimal('0.125')), 0.125)
        for valeur in (0.1, True, '0.1', Decimal(0), Decimal('-1'), Decimal('NaN'), Decimal('Infinity'),
                       Decimal('1e-9999'), Decimal('1e9999')):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurLondon):
                tick_flottant(valeur)
        for valeur in (True, '1', float('nan'), 10**400):
            with self.assertRaises(ErreurLondon):
                nombre_fini(valeur, 'valeur')

    def test_helper_bougie_refuse_type_et_unite(self):
        with self.assertRaises(ErreurLondon):
            verifier_bougie(None, UniteTemps.M15, 900000)
