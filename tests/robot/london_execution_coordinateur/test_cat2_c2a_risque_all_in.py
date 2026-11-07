"""Catégorie 2, couche 2a (risque_all_in) : contrat et bornes des sources C04–C09."""
from decimal import Decimal as D
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.london import parametres,bougies_range,bougie
from robot.outils.execution_partagee import profil
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.london.c2_moteur import MoteurLondon
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import SignalTechnique
from xpbots.execution.c0d_prix import construire_niveaux
from xpbots.execution.c2a_risque import calculer_risque

class TestJonctionRisque(unittest.TestCase):
    def test_vraie_cassure_vrais_niveaux_port_externe(self):
        p=parametres();m=MoteurLondon(p,'EURUSD',D('.0625'))
        for b in bougies_range(p): m.sur_bougie(b)
        m.sur_bougie(bougie(p=p,unite=UniteTemps.H1,heure='06:00:00'))
        s=m.sur_bougie(bougie(p=p));self.assertIsInstance(s,SignalTechnique)
        q=Cotation('EURUSD',D(str(s.cloture_prix)),D(str(s.cloture_prix)),s.cloture_ms,s.cloture_ms)
        pr=profil(tick_size=D('.0625'));n=construire_niveaux(s,q,pr,p.commun)
        r=calculer_risque(s,n,D('.1'),pr,p.commun,CalculSynthetique(profil_=pr))
        self.assertEqual(r.total,(n.distance+r.glissement+r.glissement)*pr.taille_contrat*D('.1'))
