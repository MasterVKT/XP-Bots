"""Catégorie 1, couche 2a (risque_all_in) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D,getcontext
import unittest
from robot.outils.execution_partagee import *
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import RefusExecution
from xpbots.execution.c0d_prix import construire_niveaux,recalculer_objectif
from xpbots.execution.c2a_risque import *
from xpbots.noyau.c1c_domaine import Sens,Motif

def exemple(sens=Sens.ACHAT):
    s=signal(sens,cloture_prix=1.1005,stop_technique=1.09985 if sens is Sens.ACHAT else 1.10115)
    q=cotation(bid=D('1.1005'),ask=D('1.1006'))
    return s,construire_niveaux(s,q,profil(),commun())

class TestRisque(unittest.TestCase):
    def test_L01_exact_spread_une_fois_deux_sens(self):
        for sens in Sens:
            s,n=exemple(sens);p=profil();c=CalculSynthetique(profil_=p)
            for volume,want in ((D(1),D('.80')),(D('.1'),D('.08'))):
                r=calculer_risque(s,n,volume,p,commun(),c)
                self.assertEqual((r.total,r.glissement),(want,D('.000025')))
                self.assertEqual(r.total,(n.distance+r.glissement+r.glissement)*p.taille_contrat*volume)
    def test_frais_minimaux_non_lineaires(self):
        s,n=exemple();p=profil(commission_par_lot_par_cote=D('.1'),commission_minimum_par_ordre=D('.03'),commission_nulle_confirmee=False)
        c=CalculSynthetique(profil_=p,autres_frais=D('.01'))
        a=calculer_risque(s,n,D('.1'),p,commun(),c);b=calculer_risque(s,n,D('.2'),p,commun(),c)
        self.assertEqual((a.frais,b.frais),(D('.07'),D('.07')))
        self.assertNotEqual(a.total*2,b.total)
    def test_apres_fill_sortie_seule_et_couts_entree_conserves(self):
        s,n=exemple();p=profil();c=CalculSynthetique(profil_=p)
        n=recalculer_objectif(n,n.entree+D('.0001'))
        r=calculer_risque(s,n,D('.1'),p,commun(),c,apres_remplissage=True,frais_entree_reels=D('.02'))
        self.assertEqual(r.entree_pessimiste,n.entree)
        self.assertEqual(r.sortie_pessimiste,n.stop-r.glissement)
        self.assertEqual(r.total,(n.distance+r.glissement)*p.taille_contrat*D('.1')+D('.02'))
        self.assertEqual(r.frais,D('.02'))
        self.assertEqual(calculer_risque(s,n,D('.1'),p,commun(),c,apres_remplissage=True).detail,'frais_entree_reels')
    def test_tick_minimal_et_parametre_glissement_charge(self):
        s,n=exemple();p=profil();c=CalculSynthetique(profil_=p)
        r=calculer_risque(s,n,D('.1'),p,replace(commun(),slippage_budget_atr_per_leg=0),c)
        self.assertEqual(r.glissement,p.tick_size)
        r=calculer_risque(s,n,D('.1'),p,replace(commun(),slippage_budget_atr_per_leg=.2),c)
        self.assertEqual(r.glissement,D('.00010'))
    def test_panne_ou_frais_inconnus_refuses(self):
        s,n=exemple();p=profil()
        class P(CalculSynthetique):
            def frais_aller_retour(self,*args): return None
        self.assertEqual(calculer_risque(s,n,D('.1'),p,commun(),P()).detail,'frais_aller_retour')
        class P(CalculSynthetique):
            def profit(self,*args): raise RuntimeError('panne synthétique')
        self.assertEqual(calculer_risque(s,n,D('.1'),p,commun(),P()).detail,'profit')
    def test_profil_non_pret_et_volume_hors_grille(self):
        s,n=exemple();p=profil();c=CalculSynthetique()
        for q in (replace(p,commission_nulle_confirmee=False),replace(p,tick_size=D('NaN')),replace(p,volume_min=D('.15'))):
            self.assertIsInstance(calculer_risque(s,n,D('.2'),q,commun(),c),RefusExecution)
        for v in (D('.01'),D('.15'),D(2),1):
            with self.subTest(v=v),self.assertRaises(ValueError): calculer_risque(s,n,v,p,commun(),c)
    def test_profit_positif_plancher_zero_et_contexte_global(self):
        class P(CalculSynthetique):
            def profit(self,*args): return D(1)
        s,n=exemple();before=getcontext().copy();r=calculer_risque(s,n,D('.1'),profil(),commun(),P())
        self.assertEqual(r.total,D(0));self.assertEqual(getcontext().prec,before.prec)
