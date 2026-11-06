"""Segments S3 et S4 : stratégie minimale, coordinateur minimal et enchaînement du moteur minimal."""
from datetime import date, datetime, timezone
from decimal import Decimal
import unittest

from robot.outils.configuration import configuration_figee, octets_exports, octets_technique_modifies
from robot.outils.specification import motifs_admis
from xpbots.donnees.c0a_types import BougieEnrichie, IndicateursBougie, UniteTemps
from xpbots.execution.squelette import CommandeEntree, CoordinateurMinimal
from xpbots.london.squelette import StrategieMinimale, fabriquer_strategie
from xpbots.noyau.c0c_configuration import ConfigurationFigee, analyser_export_ia, analyser_export_technique
from xpbots.noyau.c1a_marche import Bougie, Tick
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, Motif, SignalTechnique
from xpbots.noyau.c2_journal import TypeEnregistrement
from xpbots.orchestration.squelette import fabriquer_moteur_minimal
from xpbots.rejeu.squelette import hypotheses_marche_squelette

CONFIGURATION = configuration_figee()
DUREE = CONFIGURATION.technique.commun.timeframe_seconds * 1000
IDENTIFIANT = CONFIGURATION.technique.london['strategy_id']


class StrategieQuiSignale:
    """Doublure de test du contrat structurel de stratégie : rend un signal d'achat à chaque M15 close."""

    identifiant = 'TEST'

    def sur_bougie(self, enrichie):
        if enrichie.unite is not UniteTemps.M15:
            return None
        bougie = enrichie.bougie
        return SignalTechnique('TEST', bougie.symbole, bougie.fin_ms, 'ACHAT', bougie.cloture, 0.001,
                               bougie.cloture - 0.002, 2.0)


def ticks(espacement, nombre=10):
    return [Tick('EURUSD', 'EURUSD', i * espacement, i * espacement, i, 1.0 + i / 1024, 1.0 + i / 1024 + 0.0001)
            for i in range(nombre)]


def moteur_sur(strategie, configuration, suite):
    horaires, periodes = hypotheses_marche_squelette(suite, configuration)
    return fabriquer_moteur_minimal(strategie, configuration, 'REJEU', horaires=horaires, periodes_couvertes=periodes)


def enrichie(unite, duree):
    utc = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return BougieEnrichie(Bougie('EURUSD', 0, duree, 1.0, 1.0, 1.0, 1.0, 1, True, None, duree), unite,
                          IndicateursBougie(0.0, None, None, 0), date(1970, 1, 1), utc, utc, date(1970, 1, 1))


class TestStrategieEtCoordinateur(unittest.TestCase):
    def test_strategie_minimale(self):
        strategie = fabriquer_strategie(CONFIGURATION)
        self.assertEqual(strategie.identifiant, IDENTIFIANT)
        self.assertIsNone(strategie.sur_bougie(enrichie(UniteTemps.H1, 4 * DUREE)), 'rien pour une H1')
        resultat = strategie.sur_bougie(enrichie(UniteTemps.M15, DUREE))
        self.assertIsInstance(resultat, AbsenceDeSignal)
        self.assertEqual((resultat.motif, resultat.detail, resultat.cloture_ms), (Motif.NO_SETUP, 'SEGMENT_MINIMAL_S3', DUREE))
        self.assertIn(resultat.motif, motifs_admis())
        with self.assertRaises(ValueError):
            StrategieMinimale('')

    def test_coordinateur_refuse_tout_signal(self):
        coordinateur = CoordinateurMinimal()
        sans_signal = AbsenceDeSignal(IDENTIFIANT, 'EURUSD', DUREE, 'NO_SETUP', 'SEGMENT_MINIMAL_S3')
        self.assertEqual(coordinateur.decider(sans_signal).motif, Motif.NO_SETUP)
        for sens, stop in (('ACHAT', 1.09), ('VENTE', 1.11)):
            decision = coordinateur.decider(SignalTechnique(IDENTIFIANT, 'EURUSD', DUREE, sens, 1.1, 0.001, stop, 2.0))
            self.assertEqual((decision.motif, decision.detail, decision.commandes),
                             (Motif.ENVIRONMENT_NOT_READY, 'SEGMENT_MINIMAL_S4', ()))
        with self.assertRaises(TypeError):
            coordinateur.decider('signal')

    def test_commande_entree(self):
        self.assertEqual(CommandeEntree('k', 'EURUSD', 'VENTE', Decimal('0.01'), 1.2, 1.1).sens, 'VENTE')
        for sens, sl, tp in (('ACHAT', 1.2, 1.1), ('VENTE', 1.1, 1.2), ('ACHAT', float('nan'), 1.2)):
            with self.subTest(sens=sens, sl=sl), self.assertRaises(ValueError):
                CommandeEntree('k', 'EURUSD', sens, Decimal('0.01'), sl, tp)
        with self.assertRaises(ValueError):
            CommandeEntree('k', 'EURUSD', 'ACHAT', Decimal('0'), 1.0, 1.2)
        with self.assertRaises(ValueError):
            CommandeEntree('k', 'EURUSD', 'HAUT', Decimal('0.01'), 1.0, 1.2)


class TestMoteurMinimal(unittest.TestCase):
    def test_un_enregistrement_par_bougie_close(self):
        suite = ticks(DUREE // 3)
        moteur = moteur_sur(fabriquer_strategie(CONFIGURATION), CONFIGURATION, suite)
        enregistrements = [e.vers_dict() for t in suite for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual([e['numero'] for e in enregistrements], [1, 2, 3])
        premier = enregistrements[0]
        self.assertEqual((premier['type'], premier['mode'], premier['bras'], premier['deploiement'], premier['motif'],
                          premier['signal'], premier['strategie'], premier['instant_utc_ms']),
                         (TypeEnregistrement.CLOTURE, 'REJEU', 'REFERENCE', 'squelette', 'NO_SETUP', None, IDENTIFIANT,
                          DUREE))
        self.assertEqual(premier['bougie']['fin_utc_ms'], DUREE)
        self.assertEqual(dict(premier['empreinte_regles'])['technique'], CONFIGURATION.technique.empreinte_canonique)

    def test_la_duree_vient_de_la_configuration(self):
        technique = analyser_export_technique(octets_technique_modifies(
            lambda r: r['common'].__setitem__('timeframe_seconds', 300)))
        autre = ConfigurationFigee(technique, analyser_export_ia(octets_exports()[1]))
        suite = ticks(DUREE // 3)
        moteur = moteur_sur(fabriquer_strategie(autre), autre, suite)
        enregistrements = [e.vers_dict() for t in suite for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual(len(enregistrements), 9)
        self.assertEqual({e['bougie']['duree_ms'] for e in enregistrements}, {300_000})

    def test_signal_injecte_refuse_sans_commande(self):
        suite = ticks(DUREE // 3)
        moteur = moteur_sur(StrategieQuiSignale(), CONFIGURATION, suite)
        sorties = [moteur.traiter_tick(t) for t in suite]
        enregistrements = [e.vers_dict() for s in sorties for e in s.enregistrements]
        types = [e['type'] for e in enregistrements]
        self.assertEqual(types, [TypeEnregistrement.CLOTURE, TypeEnregistrement.INTENTION] * 3)
        intentions = [e for e in enregistrements if e['type'] is TypeEnregistrement.INTENTION]
        self.assertTrue(all(e['motif'] == 'ENVIRONMENT_NOT_READY' and e['detail'] == 'SEGMENT_MINIMAL_S4'
                            and e['issue']['nature'] == 'REFUSEE' for e in intentions))
        self.assertEqual([e['numero'] for e in enregistrements], list(range(1, 7)))
        self.assertEqual([c for s in sorties for c in s.commandes], [])

    def test_symboles_independants(self):
        flux = [Tick('EURUSD', 'EURUSD', 0, 0, 1, 1.1, 1.2), Tick('GBPUSD', 'GBPUSD', 1, 1, 2, 1.3, 1.4),
                Tick('EURUSD', 'EURUSD', DUREE, DUREE, 3, 1.1, 1.2), Tick('GBPUSD', 'GBPUSD', DUREE + 1, DUREE + 1, 4, 1.3, 1.4)]
        moteur = moteur_sur(fabriquer_strategie(CONFIGURATION), CONFIGURATION, flux)
        symboles = [e.vers_dict()['symbole'] for t in flux for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual(symboles, ['EURUSD', 'GBPUSD'])


if __name__ == '__main__':
    unittest.main()
