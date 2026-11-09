"""Segment S2 remplacé par l'artefact `london-donnees-temps` : couture du flux de bougies dans le moteur minimal."""
import unittest

from robot.outils.configuration import configuration_figee
from xpbots.donnees.c0a_types import UniteTemps
from robot.outils.london import strategie_squelette as fabriquer_strategie
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c2_journal import TypeEnregistrement
from xpbots.orchestration.squelette import fabriquer_moteur_minimal
from xpbots.rejeu.squelette import hypotheses_marche_squelette
from robot.outils.couture_execution import composer,enregistrements

CONFIGURATION = configuration_figee()
M15 = CONFIGURATION.technique.commun.timeframe_seconds * 1000
H1 = CONFIGURATION.technique.commun.h1_seconds * 1000


def tick(instant, bid=1.1, numero=0, symbole='EURUSD'):
    return Tick(symbole, symbole, instant, instant, numero, bid, bid + 0.0001)


class StrategieEspionne:
    """Doublure du contrat structurel de stratégie : note les unités reçues, ne signale jamais."""

    identifiant = CONFIGURATION.technique.london['strategy_id']

    def __init__(self):
        self.unites = []
        self._minimale = fabriquer_strategie(CONFIGURATION)

    def sur_bougie(self, enrichie):
        self.unites.append(enrichie.unite)
        return self._minimale.sur_bougie(enrichie)

    def sur_issue(self, issue):
        self._minimale.sur_issue(issue)


def rejouer_moteur(ticks, strategie=None, horaires=None, periodes=None):
    return enregistrements(ticks,strategie or fabriquer_strategie(CONFIGURATION),CONFIGURATION,horaires,periodes)


class TestCoutureS2(unittest.TestCase):
    def test_hypothese_de_marche_sur_l_etendue_du_fichier(self):
        horaires, periodes = hypotheses_marche_squelette(
            [tick(H1 + 5), tick(3 * H1 + 7, numero=1), tick(10, symbole='GBPUSD', numero=2)], CONFIGURATION)
        self.assertEqual(periodes, {'EURUSD': (Intervalle(H1, 4 * H1),), 'GBPUSD': (Intervalle(0, H1),)})
        self.assertEqual((horaires['EURUSD'].debut_validite_ms, horaires['EURUSD'].fin_validite_ms), (H1, 5 * H1))
        self.assertEqual(hypotheses_marche_squelette([], CONFIGURATION), ({}, {}))

    def test_m15_journalisees_avec_indicateurs_h1_transmises_a_la_strategie(self):
        espion = StrategieEspionne()
        enregistrements = rejouer_moteur([tick(i * M15, 1.1 + 0.001 * i, i) for i in range(5)], espion)
        enregistrements=[e for e in enregistrements if e['type'] is TypeEnregistrement.CLOTURE]
        self.assertEqual([e['type'] for e in enregistrements], [TypeEnregistrement.CLOTURE] * 4)
        self.assertEqual({e['bougie']['duree_ms'] for e in enregistrements}, {M15})
        self.assertEqual([e['indicateurs']['rang'] for e in enregistrements], [0, 1, 2, 3])
        self.assertAlmostEqual(enregistrements[1]['indicateurs']['tr'], 0.001, places=12)
        self.assertEqual(espion.unites, [UniteTemps.M15] * 3 + [UniteTemps.H1, UniteTemps.M15])

    def test_bougie_sans_tick_journalisee_invalide_p02(self):
        enregistrements = rejouer_moteur([tick(0), tick(2 * M15 + 3, numero=1), tick(3 * M15, numero=2)])
        enregistrements=[e for e in enregistrements if e['type'] is TypeEnregistrement.CLOTURE]
        self.assertEqual([(e['bougie']['debut_utc_ms'], e['bougie']['valide'], e['bougie']['motif_invalidite'],
                           e['indicateurs']) for e in enregistrements][1], (M15, False, 'AUCUN_BID', {}))
        self.assertEqual(len(enregistrements), 3)

    def test_trou_signale_par_des_alertes(self):
        ticks = [tick(i * M15, numero=i) for i in range(6)]
        horaires, _ = hypotheses_marche_squelette(ticks, CONFIGURATION)
        periodes = {'EURUSD': (Intervalle(0, 2 * M15), Intervalle(3 * M15, H1 + H1))}
        enregistrements = rejouer_moteur(ticks, horaires=horaires, periodes=periodes)
        alertes = [(e['alerte'], e['nature'], e['intervalle_utc_ms']) for e in enregistrements
                   if e['type'] is TypeEnregistrement.ALERTE]
        self.assertEqual(alertes, [('DATA_GAP', 'DEBUT', 2 * M15), ('DATA_GAP', 'FIN', 3 * M15)])
        self.assertEqual([e['bougie']['motif_invalidite'] for e in enregistrements if e['type'] is TypeEnregistrement.CLOTURE],
                         [None, None, 'TROU_DONNEES', None, None])

    def test_refus_de_la_couture(self):
        ticks = [tick(0), tick(M15, numero=1)]
        horaires, periodes = hypotheses_marche_squelette(ticks, CONFIGURATION)
        with self.assertRaises(ValueError):
            composer(ticks,fabriquer_strategie(CONFIGURATION),horaires=horaires,periodes={})
        moteur,_,_ = composer(ticks)
        with self.assertRaises(ValueError):
            moteur.traiter_tick(tick(5, symbole='GBPUSD'))

        class Muette:
            identifiant = 'MUETTE'

            def sur_bougie(self, enrichie):
                return None

        class Bavarde(StrategieEspionne):
            def sur_bougie(self, enrichie):
                return self._minimale.sur_bougie(enrichie.__class__(enrichie.bougie, UniteTemps.M15, enrichie.indicateurs,
                                                                    enrichie.jour_londres, enrichie.ouverture_locale,
                                                                    enrichie.cloture_locale, enrichie.jour_utc))

        for strategie, suite in ((Muette(), ticks), (Bavarde(), [tick(i * M15, numero=i) for i in range(5)])):
            with self.subTest(strategie=type(strategie).__name__), self.assertRaises(ValueError):
                rejouer_moteur(suite, strategie)


if __name__ == '__main__':
    unittest.main()
