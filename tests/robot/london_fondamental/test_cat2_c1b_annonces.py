"""Catégorie 2, couche 1b : vraies valeurs, configuration et versions de frontière."""
import unittest
from robot.outils.configuration import octets_technique_modifies
from robot.outils.fondamental import T, commun, octets, calendrier, evenement, table_importance, ConversionServeurScenario
from xpbots.noyau.c0c_configuration import analyser_export_technique
from xpbots.fondamental.c0_types import Annonce, VersionCalendrier
from xpbots.fondamental.c1b_annonces import GardeAnnonces


class TestJonctionAnnonces(unittest.TestCase):
    def test_export_mql5_exact_converti_en_valeurs_reelles(self):
        g=GardeAnnonces(commun(),ConversionServeurScenario())
        r=g.recevoir(octets(calendrier(evenements=[evenement(nom='Décision synthétique éà')])) ,T,table_importance())
        self.assertIsInstance(r.version,VersionCalendrier)
        self.assertIsInstance(r.version.annonces[0],Annonce)
        self.assertEqual(r.version.annonces[0].nom,'Décision synthétique éà')
        self.assertEqual(r.version.table,table_importance())

    def test_parametres_charges_regissent_la_fenetre(self):
        def changer(p):p['common']['news_before_seconds']=300
        c=analyser_export_technique(octets_technique_modifies(changer)).commun
        g=GardeAnnonces(c,ConversionServeurScenario())
        g.recevoir(octets(calendrier(evenements=[evenement(T+600000)])),T,table_importance())
        self.assertTrue(g.evaluer('EURUSD',T+299999).admise)
        self.assertTrue(g.evaluer('EURUSD',T+300000).cloture_obligatoire)

    def test_prefixe_et_reprise_restent_causes_apres_revision_future(self):
        g=GardeAnnonces(commun(),ConversionServeurScenario())
        g.recevoir(octets(calendrier(evenements=[evenement()])),T,table_importance())
        instants=(T,T+900000,T+1800000)
        attendus=tuple(g.evaluer('EURUSD',t) for t in instants)
        g.recevoir(octets(calendrier(2,T+3600000,[evenement(T+7200000,revision=2)])),T+3600000,table_importance())
        r=GardeAnnonces(commun(),ConversionServeurScenario(),g.etat)
        self.assertEqual(tuple(r.evaluer('EURUSD',t) for t in instants),attendus)
