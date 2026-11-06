"""Catégorie 1, couche 0b (sessions_londres) : Londres et UTC, range, fenêtre de la référence, blackout."""
from datetime import date, datetime, time, timedelta, timezone
import unittest

import pandas as pd

from reference.technical import LONDON_CFG, local_decision_in_window
from robot.outils.configuration import configuration_figee
from xpbots.donnees.c0b_sessions import CalendrierLondres, ErreurSessions
from xpbots.noyau.c0a_temps import instant_depuis_iso

CONFIGURATION = configuration_figee()
COMMUN = CONFIGURATION.technique.commun
LONDON = CONFIGURATION.technique.london
CALENDRIER = CalendrierLondres.depuis_parametres(COMMUN)
M15 = COMMUN.timeframe_seconds * 1000
HEURE = time.fromisoformat


class TestLondresEtUtc(unittest.TestCase):
    def test_jours_de_reference_de_check_technical(self):
        for local, heure_utc in (('2026-03-30', 7), ('2026-10-26', 8), ('2026-07-01', 7), ('2026-01-12', 8)):
            with self.subTest(jour=local):
                instant = CALENDRIER.instant_local(date.fromisoformat(local), time(8))
                self.assertEqual(datetime.fromtimestamp(instant / 1000, timezone.utc).hour, heure_utc)

    def test_vingt_ouvertures_du_range_ete_et_hiver(self):
        for jour in (date(2026, 7, 1), date(2026, 1, 12), date(2019, 3, 29), date(2027, 10, 29)):
            with self.subTest(jour=jour):
                ouvertures = CALENDRIER.ouvertures(jour, HEURE(LONDON['range_start_local']),
                                                   HEURE(LONDON['range_end_local_exclusive']), M15)
                self.assertEqual(len(ouvertures), LONDON['expected_range_m15_bars'])
                self.assertEqual(CALENDRIER.datetime_local(ouvertures[0]).time(), HEURE(LONDON['range_start_local']))

    def test_changements_d_heure_le_dimanche_a_01h_utc(self):
        moment = datetime(2019, 1, 1, tzinfo=timezone.utc)
        decalage = CALENDRIER.datetime_local(int(moment.timestamp() * 1000)).utcoffset()
        changements = []
        while moment.year < 2028:
            courant = CALENDRIER.datetime_local(int(moment.timestamp() * 1000)).utcoffset()
            if courant != decalage:
                changements.append(moment)
                decalage = courant
            moment += timedelta(hours=1)
        self.assertEqual(len(changements), 18)
        for changement in changements:
            with self.subTest(changement=changement):
                self.assertEqual((changement.weekday(), changement.hour), (6, 1))
                self.assertFalse(CALENDRIER.jour_actif(CALENDRIER.jour_local(int(changement.timestamp() * 1000))))

    def test_heure_inexistante_ou_ambigue_refusee(self):
        for jour in (date(2026, 3, 29), date(2026, 10, 25)):
            with self.subTest(jour=jour), self.assertRaises(ErreurSessions):
                CALENDRIER.instant_local(jour, time(1, 30))
        self.assertEqual(CALENDRIER.instant_local(date(2026, 3, 29), time(2, 0)), instant_depuis_iso('2026-03-29T01:00:00Z'))

    def test_jour_utc_distinct_du_jour_londres(self):
        instant = instant_depuis_iso('2026-07-14T23:30:00Z')
        self.assertEqual((CALENDRIER.jour_utc(instant), CALENDRIER.jour_local(instant)), (date(2026, 7, 14), date(2026, 7, 15)))


class TestFenetreDeDecision(unittest.TestCase):
    def test_bornes_de_la_methode(self):
        jour = date(2026, 7, 15)
        debut, fin = HEURE(LONDON['session_start_local']), HEURE(LONDON['entry_end_local_exclusive'])
        ouverture = CALENDRIER.instant_local(jour, debut)
        self.assertTrue(CALENDRIER.decision_dans_fenetre(ouverture, ouverture + M15, debut, fin), 'première clôture 08:15')
        derniere = CALENDRIER.instant_local(jour, fin) - M15
        self.assertFalse(CALENDRIER.decision_dans_fenetre(derniere, derniere + M15, debut, fin), 'clôture à 11:00 exclue')
        self.assertTrue(CALENDRIER.decision_dans_fenetre(derniere - M15, derniere, debut, fin), 'dernière clôture 10:45')

    def test_egalite_avec_local_decision_in_window_de_2019_a_2027(self):
        debut, fin = HEURE(LONDON['session_start_local']), HEURE(LONDON['entry_end_local_exclusive'])
        jour, comptes = date(2019, 1, 1), 0
        while jour <= date(2027, 12, 31):
            proche_changement = jour.month in (3, 10) and jour.day >= 22
            if proche_changement or jour.toordinal() % 5 == 0:
                minuit = pd.Timestamp(jour.isoformat(), tz='UTC')
                for quart in range(20, 52):
                    ouverture = minuit + pd.Timedelta(minutes=15 * quart)
                    cloture = ouverture + pd.Timedelta(minutes=15)
                    attendu = local_decision_in_window(ouverture, cloture, LONDON_CFG)
                    obtenu = CALENDRIER.decision_dans_fenetre(ouverture.value // 1_000_000, cloture.value // 1_000_000, debut, fin)
                    if attendu != obtenu:
                        self.fail(f'écart à {ouverture} : référence {attendu}, robot {obtenu}')
                    comptes += 1
            jour += timedelta(days=1)
        self.assertGreater(comptes, 20_000)


class TestBlackout(unittest.TestCase):
    def test_intervalle_utc_et_prochain_debut(self):
        jour = '2026-07-15T'
        self.assertFalse(CALENDRIER.dans_blackout(instant_depuis_iso(jour + '20:59:59.999Z')))
        self.assertTrue(CALENDRIER.dans_blackout(instant_depuis_iso(jour + '21:00:00Z')))
        self.assertTrue(CALENDRIER.dans_blackout(instant_depuis_iso(jour + '22:59:59.999Z')))
        self.assertFalse(CALENDRIER.dans_blackout(instant_depuis_iso(jour + '23:00:00Z')))
        self.assertEqual(CALENDRIER.prochain_debut_blackout(instant_depuis_iso(jour + '10:00:00Z')),
                         instant_depuis_iso(jour + '21:00:00Z'))
        self.assertEqual(CALENDRIER.prochain_debut_blackout(instant_depuis_iso(jour + '21:00:00Z')),
                         instant_depuis_iso(jour + '21:00:00Z'))
        self.assertEqual(CALENDRIER.prochain_debut_blackout(instant_depuis_iso(jour + '21:00:00.001Z')),
                         instant_depuis_iso('2026-07-16T21:00:00Z'))

    def test_blackout_qui_passe_minuit(self):
        calendrier = CalendrierLondres('Europe/London', (0, 1, 2, 3, 4), time(23), time(1))
        self.assertTrue(calendrier.dans_blackout(instant_depuis_iso('2026-07-15T00:30:00Z')))
        self.assertFalse(calendrier.dans_blackout(instant_depuis_iso('2026-07-15T01:00:00Z')))

    def test_refus(self):
        for arguments in (('Europe/Paris_inconnue', (0,), time(21), time(23)), ('Europe/London', (7,), time(21), time(23)),
                          ('Europe/London', (), time(21), time(23)), ('Europe/London', (0,), time(21), time(21))):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurSessions):
                CalendrierLondres(*arguments)
        with self.assertRaises(ErreurSessions):
            CALENDRIER.ouvertures(date(2026, 7, 15), time(2), time(7, 5), M15)
        with self.assertRaises(ErreurSessions):
            CALENDRIER.jour_local(-1)


if __name__ == '__main__':
    unittest.main()
