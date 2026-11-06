"""Catégorie 1, couche 1b (indicateurs) : TR, ATR Wilder et A_t = ATR de t − 1, comparés à la référence."""
import math
import unittest

import numpy as np

from reference.technical import wilder
from xpbots.donnees.c0a_types import ErreurDonneesTemps
from xpbots.donnees.c1b_indicateurs import EtatIndicateurs, avancer, etat_initial


def serie(n=60):
    bougies = []
    for i in range(n):
        base = 1.1 + 0.001 * math.sin(i / 3)
        haut, bas = base + 0.0004 + 0.0001 * (i % 4), base - 0.0003 - 0.0001 * (i % 3)
        bougies.append((haut, bas, bas + (haut - bas) * ((i % 5) / 4)))
    return bougies


class TestIndicateurs(unittest.TestCase):
    def test_wilder_trois_a_la_main(self):
        etat, atrs = etat_initial(3), []
        for tr in (1, 2, 3, 4, 5):
            resultat = avancer(etat, float(tr), 0.0, 0.0 if tr == 1 else float(tr) / 2)
            etat, _ = resultat.etat, atrs.append(resultat.atr)
        self.assertEqual(atrs[:2], [None, None])
        self.assertTrue(math.isclose(atrs[2], np.nanmean([1, 2, 3])) and atrs[2] == 2.0)

    def test_tr_et_atr_identiques_a_la_reference(self):
        bougies, etat, trs, atrs, a = serie(), etat_initial(14), [], [], []
        for haut, bas, cloture in bougies:
            resultat = avancer(etat, haut, bas, cloture)
            etat = resultat.etat
            trs.append(resultat.tr), atrs.append(resultat.atr), a.append(resultat.a)
        precedentes = [bougies[0][2]] + [b[2] for b in bougies[:-1]]
        attendus_tr = [max(h - l, abs(h - p), abs(l - p)) for (h, l, _), p in zip(bougies, precedentes)]
        self.assertEqual(trs, attendus_tr)
        reference = wilder(np.array(trs), 14)
        for i in range(len(bougies)):
            with self.subTest(i=i):
                if i < 13:
                    self.assertIsNone(atrs[i])
                else:
                    self.assertTrue(math.isclose(atrs[i], reference[i], rel_tol=1e-12))
                self.assertEqual(a[i], atrs[i - 1] if i else None, 'A_t = ATR de t − 1')

    def test_premier_tr_est_l_amplitude(self):
        self.assertEqual(avancer(etat_initial(14), 1.2, 1.0, 1.05).tr, 1.2 - 1.0)

    def test_saut_apres_fermeture_compte(self):
        etat = avancer(etat_initial(14), 1.1, 1.0, 1.05).etat
        self.assertEqual(avancer(etat, 1.3, 1.25, 1.28).tr, 1.3 - 1.05)

    def test_refus(self):
        for arguments in ((1.0, 1.1, 1.05), (1.1, 1.0, 1.2), (float('nan'), 1.0, 1.0), (True, 1.0, 1.0)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                avancer(etat_initial(14), *arguments)
        for periode in (0, True, 1.5):
            with self.subTest(periode=periode), self.assertRaises(ErreurDonneesTemps):
                etat_initial(periode)
        with self.assertRaises(ErreurDonneesTemps):
            EtatIndicateurs(2, 1.0, (0.1, 0.2), None)
        with self.assertRaises(ErreurDonneesTemps):
            avancer('etat', 1.1, 1.0, 1.05)


if __name__ == '__main__':
    unittest.main()
