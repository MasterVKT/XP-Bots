"""Segments S3 et S4 : stratégie minimale, coordinateur minimal et enchaînement du moteur minimal."""
from decimal import Decimal
import unittest

from robot.outils.chemins import CONFIGURATION_TECHNIQUE
from robot.outils.specification import motifs_admis, octets_configuration_modifiee
from xpbots.execution.squelette import CommandeEntree, CoordinateurMinimal
from xpbots.london.squelette import StrategieMinimale, fabriquer_strategie
from xpbots.noyau.squelette import Bougie, ResultatTechnique, Tick, lire_configuration_squelette
from xpbots.orchestration.squelette import fabriquer_moteur_minimal

CONFIGURATION = lire_configuration_squelette(CONFIGURATION_TECHNIQUE.read_bytes())


class StrategieQuiSignale:
    """Doublure de test du contrat structurel de stratégie : rend un signal d'achat à chaque clôture."""

    identifiant = 'TEST'

    def sur_cloture(self, bougie):
        return ResultatTechnique('TEST', bougie.symbole, bougie.fin_ms, 'ACHAT', None, None)


class TestStrategieEtCoordinateur(unittest.TestCase):
    def test_strategie_minimale(self):
        strategie = fabriquer_strategie(CONFIGURATION)
        self.assertEqual(strategie.identifiant, CONFIGURATION.identifiant_strategie)
        resultat = strategie.sur_cloture(Bougie('EURUSD', 0, 900, 1.0, 1.0, 1.0, 1.0, 1))
        self.assertEqual((resultat.sens, resultat.motif, resultat.detail, resultat.cloture_ms),
                         (None, 'NO_SETUP', 'SEGMENT_MINIMAL_S3', 900))
        self.assertIn(resultat.motif, motifs_admis())
        with self.assertRaises(ValueError):
            StrategieMinimale('')

    def test_coordinateur_refuse_tout_signal(self):
        coordinateur = CoordinateurMinimal()
        sans_signal = ResultatTechnique('LONDON_V3', 'EURUSD', 900, None, 'NO_SETUP', 'X')
        self.assertEqual(coordinateur.decider(sans_signal).motif, 'NO_SETUP')
        for sens in ('ACHAT', 'VENTE'):
            decision = coordinateur.decider(ResultatTechnique('LONDON_V3', 'EURUSD', 900, sens, None, None))
            self.assertEqual((decision.motif, decision.detail, decision.commandes),
                             ('ENVIRONMENT_NOT_READY', 'SEGMENT_MINIMAL_S4', ()))
            self.assertIn(decision.motif, motifs_admis())

    def test_contrats_des_types(self):
        for arguments in (('X', 'EURUSD', 0, 'HAUT', None, None), ('X', 'EURUSD', 0, None, None, None),
                          ('X', 'EURUSD', 0, 'ACHAT', 'NO_SETUP', None)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                ResultatTechnique(*arguments)
        for sens, sl, tp in (('ACHAT', 1.2, 1.1), ('VENTE', 1.1, 1.2), ('ACHAT', float('nan'), 1.2)):
            with self.subTest(sens=sens, sl=sl), self.assertRaises(ValueError):
                CommandeEntree('k', 'EURUSD', sens, Decimal('0.01'), sl, tp)
        with self.assertRaises(ValueError):
            CommandeEntree('k', 'EURUSD', 'ACHAT', Decimal('0'), 1.0, 1.2)


class TestMoteurMinimal(unittest.TestCase):
    def ticks(self, duree):
        return [Tick('EURUSD', 'EURUSD', i * duree // 3, i, 1.0 + i / 1024, 1.0 + i / 1024 + 0.0001)
                for i in range(10)]

    def test_un_enregistrement_par_bougie_close(self):
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(CONFIGURATION), CONFIGURATION, 'REJEU')
        enregistrements = [e for t in self.ticks(CONFIGURATION.duree_bougie_ms)
                           for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual([e['numero'] for e in enregistrements], [1, 2, 3])
        premier = enregistrements[0]
        self.assertEqual((premier['type'], premier['mode'], premier['motif'], premier['signal'],
                          premier['strategie'], premier['instant_utc_ms']),
                         ('CLOTURE', 'REJEU', 'NO_SETUP', None, CONFIGURATION.identifiant_strategie,
                          CONFIGURATION.duree_bougie_ms))
        self.assertEqual(premier['bougie']['fin_utc_ms'], CONFIGURATION.duree_bougie_ms)

    def test_la_duree_vient_de_la_configuration(self):
        autre = lire_configuration_squelette(octets_configuration_modifiee(timeframe_seconds=300))
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(autre), autre, 'REJEU')
        enregistrements = [e for t in self.ticks(CONFIGURATION.duree_bougie_ms)
                           for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual(len(enregistrements), 9)
        self.assertEqual({e['bougie']['fin_utc_ms'] - e['bougie']['debut_utc_ms'] for e in enregistrements},
                         {300_000})

    def test_signal_injecte_refuse_sans_commande(self):
        moteur = fabriquer_moteur_minimal(StrategieQuiSignale(), CONFIGURATION, 'REJEU')
        sorties = [moteur.traiter_tick(t) for t in self.ticks(CONFIGURATION.duree_bougie_ms)]
        enregistrements = [e for s in sorties for e in s.enregistrements]
        self.assertTrue(enregistrements)
        self.assertTrue(all(e['signal'] == 'ACHAT' and e['motif'] == 'ENVIRONMENT_NOT_READY'
                            for e in enregistrements))
        self.assertEqual([c for s in sorties for c in s.commandes], [])

    def test_symboles_independants(self):
        moteur = fabriquer_moteur_minimal(fabriquer_strategie(CONFIGURATION), CONFIGURATION, 'REJEU')
        duree = CONFIGURATION.duree_bougie_ms
        flux = [Tick('EURUSD', 'EURUSD', 0, 1, 1.1, 1.2), Tick('GBPUSD', 'GBPUSD', 1, 2, 1.3, 1.4),
                Tick('EURUSD', 'EURUSD', duree, 3, 1.1, 1.2), Tick('GBPUSD', 'GBPUSD', duree + 1, 4, 1.3, 1.4)]
        symboles = [e['symbole'] for t in flux for e in moteur.traiter_tick(t).enregistrements]
        self.assertEqual(symboles, ['EURUSD', 'GBPUSD'])


if __name__ == '__main__':
    unittest.main()
