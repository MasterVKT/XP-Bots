"""Couche 1a — `sessions_londres` : Europe/London avec changements d'heure, jours actifs, fenêtres, blackout."""
import importlib.util
import json
import unittest
from datetime import date, datetime, timedelta, timezone

from xpbots.donnees_temps.c0_parametres_seances import ParametresTechniques, charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import HeureLocaleInvalide, SessionsLondres
from xpbots.noyau.config import charger_bundle_technique
from robot.outils import RACINE

M15 = 900_000
REFERENCE_DISPONIBLE = all(importlib.util.find_spec(nom) for nom in ('numpy', 'pandas'))


def ms(annee, mois, jour, heure=0, minute=0, seconde=0, milli=0):
    return int(datetime(annee, mois, jour, heure, minute, seconde, milli * 1000,
                        tzinfo=timezone.utc).timestamp() * 1000)


class TestSessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = charger_bundle_technique()
        cls.sessions = SessionsLondres(charger_parametres_techniques(cls.bundle))
        ema = cls.bundle.donnees['ema']
        cls.debut, cls.fin = ema['session_start_local'], ema['entry_end_local_exclusive']

    def fenetre(self, ouverture):
        return self.sessions.dans_fenetre(ouverture, ouverture + M15, self.debut, self.fin)

    def test_premiere_et_derniere_cloture_en_hiver(self):
        self.assertTrue(self.fenetre(ms(2026, 3, 27, 8, 0)))        # vendredi GMT : 08:00–08:15 Londres
        self.assertFalse(self.fenetre(ms(2026, 3, 27, 7, 45)))
        self.assertTrue(self.fenetre(ms(2026, 3, 27, 15, 30)))      # dernière clôture admissible 15:45
        self.assertFalse(self.fenetre(ms(2026, 3, 27, 15, 45)))     # clôture exactement à 16:00 : exclue

    def test_passage_a_l_heure_d_ete(self):
        # Lundi 30 mars 2026, BST : 08:00 Londres = 07:00 UTC.
        self.assertTrue(self.fenetre(ms(2026, 3, 30, 7, 0)))
        self.assertFalse(self.fenetre(ms(2026, 3, 30, 6, 45)))
        self.assertTrue(self.fenetre(ms(2026, 3, 30, 14, 30)))
        self.assertFalse(self.fenetre(ms(2026, 3, 30, 14, 45)))
        self.assertEqual(self.sessions.instant_local(date(2026, 3, 30), '08:00:00'), ms(2026, 3, 30, 7))
        self.assertEqual(self.sessions.instant_local(date(2026, 3, 27), '08:00:00'), ms(2026, 3, 27, 8))

    def test_retour_a_l_heure_d_hiver_2025(self):
        self.assertTrue(self.fenetre(ms(2025, 10, 24, 7, 0)))       # vendredi BST
        self.assertTrue(self.fenetre(ms(2025, 10, 27, 8, 0)))       # lundi GMT
        self.assertFalse(self.fenetre(ms(2025, 10, 27, 7, 0)))
        self.assertEqual(self.sessions.instant_local(date(2025, 10, 27), '16:00:00'), ms(2025, 10, 27, 16))

    def test_aucune_entree_le_week_end(self):
        for ouverture in (ms(2026, 3, 28, 10), ms(2026, 3, 29, 10), ms(2026, 10, 25, 10)):
            with self.subTest(ouverture=ouverture):
                self.assertFalse(self.fenetre(ouverture))
        self.assertFalse(self.sessions.jour_actif(date(2026, 11, 8)))
        self.assertTrue(self.sessions.jour_actif(date(2026, 11, 9)))

    def test_jour_utc_distinct_du_jour_londres(self):
        instant = ms(2026, 6, 1, 23, 30)
        self.assertEqual(self.sessions.jour_utc(instant), date(2026, 6, 1))
        self.assertEqual(self.sessions.jour_londres(instant), date(2026, 6, 2))
        hiver = ms(2026, 1, 5, 23, 30)
        self.assertEqual(self.sessions.jour_londres(hiver), self.sessions.jour_utc(hiver))

    def test_bougie_a_cheval_sur_minuit_exclue(self):
        ouverture = ms(2026, 1, 5, 23, 45)
        self.assertFalse(self.sessions.dans_fenetre(ouverture, ouverture + M15, '00:00:00', '23:59:59'))
        with self.assertRaises(ValueError):
            self.sessions.dans_fenetre(ouverture, ouverture, '00:00:00', '23:59:59')

    def test_heures_locales_inexistantes_ou_ambigues(self):
        with self.assertRaises(HeureLocaleInvalide):
            self.sessions.instant_local(date(2026, 3, 29), '01:30:00')
        with self.assertRaises(HeureLocaleInvalide):
            self.sessions.instant_local(date(2026, 10, 25), '01:30:00')

    def test_blackout_debut_inclus_fin_exclue(self):
        s = self.sessions
        self.assertTrue(s.dans_blackout(ms(2026, 11, 4, 21, 0)))
        self.assertTrue(s.dans_blackout(ms(2026, 11, 4, 22, 59, 59, 999)))
        self.assertFalse(s.dans_blackout(ms(2026, 11, 4, 23, 0)))
        self.assertFalse(s.dans_blackout(ms(2026, 11, 4, 20, 59, 59, 999)))

    def test_blackout_a_cheval_sur_minuit(self):
        bloc = json.loads((RACINE / 'config' / 'parametres_figes_v3.json').read_text(encoding='utf-8'))['common']
        bloc['rollover_blackout_utc_start'], bloc['rollover_blackout_utc_end'] = '23:00:00', '01:00:00'
        s = SessionsLondres(ParametresTechniques(bloc, self.bundle.empreinte))
        self.assertTrue(s.dans_blackout(ms(2026, 11, 4, 23, 30)))
        self.assertTrue(s.dans_blackout(ms(2026, 11, 5, 0, 30)))
        self.assertFalse(s.dans_blackout(ms(2026, 11, 5, 1, 0)))

    @unittest.skipUnless(REFERENCE_DISPONIBLE, 'pandas requis par reference.technical')
    def test_concordance_avec_la_reference_autour_des_changements_d_heure(self):
        import pandas as pd
        from reference import technical
        for debut in (date(2025, 3, 24), date(2025, 10, 20), date(2026, 3, 23), date(2026, 10, 19)):
            for cfg in (technical.EMA, technical.LONDON_CFG):
                origine = ms(debut.year, debut.month, debut.day)
                for i in range(14 * 96):
                    ouverture = origine + i * M15
                    attendu = technical.local_decision_in_window(
                        pd.Timestamp(ouverture, unit='ms', tz='UTC'),
                        pd.Timestamp(ouverture + M15, unit='ms', tz='UTC'), cfg)
                    obtenu = self.sessions.dans_fenetre(ouverture, ouverture + M15, cfg['session_start_local'],
                                                        cfg['entry_end_local_exclusive'])
                    if obtenu != attendu:
                        self.fail(f'écart à {datetime.fromtimestamp(ouverture / 1000, timezone.utc)} '
                                  f'({cfg["strategy_id"]}) : {obtenu} au lieu de {attendu}')


if __name__ == '__main__':
    unittest.main()
