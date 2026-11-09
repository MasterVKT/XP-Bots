"""Catégorie 2 : bras sur London, flux, coordinateur, protections et compte réels."""
from datetime import date
import json
import unittest
from robot.outils.orchestration import C,composer_bras,executer_bras
from robot.outils.couture_execution import journee_executable
from robot.outils.fabrique_ticks import lignes_csv
from xpbots.rejeu.squelette import analyser_lignes_ticks
from xpbots.noyau.c2_journal import serialiser
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.orchestration.c1_bras import construire_bras


class TestJonctionBras(unittest.TestCase):
    def test_initialisation_rejouee_dans_le_vrai_coordinateur(self):
        b,p,_,_=composer_bras()
        appels=b.calculs.initialisation
        # Le C6 actuel ne consulte pas le port pendant sa construction ; ce zéro est conservé.
        self.assertEqual(appels,())
        class Interdit:
            profil_compte=p.profil_compte
            def __getattr__(self,n):raise AssertionError('backend consulté pendant le rejeu')
        r=construire_bras(C,b.deploiement,b.nom,p.profils,Interdit(),b.fondamental,p.instant_ms,
            observation=p.observation(),base_utc=p.base_utc(),appels_initialisation=appels)
        self.assertEqual(r.calculs.initialisation,appels)
        self.assertEqual(r.coordinateur.etat,b.coordinateur.etat)

    def test_london_reel_fill_et_cloture_propres_au_bras(self):
        _,fab=journee_executable(date(2026,7,15),C.technique)
        ticks=list(analyser_lignes_ticks(lignes_csv(fab)))
        b,p,h,per=composer_bras(ticks=ticks)
        lignes,signaux,reponses=executer_bras(b,p,ticks,h,per)
        self.assertEqual(len(signaux),1)
        self.assertEqual(sum(r.nature is NatureReponse.REMPLISSAGE for r in reponses),1)
        self.assertEqual(sum(r.nature is NatureReponse.CLOTURE for r in reponses),1)
        self.assertFalse(p.positions_ouvertes)
        intentions=[e.vers_dict() for e in lignes if e.type.value=='INTENTION']
        self.assertEqual([i['nature'] for e in intentions for i in e['issues_nouvelles']],['REMPLIE','CLOTUREE'])
        self.assertEqual(intentions[-1]['reservations']['reservations'],())
        self.assertTrue(any(t.nature=='ISSUE' for t in b.etat.historique))
        for e in lignes:self.assertEqual(json.loads(serialiser(e))['bras'],'REFERENCE')
        etat=b.etat
        r=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,p.instant_ms,
            observation=p.observation(),base_utc=p.base_utc(),etat=etat)
        self.assertEqual(r.etat.historique,etat.historique)
        self.assertEqual(r.etat.numero,etat.numero)

    def test_fabriques_ne_recoivent_qu_un_symbole_et_configuration_reelle(self):
        from robot.outils.orchestration import ticks_courts
        from xpbots.orchestration.c0_contrats import FabriqueStrategie
        from xpbots.london.c2_moteur import fabriquer_strategie
        appels=[]
        def fabriquer(c,tailles):
            appels.append((c,tuple(tailles)));return fabriquer_strategie(c,tailles)
        b,_,_,_=composer_bras(ticks=ticks_courts(('EURUSD','GBPUSD')),
            fabriques=[FabriqueStrategie(C.technique.london['strategy_id'],fabriquer)])
        self.assertEqual({s for _,table in appels for s in table},{'EURUSD','GBPUSD'})
        self.assertTrue(all(c is C and len(table)==1 for c,table in appels))
        self.assertEqual(len(b.strategies),2)
