"""Jonction réelle du moteur, des deux bras London et du journal de calcul."""
from dataclasses import replace
from datetime import date
import unittest
from robot.outils.orchestration import C
from robot.outils.couture_execution import journee_executable
from robot.outils.fabrique_ticks import lignes_csv
from robot.outils.pilote_orchestration import duo,piloter
from xpbots.rejeu.squelette import analyser_lignes_ticks
from xpbots.execution.c4_cycle import NatureReponse


class TestJonctionMoteur(unittest.TestCase):
    def test_journee_london_ab_rejeu_exact_backend_interdit(self):
        _,fab=journee_executable(date(2026,7,15),C.technique)
        ticks=list(analyser_lignes_ticks(lignes_csv(fab)))
        m,ports,ia,_,_=duo(ticks);sorties,reponses=piloter(ticks,m,ports)
        for nom in ports:
            self.assertEqual(sum(r.nature is NatureReponse.REMPLISSAGE for r in reponses[nom]),1)
            self.assertEqual(sum(r.nature is NatureReponse.CLOTURE for r in reponses[nom]),1)
            self.assertFalse(ports[nom].positions_ouvertes)
        self.assertIsNot(m.bras['IA'].coordinateur,m.bras['REFERENCE'].coordinateur)
        self.assertTrue(all(e.enveloppe.bras==n for s in sorties for n,v in s.sorties for e in v.enregistrements))
        r,p2,_,_,_=duo(ticks)
        def interdit(*a,**kw):raise AssertionError('backend consulté au rejeu')
        for p in p2.values():
            for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):setattr(p,n,interdit)
        archive=m.entrees
        self.assertEqual(len(sorties),len(archive))
        for j,s in zip(archive,sorties):self.assertEqual(r.rejouer(j),s)
        self.assertEqual(r.entrees,archive)
        self.assertEqual(r.etat.flux,m.etat.flux)

    def test_bougies_communes_h1_avant_m15_et_strategies_distinctes(self):
        from robot.outils.orchestration import ticks_courts
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);piloter(ticks,m,ports)
        a=m.bras['REFERENCE'].etat.historique;b=m.bras['IA'].etat.historique
        self.assertEqual(a,b)
        self.assertTrue(all(x.valeur is y.valeur for x,y in zip(a,b)))
        h=[x.valeur.unite.value for x in a if x.nature=='BOUGIE' and x.valeur.bougie.fin_ms==ticks[-1].instant_fournisseur_ms]
        self.assertEqual(h,['H1','M15'])
        self.assertIsNot(next(iter(m.bras['IA'].strategies.values())),next(iter(m.bras['REFERENCE'].strategies.values())))

    def test_veto_limite_au_bras_ia_sans_rattrapage(self):
        from robot.squelette.test_contexte_ia import paquet
        from robot.squelette.test_fondamental import SignalUnique,T,S,ticks_courts
        from xpbots.orchestration.c0_contrats import FabriqueStrategie
        ticks=ticks_courts();f=FabriqueStrategie(SignalUnique.identifiant,lambda c,t:SignalUnique())
        m,p,_,_,_=duo(ticks,fabriques=(f,),paquets_ia=(paquet(S,S+30000),))
        sorties,reponses=piloter(ticks,m,p)
        self.assertEqual(sum(r.nature is NatureReponse.REMPLISSAGE for r in reponses['REFERENCE']),1)
        self.assertEqual(reponses['IA'],[])
        self.assertTrue(p['REFERENCE'].positions_ouvertes);self.assertFalse(p['IA'].positions_ouvertes)
        self.assertNotEqual(p['REFERENCE'].etat_compte().fonds_propres,p['IA'].etat_compte().fonds_propres)
        self.assertTrue(any(e.vers_dict().get('motif')=='AI_CONTEXT_VETO' for s in sorties for n,v in s.sorties if n=='IA' for e in v.enregistrements))
        ref=m.bras['REFERENCE'].etat.historique;ia=m.bras['IA'].etat.historique
        self.assertTrue(any(x.nature=='ISSUE' and x.valeur.nature.value=='REMPLIE' for x in ref))
        self.assertFalse(any(x.nature=='ISSUE' and x.valeur.nature.value=='REMPLIE' for x in ia))
