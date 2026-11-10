"""S1/S5/S7 utilisent le code commun, les couts C10 et des rapports non qualifies."""
from datetime import date
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.couture_execution import journee_executable
from robot.outils.fabrique_ticks import ecrire_csv,lignes_csv
from robot.outils.chemins import RACINE_DEPOT
from robot.outils.rejeu import experience_courte
from robot.squelette.test_s7_point_entree import executer
from xpbots.app.rejeu_squelette import composer_rejeu_papier
from xpbots.rejeu.squelette import analyser_lignes_ticks,ContratPapier,rejouer,ErreurDonnees
from xpbots.rejeu.c1b_simulateur import SimulateurExecution


class TestCouturesRejeu(unittest.TestCase):
    def test_s1_manifeste_exact_et_refus_sans_prefixe_partiel(self):
        _,source,_,_,_=experience_courte()
        lignes=tuple(source.lire());ticks=tuple(analyser_lignes_ticks(lignes,source.manifeste))
        self.assertTrue(ticks)
        with self.assertRaises(ErreurDonnees):
            analyser_lignes_ticks(lignes[:-1]+(lignes[-1].replace('1.102','1.103'),),source.manifeste)
        with self.assertRaises(ErreurDonnees):analyser_lignes_ticks(lignes[:-1]+('invalide\n',))

    def test_s5_simulateur_unique_reference_et_stress_differents(self):
        c=configuration_figee();_,fab=journee_executable(date(2026,7,15),c.technique)
        ticks=tuple(analyser_lignes_ticks(lignes_csv(fab)));resultats={}
        for scenario in ('REFERENCE','STRESS'):
            m,e,s=composer_rejeu_papier(c,ticks,{'EURUSD':D('.00001')},
                {'EURUSD':ContratPapier(D(1000),D('.1'),D(1),D('.1'))},
                scenario='TECHNICAL_CONTROL_NEUTRAL',modele_couts=scenario)
            self.assertIsInstance(e,SimulateurExecution);self.assertEqual(e.scenario.nom,scenario)
            r=rejouer(ticks,m,e,s);self.assertEqual(r.nombre_ticks,len(ticks))
            self.assertTrue(e.trades);self.assertFalse(e.positions_ouvertes)
            resultats[scenario]=e.trades[0]
        self.assertGreater(resultats['STRESS'].prix_entree,resultats['REFERENCE'].prix_entree)
        # Les quatre ticks/M15 de cette fixture ne contiennent aucun prix entre 250 et 1000 ms.
        self.assertEqual(resultats['STRESS'].entree_ms,resultats['REFERENCE'].entree_ms)

    def test_s7_rapport_stress_ab_et_statut_fixture_explicites(self):
        c=configuration_figee();_,fab=journee_executable(date(2026,7,15),c.technique)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=ecrire_csv(p/'ticks.csv',fab)
            code,sortie,erreurs=executer(['--racine-depot',str(RACINE_DEPOT),'--ticks',str(f),
                '--sortie',str(p/'sortie'),'--tick-size','EURUSD=0.00001','--mode','PAPER_AB','--couts','STRESS'])
            self.assertEqual((code,erreurs),(0,''));r=json.loads(sortie)
            self.assertEqual(r['rapport']['statut'],'NON_VALIDE_FIXTURE')
            self.assertEqual(set(r['rapport']['bras']),{'REFERENCE','IA'})
            for b in r['rapport']['bras'].values():
                self.assertEqual(b['scenario_couts'],'STRESS');self.assertGreater(b['positions_closes'],0)
                self.assertIsNone(b['configurations_potentielles'])
            self.assertTrue((p/'sortie/decisions.jsonl').is_file())
