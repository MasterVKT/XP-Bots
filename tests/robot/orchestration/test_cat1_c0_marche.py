"""Catégorie 1, couche 0 : extension additive des réceptions de marché physiques."""
import unittest
from xpbots.orchestration.c0_contrats import ReceptionExterne, EntreeMoteur, ErreurOrchestration


class TestReceptionMarche(unittest.TestCase):
    def test_fait_marche_date_par_son_cadre_sans_lire_ni_parser(self):
        r = ReceptionExterne('MARCHE', b'{"schema":"xp-etat-marche-v1"}', 'EURUSD')
        e = EntreeMoteur(100, 1, receptions=(r,))
        self.assertEqual(e.receptions, (r,))
        self.assertEqual(e.instant_ms, 100)
        self.assertEqual(r.octets, b'{"schema":"xp-etat-marche-v1"}')

    def test_structure_stricte_et_octets_obligatoires(self):
        for b, s, table in ((None, 'EURUSD', None), ('{}', 'EURUSD', None),
                            (b'{}', None, None), (b'{}', '', None), (b'{}', 'EURUSD', object())):
            with self.assertRaises(ErreurOrchestration): ReceptionExterne('MARCHE', b, s, table)

    def test_formes_anterieures_conservees(self):
        self.assertIsNone(ReceptionExterne('SNAPSHOT', None).octets)
        self.assertEqual(ReceptionExterne('INTERRUPTION', symbole='EURUSD').octets, b'')
        self.assertEqual(ReceptionExterne('PERMISSION', b'{}', 'EURUSD').symbole, 'EURUSD')
