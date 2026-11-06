"""Catégorie 2, couche 1b : configuration et calendrier réels, réception du gel et changement d'heure."""
from datetime import date, time
import unittest

from robot.outils.london import bougie, parametres
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c1b_gel_atr_h1 import construire_gel


class TestJonctionGel(unittest.TestCase):
    def test_gel_en_utc_ete_hiver_et_prechargement_configurable(self):
        p = parametres(lambda j: j['common'].__setitem__('warmup_closed_h1_bars', 16))
        cal = CalendrierLondres.depuis_parametres(p.commun)
        for jour, heure_utc in ((date(2026, 1, 12), 7), (date(2026, 7, 1), 6)):
            h = bougie(p=p, jour=jour, heure='06:00:00', unite=UniteTemps.H1, rang=15)
            gel = construire_gel(jour, [h], p)
            self.assertEqual(gel.fin_h1_ms, cal.instant_local(jour, p.range_h1_atr_frozen_local))
            self.assertEqual((gel.fin_h1_ms // 3600000) % 24, heure_utc)
