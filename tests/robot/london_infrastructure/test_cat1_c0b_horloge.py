"""Catégorie 1, couche 0b : seule frontière time doublée."""
import unittest
from unittest.mock import patch
from xpbots.infra.c0b_horloge import HorlogeSysteme


class TestHorloge(unittest.TestCase):
    def test_conversion_utc_et_monotone_distinct(self):
        with patch('time.time_ns', return_value=1_234_567_890), patch('time.monotonic_ns', return_value=987):
            h = HorlogeSysteme()
            self.assertEqual(h.utc_ms(), 1234)
            self.assertEqual(h.monotone_ns(), 987)

    def test_attente_exacte_a_la_frontiere(self):
        with patch('time.sleep') as sleep:
            HorlogeSysteme().attendre_ms(100)
            sleep.assert_called_once_with(.1)

    def test_attentes_invalides(self):
        for d in (True, -1, float('nan'), float('inf'), '100'):
            with self.assertRaises(ValueError): HorlogeSysteme().attendre_ms(d)
