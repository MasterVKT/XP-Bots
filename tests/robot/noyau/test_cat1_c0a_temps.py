"""Catégorie 1, couche 0a (instant) : contrat propre de l'unité, comparé à `utc()` de la référence."""
from datetime import datetime, timedelta, timezone
import unittest
from zoneinfo import ZoneInfo

from reference.llm_contracts import utc
from xpbots.noyau.c0a_temps import (CleEvenement, ErreurInstant, aligner, instant_depuis_datetime,
                                    instant_depuis_iso, instant_vers_datetime, instant_vers_iso, verifier_instant)


class TestInstant(unittest.TestCase):
    def test_texte_iso_utc(self):
        self.assertEqual(instant_depuis_iso('1970-01-01T00:00:00Z'), 0)
        self.assertEqual(instant_depuis_iso('2026-07-15T07:00:00.250Z'), 1784098800250)
        self.assertEqual(instant_depuis_iso('2026-07-15T07:00:00+00:00'), 1784098800000)

    def test_meme_refus_que_la_reference(self):
        for texte in ('2026-07-15T07:00:00', '2026-07-15T08:00:00+01:00', '2026-07-15T07:00:00-00:30'):
            with self.subTest(texte=texte):
                with self.assertRaises(ValueError):
                    utc(texte)
                with self.assertRaises(ErreurInstant):
                    instant_depuis_iso(texte)
        for texte in ('2026-07-15T07:00:00Z', '2026-01-14T23:59:59.999+00:00'):
            with self.subTest(texte=texte):
                attendu = (utc(texte) - datetime(1970, 1, 1, tzinfo=timezone.utc)) // timedelta(milliseconds=1)
                self.assertEqual(instant_depuis_iso(texte), attendu)

    def test_refus_divers(self):
        for valeur in ('demain', 12, None):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurInstant):
                instant_depuis_iso(valeur)
        with self.assertRaises(ErreurInstant):
            instant_depuis_iso('2026-07-15T07:00:00.000500Z')
        with self.assertRaises(ErreurInstant):
            instant_depuis_datetime(datetime(2026, 7, 15, 7))
        for valeur in (-1, 1.0, True, '5'):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurInstant):
                verifier_instant(valeur)

    def test_datetime_conscient_de_tout_fuseau(self):
        londres = datetime(2026, 7, 15, 8, 0, tzinfo=ZoneInfo('Europe/London'))
        self.assertEqual(instant_depuis_datetime(londres), instant_depuis_iso('2026-07-15T07:00:00Z'))
        hiver = datetime(2026, 1, 14, 8, 0, tzinfo=ZoneInfo('Europe/London'))
        self.assertEqual(instant_depuis_datetime(hiver), instant_depuis_iso('2026-01-14T08:00:00Z'))

    def test_aller_retour_texte(self):
        for texte in ('2026-07-15T07:00:00.250Z', '1970-01-01T00:00:00.000Z', '2027-12-31T23:59:59.999Z'):
            with self.subTest(texte=texte):
                self.assertEqual(instant_vers_iso(instant_depuis_iso(texte)), texte)
        self.assertEqual(instant_vers_datetime(1500), datetime(1970, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc))

    def test_alignement(self):
        quinze = 900_000
        self.assertEqual(aligner(0, quinze), 0)
        self.assertEqual(aligner(quinze - 1, quinze), 0)
        self.assertEqual(aligner(quinze, quinze), quinze, 'le tick de frontière appartient à la bougie suivante')
        self.assertEqual(aligner(instant_depuis_iso('2026-07-15T07:14:59.999Z'), quinze),
                         instant_depuis_iso('2026-07-15T07:00:00Z'))
        for duree in (0, -900_000, 900.0, True):
            with self.subTest(duree=duree), self.assertRaises(ErreurInstant):
                aligner(0, duree)

    def test_cle_evenement(self):
        cles = [CleEvenement(10, 2), CleEvenement(5, 9), CleEvenement(10, 1)]
        self.assertEqual(sorted(cles), [CleEvenement(5, 9), CleEvenement(10, 1), CleEvenement(10, 2)])
        with self.assertRaises(ErreurInstant):
            CleEvenement(10, -1)
        with self.assertRaises(Exception):
            cles[0].numero = 3


if __name__ == '__main__':
    unittest.main()
