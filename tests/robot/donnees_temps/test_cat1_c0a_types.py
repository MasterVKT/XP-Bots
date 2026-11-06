"""Catégorie 1, couche 0a (types_donnees) : contrat propre des objets intermédiaires du flux."""
from datetime import date, datetime, timezone
import unittest

from robot.outils.configuration import configuration_figee
from xpbots.donnees.c0a_types import (AnomalieDonnees, BougieEnrichie, ChangementTrou, ErreurDonneesTemps,
                                      IdentitePrechargement, IndicateursBougie, NatureTrou, StatutCouverture, UniteTemps)
from xpbots.noyau.c1a_marche import Bougie

COMMUN = configuration_figee().technique.commun
VALIDE = Bougie('EURUSD', 900_000, 900_000, 1.1, 1.2, 1.0, 1.15, 4, True, None, 1_800_000)
INVALIDE = Bougie('EURUSD', 900_000, 900_000, None, None, None, None, 0, False, 'AUCUN_BID', 1_800_000)
LOCAL = datetime(1970, 1, 1, 0, 15, tzinfo=timezone.utc)


class TestTypes(unittest.TestCase):
    def test_unites_lisent_la_configuration(self):
        self.assertEqual(UniteTemps.M15.duree_ms(COMMUN), COMMUN.timeframe_seconds * 1000)
        self.assertEqual(UniteTemps.H1.duree_ms(COMMUN), COMMUN.h1_seconds * 1000)
        self.assertEqual({s.value for s in StatutCouverture}, {'COUVERT', 'FERMETURE_OFFICIELLE', 'TROU', 'INCONNU'})

    def test_changement_et_anomalie(self):
        self.assertIs(ChangementTrou('EURUSD', 'DEBUT', 900_000, 1_800_000).nature, NatureTrou.DEBUT)
        for arguments in (('', 'DEBUT', 0, 0), ('EURUSD', 'MILIEU', 0, 0), ('EURUSD', 'FIN', -1, 0)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                ChangementTrou(*arguments)
        with self.assertRaises(ErreurDonneesTemps):
            AnomalieDonnees('EURUSD', '', 0)

    def test_indicateurs(self):
        self.assertEqual(IndicateursBougie(1, None, None, 0).tr, 1.0)
        for arguments in ((-0.1, None, None, 0), (0.1, float('nan'), None, 0), (0.1, 0.2, -1, 0), (0.1, 0.2, 0.2, -1),
                          (True, None, None, 0)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                IndicateursBougie(*arguments)

    def test_identite(self):
        self.assertEqual(IdentitePrechargement(None, 0, '0' * 64).nombre, 0)
        for arguments in ((None, 2, '0' * 64), (5, 0, '0' * 64), (5, 1, 'abc'), (-1, 1, '0' * 64)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                IdentitePrechargement(*arguments)

    def test_bougie_enrichie(self):
        indicateurs = IndicateursBougie(0.2, 0.15, 0.14, 999)
        enrichie = BougieEnrichie(VALIDE, 'M15', indicateurs, date(1970, 1, 1), LOCAL, LOCAL, date(1970, 1, 1))
        self.assertIs(enrichie.unite, UniteTemps.M15)
        self.assertIsNone(BougieEnrichie(INVALIDE, 'H1', None, date(1970, 1, 1), LOCAL, LOCAL, date(1970, 1, 1)).indicateurs)
        for arguments in ((VALIDE, 'M15', None), (INVALIDE, 'M15', indicateurs), (VALIDE, 'M5', indicateurs),
                          ('bougie', 'M15', indicateurs)):
            with self.subTest(arguments=arguments[1:]), self.assertRaises(ErreurDonneesTemps):
                BougieEnrichie(*arguments, date(1970, 1, 1), LOCAL, LOCAL, date(1970, 1, 1))
        with self.assertRaises(ErreurDonneesTemps):
            BougieEnrichie(VALIDE, 'M15', indicateurs, date(1970, 1, 1), datetime(1970, 1, 1), LOCAL, date(1970, 1, 1))
        with self.assertRaises(ErreurDonneesTemps):
            BougieEnrichie(VALIDE, 'M15', indicateurs, LOCAL, LOCAL, LOCAL, date(1970, 1, 1))


if __name__ == '__main__':
    unittest.main()
