"""Couche 1c — `indicateurs` : récurrences de C03, concordance avec `reference.technical`, export et import."""
import importlib.util
import math
import random
import unittest

from xpbots.donnees_temps.c1c_indicateurs import (CLE_TR, EtatATR, EtatEMA, EtatRSI, EtatWilder, ValeurInvalide,
                                                  cle_atr, cle_ema, cle_ema_decalee, cle_rsi)

REFERENCE_DISPONIBLE = all(importlib.util.find_spec(nom) for nom in ('numpy', 'pandas'))


def serie_ohlc(longueur=400, graine=11):
    alea = random.Random(graine)
    c, barres = 1.1, []
    for _ in range(longueur):
        o = c
        c = round(o + alea.uniform(-0.0012, 0.0012), 5)
        h = round(max(o, c) + alea.uniform(0, 0.0006), 5)
        l = round(min(o, c) - alea.uniform(0, 0.0006), 5)  # noqa: E741
        barres.append((o, h, l, c))
    return barres


def proche(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-15)


class TestRecurrences(unittest.TestCase):
    def test_ema_graine_puis_recurrence(self):
        e = EtatEMA(3)
        self.assertIsNone(e.maj(1.0))
        self.assertIsNone(e.maj(2.0))
        self.assertEqual(e.maj(6.0), 3.0)
        self.assertEqual(e.maj(7.0), 3.0 + 2 / 4 * (7.0 - 3.0))

    def test_wilder(self):
        w = EtatWilder(2)
        self.assertIsNone(w.maj(1.0))
        self.assertEqual(w.maj(3.0), 2.0)
        self.assertEqual(w.maj(4.0), (1 * 2.0 + 4.0) / 2)

    def test_rsi_cas_nuls(self):
        for closes, attendu in (([1.1] * 20, 50.0), ([1.0 + i * 0.001 for i in range(20)], 100.0),
                                ([2.0 - i * 0.001 for i in range(20)], 0.0)):
            r = EtatRSI(14)
            valeurs = [r.maj(c) for c in closes]
            with self.subTest(attendu=attendu):
                self.assertTrue(all(v is None for v in valeurs[:14]))
                self.assertEqual(valeurs[14], attendu)

    def test_tr_premiere_bougie_et_a_t(self):
        a = EtatATR(2)
        m1 = a.maj(1.2, 1.0, 1.1)
        self.assertEqual((m1.tr, m1.atr, m1.a_t), (1.2 - 1.0, None, None))
        m2 = a.maj(1.5, 1.3, 1.4)
        self.assertEqual(m2.tr, max(1.5 - 1.3, abs(1.5 - 1.1), abs(1.3 - 1.1)))
        self.assertIsNone(m2.a_t)
        m3 = a.maj(1.45, 1.35, 1.4)
        self.assertEqual(m3.a_t, m2.atr)  # A_t = ATR de la bougie précédente

    def test_entrees_invalides(self):
        for appel in (lambda: EtatEMA(0), lambda: EtatEMA(2.0), lambda: EtatEMA(3).maj(1),
                      lambda: EtatEMA(3).maj(float('nan')), lambda: EtatATR(3).maj(1.0, 1.2, 1.1),
                      lambda: EtatRSI(3).maj(float('inf'))):
            with self.assertRaises(ValeurInvalide):
                appel()

    def test_noms_des_indicateurs(self):
        self.assertEqual((cle_ema(15), cle_ema_decalee(50, 4), cle_rsi(14), cle_atr(14), CLE_TR),
                         ('ema_15', 'ema_50_t_moins_4', 'rsi_14', 'atr_14', 'tr'))


class TestExportImport(unittest.TestCase):
    def test_reprise_identique_au_flux_continu(self):
        barres = serie_ohlc(200)
        continus = [EtatEMA(15), EtatRSI(14), EtatATR(14)]
        coupes = [EtatEMA(15), EtatRSI(14), EtatATR(14)]

        def pas(etats, b):
            return (etats[0].maj(b[3]), etats[1].maj(b[3]), etats[2].maj(b[1], b[2], b[3]))

        sorties_continues = [pas(continus, b) for b in barres]
        sorties = [pas(coupes, b) for b in barres[:7]]  # avant la fin des graines
        coupes = [type(e).importer(e.exporter()) for e in coupes]
        sorties += [pas(coupes, b) for b in barres[7:120]]
        coupes = [type(e).importer(e.exporter()) for e in coupes]
        sorties += [pas(coupes, b) for b in barres[120:]]
        self.assertEqual(sorties, sorties_continues)

    def test_etat_incoherent_refuse(self):
        etat = EtatEMA(3).exporter()
        for altere in (dict(etat, n=0), dict(etat, valeur=1.0, graine=[1.0]), {'n': 3}, dict(etat, valeur=1),
                       dict(etat, graine=[1.0, 2.0, 3.0])):
            with self.subTest(altere=altere), self.assertRaises(ValeurInvalide):
                EtatEMA.importer(altere)


@unittest.skipUnless(REFERENCE_DISPONIBLE, 'numpy et pandas requis par reference.technical')
class TestConcordanceReference(unittest.TestCase):
    def test_ema_rsi_wilder_tr_atr(self):
        import numpy as np
        import pandas as pd
        from reference import technical
        barres = serie_ohlc(400)
        closes = [b[3] for b in barres]
        for n in (15, 25, 50):
            ref = technical.ema(closes, n)
            e = EtatEMA(n)
            for i, c in enumerate(closes):
                v = e.maj(c)
                with self.subTest(n=n, i=i):
                    self.assertEqual(v is None, bool(np.isnan(ref[i])))
                    if v is not None:
                        self.assertTrue(proche(v, ref[i]))
        ref_rsi = technical.rsi(closes, 14)
        r = EtatRSI(14)
        for i, c in enumerate(closes):
            v = r.maj(c)
            self.assertEqual(v is None, bool(np.isnan(ref_rsi[i])))
            if v is not None:
                self.assertTrue(proche(v, ref_rsi[i]))
        df = technical.add_indicators(pd.DataFrame(barres, columns=['O', 'H', 'L', 'C']))
        a = EtatATR(14)
        for i, (o, h, l, c) in enumerate(barres):  # noqa: E741
            m = a.maj(h, l, c)
            self.assertTrue(proche(m.tr, df.TR.iloc[i]))
            self.assertEqual(m.atr is None, bool(np.isnan(df.ATR.iloc[i])))
            if m.atr is not None:
                self.assertTrue(proche(m.atr, df.ATR.iloc[i]))
            self.assertEqual(m.a_t is None, bool(np.isnan(df.A.iloc[i])))
            if m.a_t is not None:
                self.assertTrue(proche(m.a_t, df.A.iloc[i]))

    def test_memes_comparaisons_de_seuil_que_la_reference(self):
        import numpy as np
        from reference import technical
        for graine in range(5):
            closes = [b[3] for b in serie_ohlc(600, graine)]
            ref = {n: technical.ema(closes, n) for n in (15, 25, 50)}
            ref_rsi = technical.rsi(closes, 14)
            emas = {n: EtatEMA(n) for n in (15, 25, 50)}
            r = EtatRSI(14)
            for i, c in enumerate(closes):
                v = {n: emas[n].maj(c) for n in emas}
                rsi = r.maj(c)
                if i < 50:
                    continue
                with self.subTest(graine=graine, i=i):
                    self.assertEqual(v[15] > v[25] > v[50], bool(ref[15][i] > ref[25][i] > ref[50][i]))
                    self.assertEqual(c > v[15], bool(c > ref[15][i]))
                    for seuil in (40, 50, 60):
                        self.assertEqual(rsi >= seuil, bool(ref_rsi[i] >= seuil))
                        self.assertFalse(np.isnan(ref_rsi[i]))


if __name__ == '__main__':
    unittest.main()
