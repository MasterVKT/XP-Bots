"""Contrat propre du moteur ; composants internes réels."""
from dataclasses import replace
import unittest
from robot.outils.orchestration import C,T,composer_bras,ticks_courts
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.orchestration.c0_contrats import ErreurOrchestration,EntreeMoteur,EntreeJournalisee,ReceptionExterne
from xpbots.orchestration.c2_moteur import MoteurDecision


def composer():
    b,p,h,c=composer_bras()
    return MoteurDecision(C,(b,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario),b,p,h,c


class TestMoteurDecision(unittest.TestCase):
    def test_repetition_derniere_entree_sans_effet(self):
        m,b,p,_,_=composer();e=EntreeMoteur(T,1)
        s=m.traiter(e);etat=m.etat
        self.assertFalse(s.ignoree);self.assertTrue(m.traiter(e).ignoree)
        self.assertEqual(m.etat,etat);self.assertEqual(len(m.entrees),1)
        self.assertEqual(m.traiter(e).sorties,())

    def test_recriture_recul_sequence_et_bras_etranger(self):
        m,*_=composer();m.traiter(EntreeMoteur(T,1))
        for e in (EntreeMoteur(T+1,1),EntreeMoteur(T-1,2),EntreeMoteur(T,3)):
            with self.subTest(e=e),self.assertRaises(ErreurOrchestration):m.traiter(e)
        self.assertEqual(len(m.entrees),1)

    def test_reception_sans_controle_est_refusee_avant_mutation(self):
        m,*_=composer()
        with self.assertRaises(ErreurOrchestration):m.traiter(EntreeMoteur(T,1,receptions=(ReceptionExterne('SNAPSHOT',None),)))
        self.assertEqual(m.entrees,());self.assertIsNotNone(m.etat)

    def test_aucune_permission_neutre_implicite(self):
        _,b,_,h,c=composer()
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b,),h,c)

    def test_composition_mode_ab_incomplete(self):
        from xpbots.orchestration.c1_bras import construire_bras
        _,b,p,h,c=composer();d=replace(b.deploiement,mode=C.ia.parametres['default_evaluation_mode'])
        b2=construire_bras(C,d,'REFERENCE',p.profils,p,b.fondamental,T,observation=p.observation(),base_utc=p.base_utc())
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b2,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario)

    def test_branches_et_symboles_non_concordants(self):
        _,b,_,h,c=composer()
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b,b),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario)
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b,),{},c,scenario_fondamental=ControleTechniqueNeutre.scenario)

    def test_entree_calculee_et_rejeu_exact_sans_backend(self):
        m,*_=composer();s=m.traiter(EntreeMoteur(T,1));j=m.entrees[-1]
        r,b,p,_,_=composer()
        def interdit(*a,**kw):raise AssertionError('backend consulté')
        for nom in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):setattr(p,nom,interdit)
        self.assertTrue(j.calculs[0][1]);self.assertEqual(r.rejouer(j),s)
        self.assertTrue(r.rejouer(j).ignoree)
        self.assertEqual(r.entrees,m.entrees)

    def test_calcul_manquant_invalide_et_ne_peut_etre_exporte(self):
        m,*_=composer();m.traiter(EntreeMoteur(T,1));j=m.entrees[-1]
        r,*_=composer()
        with self.assertRaises(ErreurOrchestration):r.rejouer(EntreeJournalisee(j.entree,(('REFERENCE',()),)))
        with self.assertRaises(ErreurOrchestration):_ = r.etat
        with self.assertRaises(ErreurOrchestration):r.traiter_evenement(T+1)

    def test_minuterie_ne_fabrique_pas_de_cotation_ni_bougie(self):
        m,*_=composer();s=m.traiter_evenement(T)
        self.assertFalse(any(e.type.value=='CLOTURE' for e in s.enregistrements))
        self.assertEqual(m.entrees[-1].entree.ticks,())

    def test_reprise_flux_et_journal_et_corruption_refusee(self):
        from xpbots.orchestration.c1_bras import construire_bras
        m,b,p,h,c=composer();tick=ticks_courts()[0];p.sur_tick(tick);m.traiter_ticks((tick,));e=m.etat
        b2=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,T,
            observation=p.observation(),base_utc=p.base_utc(),etat=e.bras[0])
        r=MoteurDecision(C,(b2,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario,etat=e)
        self.assertEqual(r.entrees,m.entrees);self.assertEqual(r.etat.flux,e.flux)
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b2,),h,c,
            scenario_fondamental=ControleTechniqueNeutre.scenario,etat=replace(e,entrees=()))

    def test_source_differente_refusee(self):
        _,b,_,h,c=composer()
        with self.assertRaises(ErreurOrchestration):MoteurDecision(C,(b,),h,c,source_ia=object(),scenario_fondamental=ControleTechniqueNeutre.scenario)

    def test_c11_10_methodes_et_symboles_arbitres_ensemble(self):
        from robot.outils.pilote_orchestration import duo,piloter
        from robot.squelette.test_fondamental import SignalUnique
        from xpbots.orchestration.c0_contrats import FabriqueStrategie
        from xpbots.execution.c4_cycle import NatureReponse
        methodes=C.technique.commun.simultaneous_strategy_priority
        fabriques=[]
        for identifiant in reversed(methodes):
            def creer(c,tailles,identifiant=identifiant):
                s=SignalUnique();s.identifiant=identifiant;return s
            fabriques.append(FabriqueStrategie(identifiant,creer))
        ticks=ticks_courts(tuple(reversed(C.technique.commun.universe_priority[:2])))
        m,p,_,_,_=duo(ticks,fabriques=fabriques);sorties,reponses=piloter(ticks,m,p)
        for nom in p:
            fills=[r for r in reponses[nom] if r.nature is NatureReponse.REMPLISSAGE]
            self.assertEqual({(r.cle.strategie,r.cle.symbole) for r in fills},{(methodes[0],s) for s in C.technique.commun.universe_priority[:2]})
            entrees=[c for s in sorties for n,v in s.sorties if n==nom for c in v.commandes if c.nature.value=='ENTREE']
            self.assertEqual([(c.cle.strategie,c.cle.symbole) for c in entrees],[(methodes[0],s) for s in C.technique.commun.universe_priority[:2]])
            lignes=[e.vers_dict() for s in sorties for n,v in s.sorties if n==nom for e in v.enregistrements]
            refus=[x for x in lignes if x.get('strategie')==methodes[1] and x.get('motif')=='SYMBOL_BUSY']
            self.assertEqual({x['symbole'] for x in refus},set(C.technique.commun.universe_priority[:2]))
