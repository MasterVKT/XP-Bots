"""Catégorie 1, couche 0a : conversion qualifiée et scalaires natifs."""
from decimal import Decimal
import unittest
import numpy as np
from xpbots.infra.c0a_types import (TableHeureServeur, SegmentServeur, ErreurInfra,
    ErreurNative, entier_natif, nombre_decimal, champ_natif)


class TestTypesInfra(unittest.TestCase):
    def table(self, *segments):
        return TableHeureServeur('SERVEUR_FIXTURE', 1, '2026-11-10T00:00:00.000Z', ('mesure synthétique S01',), segments)

    def test_conversion_et_bornes_exactes(self):
        t = self.table(SegmentServeur(0, 3_600_000, 3600))
        self.assertEqual(t.utc_de_serveur(3_600_000), 0)
        self.assertEqual(t.serveur_de_utc(3_599_999), 7_199_999)
        for n in (3_599_999, 7_200_000):
            with self.assertRaises(ErreurInfra): t.utc_de_serveur(n)
        with self.assertRaises(ErreurInfra): t.serveur_de_utc(3_600_000)

    def test_heure_repetee_et_trou_ne_sont_pas_devines(self):
        for offsets in ((7200, 3600), (3600, 7200)):
            t = self.table(SegmentServeur(0, 3_600_000, offsets[0]), SegmentServeur(3_600_000, 7_200_000, offsets[1]))
            with self.assertRaises(ErreurInfra): t.utc_de_serveur(8_000_000)

    def test_document_et_mesures_obligatoires(self):
        d = dict(schema='xp-heure-serveur-v1', serveur='FIXTURE', version=1,
                 date_releve='2026-11-10T00:00:00.000Z', mesures=['preuve synthétique'],
                 segments=[dict(debut_utc='2026-11-10T00:00:00.000Z', fin_utc='2026-11-11T00:00:00.000Z', decalage_secondes=0)])
        t = TableHeureServeur.depuis_document(d)
        self.assertEqual(t.utc_de_serveur(1794268800000), 1794268800000)
        for changement in ({'version': True}, {'mesures': []}, {'mesures': 'preuve'}, {'extra': 0}):
            with self.assertRaises(ValueError): TableHeureServeur.depuis_document(dict(d, **changement))

    def test_types_stricts_segments_et_ordres(self):
        for v in (True, 1.0, -1):
            with self.assertRaises(ValueError): SegmentServeur(v, 2, 0)
        with self.assertRaises(ValueError): SegmentServeur(0, 2, True)
        with self.assertRaises(ErreurInfra): self.table(SegmentServeur(0, 3, 0), SegmentServeur(2, 4, 0))

    def test_numpy_entiers_prix_et_lignes_sans_test_de_verite(self):
        self.assertEqual(entier_natif(np.int64(123)), 123)
        self.assertEqual(nombre_decimal(np.float64(1.2345)), Decimal('1.2345'))
        a = np.array([(12, 1.2, 1.3)], dtype=[('time_msc', 'i8'), ('bid', 'f8'), ('ask', 'f8')])
        self.assertEqual(entier_natif(champ_natif(a[0], 'time_msc')), 12)
        with self.assertRaises(ErreurInfra): champ_natif(a[0], 'absent')

    def test_scalaires_invalides_et_erreurs_sans_message_sensible(self):
        for v in (True, np.bool_(True), 1.2, '2'):
            with self.assertRaises(ErreurInfra): entier_natif(v)
        for v in (True, np.bool_(False), '1', float('nan'), float('inf')):
            with self.assertRaises(ErreurInfra): nombre_decimal(v)
        e = ErreurNative('account_info', -6)
        self.assertEqual(e.code, -6)
        self.assertEqual(str(e), 'ENVIRONMENT_NOT_READY account_info code=-6')
