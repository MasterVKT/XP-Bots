"""Catégorie 2, couche 1e : issues du noyau et minuit Londres distinct de minuit UTC (C11.4)."""
from datetime import date
import unittest

from robot.outils.london import issue, parametres
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.london.c1e_quotas import QuotasLondon


class TestJonctionQuotas(unittest.TestCase):
    def test_jour_de_remplissage_londres_et_non_utc(self):
        p = parametres()
        q = QuotasLondon(p, 'EURUSD')
        cal = CalendrierLondres.depuis_parametres(p.commun)
        ancien = issue(jour=date(2026, 7, 1), heure='23:45:00')
        nouveau = issue(jour=date(2026, 7, 2), heure='00:15:00')
        self.assertEqual(cal.jour_utc(ancien.instant_ms), cal.jour_utc(nouveau.instant_ms))
        q.sur_issue(ancien)
        q.sur_issue(nouveau)
        self.assertEqual(q.etat.jour, date(2026, 7, 2))
        self.assertEqual(q.etat.remplissages, (nouveau.cle,))
