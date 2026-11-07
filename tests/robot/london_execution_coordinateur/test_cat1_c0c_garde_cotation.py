"""Catégorie 1, couche 0c (garde_cotation) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.configuration import configuration_figee
from xpbots.execution.c0c_cotation import *
from xpbots.noyau.c1a_marche import Cotation
from xpbots.noyau.c1c_domaine import SignalTechnique,Sens,Motif

class TestCotation(unittest.TestCase):
    def setUp(self):
        self.p=configuration_figee().technique.commun
        self.s=SignalTechnique('LONDON_V3','EURUSD',10000,Sens.ACHAT,1.1,.001,1.099,2)
        self.q=Cotation('EURUSD',D('1.1'),D('1.10015'),10000,10000)
    def v(self,q=None,now=10000,**kw): return evaluer_cotation(self.s,self.q if q is None else q,now,self.p,**kw)
    def test_spread_plafond_et_zero_admis(self):
        self.assertIs(self.v().etat,EtatCotation.ADMISSIBLE)
        self.assertIs(self.v(replace(self.q,ask=self.q.bid)).etat,EtatCotation.ADMISSIBLE)
        self.assertIs(self.v(replace(self.q,ask=self.q.ask+D('.00001'))).motif,Motif.SPREAD_CAP)
    def test_ecart_entree_borne_incluse(self):
        gap=D(str(self.p.max_entry_bid_gap_atr))*D(str(self.s.atr_reference))
        q=replace(self.q,bid=D('1.1')+gap,ask=D('1.1')+gap)
        self.assertIs(self.v(q).etat,EtatCotation.ADMISSIBLE)
        self.assertIs(self.v(replace(q,bid=q.bid+D('.00001'),ask=q.ask+D('.00001'))).motif,Motif.ENTRY_GAP)
    def test_deux_ages_exactement_admis_puis_exclus(self):
        self.assertIs(self.v(now=12000).etat,EtatCotation.ADMISSIBLE)
        for q in (self.q,replace(self.q,instant_fournisseur_ms=12001),replace(self.q,instant_reception_ms=12001)):
            self.assertEqual(self.v(q,12001).derniere_cause,'COTATION_INVALIDE')
        for champ in ('instant_fournisseur_ms','instant_reception_ms'):
            self.assertEqual(self.v(replace(self.q,**{champ:9999})).derniere_cause,'COTATION_INVALIDE')
            self.assertEqual(self.v(replace(self.q,**{champ:10001})).derniere_cause,'COTATION_INVALIDE')
    def test_ttl_exact_et_cause_conservee(self):
        q=replace(self.q,instant_fournisseur_ms=14999,instant_reception_ms=14999)
        self.assertIs(self.v(q,14999).etat,EtatCotation.ADMISSIBLE)
        v=self.v(q,15000,derniere_cause='SPREAD_CAP')
        self.assertEqual((v.etat,v.motif,v.detail),(EtatCotation.EXPIREE,Motif.SIGNAL_EXPIRED,'SPREAD_CAP'))
        self.assertEqual(evaluer_cotation(self.s,None,15000,self.p).detail,'AUCUNE_COTATION')
    def test_invalides_absence_croisement_autre_symbole(self):
        self.assertEqual(evaluer_cotation(self.s,None,10000,self.p).derniere_cause,'AUCUNE_COTATION')
        for q in (replace(self.q,ask=D('1.0999')),replace(self.q,symbole='GBPUSD'),'invalide'):
            self.assertEqual(self.v(q).derniere_cause,'COTATION_INVALIDE')
        with self.assertRaises(ValueError): self.v(now=True)
    def test_parametres_modifies_effectifs(self):
        p=replace(self.p,max_spread_price={'EURUSD':.0002,'GBPUSD':.0002,'XAUUSD':.5},entry_signal_ttl_seconds=6)
        q=replace(self.q,ask=D('1.1002'),instant_fournisseur_ms=15000,instant_reception_ms=15000)
        self.assertIs(evaluer_cotation(self.s,q,15000,p).etat,EtatCotation.ADMISSIBLE)
