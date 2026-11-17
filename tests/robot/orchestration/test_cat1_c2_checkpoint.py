"""Catégorie 1, couche 2 : checkpoint lié au journal du moteur réel."""
from dataclasses import replace
import unittest
from robot.outils.orchestration import C,T,composer_bras,ticks_courts
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.orchestration.c0_contrats import ErreurOrchestration,EntreeJournalisee
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision


def composer():
    b,p,h,c=composer_bras()
    m=MoteurDecision(C,(b,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario)
    return m,b,p,h,c


def reprendre(b,p,h,c,photographie,**options):
    b2=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,T,
        observation=p.observation(),base_utc=p.base_utc(),etat=photographie.bras[0])
    return MoteurDecision(C,(b2,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario,**options)


class TestCheckpoint(unittest.TestCase):
    def test_checkpoint_vide_sans_copie_du_journal(self):
        m,*_=composer();p=m.exporter_checkpoint()
        self.assertEqual(p.numero_entrees,0);self.assertFalse(hasattr(p,'entrees'));p.verifier()
        self.assertEqual(p.flux,m.etat.flux);self.assertEqual(p.bras,m.etat.bras)

    def test_reprise_equivalente_et_repetition_sans_effet(self):
        m,b,p,h,c=composer();tick=ticks_courts()[0];p.sur_tick(tick);m.traiter_ticks((tick,))
        etat=m.etat;cp=m.exporter_checkpoint();journal=m.entrees
        ancien=reprendre(b,p,h,c,etat,etat=etat)
        nouveau=reprendre(b,p,h,c,etat,checkpoint=cp,entrees=journal)
        self.assertEqual(nouveau.etat,ancien.etat)
        self.assertTrue(m.rejouer(journal[-1]).ignoree);self.assertEqual(m.exporter_checkpoint(),cp)

    def test_entrees_depuis_et_bornes(self):
        m,*_=composer();m.traiter_evenement(T);m.traiter_evenement(T)
        self.assertEqual(m.entrees_depuis(0),m.entrees)
        self.assertEqual(m.entrees_depuis(1),m.entrees[1:]);self.assertEqual(m.entrees_depuis(2),())
        for v in (-1,3,True,1.0,None):
            with self.subTest(v=v),self.assertRaises(ErreurOrchestration):m.entrees_depuis(v)

    def test_checkpoint_et_journal_corrompus_refuses(self):
        m,b,p,h,c=composer();m.traiter_evenement(T);m.traiter_evenement(T)
        etat=m.etat;cp=m.exporter_checkpoint();journal=m.entrees
        altere=replace(journal[0],entree=replace(journal[0].entree,instant_ms=T-1))
        for js in (journal[:-1],tuple(reversed(journal)),(altere,journal[1])):
            with self.subTest(js=js),self.assertRaises(ErreurOrchestration):reprendre(b,p,h,c,etat,checkpoint=cp,entrees=js)
        for faux in (replace(cp,numero_entrees=True),replace(cp,empreinte='0'*64),replace(cp,empreinte_journal='0'*64)):
            with self.subTest(faux=faux),self.assertRaises(ErreurOrchestration):reprendre(b,p,h,c,etat,checkpoint=faux,entrees=journal)
        with self.assertRaises(ErreurOrchestration):reprendre(b,p,h,c,etat,etat=etat,checkpoint=cp,entrees=journal)
        with self.assertRaises(ErreurOrchestration):reprendre(b,p,h,c,etat,entrees=journal)

    def test_export_refuse_si_le_moteur_est_invalide(self):
        m,*_=composer();m.traiter_evenement(T);j=m.entrees[-1];r,*_=composer()
        with self.assertRaises(ErreurOrchestration):r.rejouer(EntreeJournalisee(j.entree,(('REFERENCE',()),)))
        with self.assertRaises(ErreurOrchestration):r.exporter_checkpoint()
