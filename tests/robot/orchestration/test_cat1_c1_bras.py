"""Catégorie 1 : composition, isolation, état pur et journal du bras."""
from dataclasses import replace,FrozenInstanceError
from decimal import Decimal as D
import unittest
from robot.outils.orchestration import C,T,composer_bras,ticks_courts,flux,executer_bras
from robot.outils.contexte_ia import parametres,octets,snapshot,evenement
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.contexte_ia.c0_types import PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.orchestration.c0_contrats import ErreurOrchestration,FabriqueStrategie
from xpbots.orchestration.c1_bras import construire_bras,EtatBras,PortCalculJournalise
from xpbots.execution.c1a_calcul import appeler_calcul
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1c_domaine import SignalTechnique,Issue,CleIntention
from xpbots.execution.c4_cycle import NatureReponse


class SignalPort:
    """Stratégie externe contractuelle pour tester la composition des ports, pas S02."""
    identifiant=C.technique.london['strategy_id']
    def sur_bougie(self,b):
        if b.unite.value!='M15':return None
        x=b.bougie
        return SignalTechnique(self.identifiant,x.symbole,x.fin_ms,'ACHAT',x.cloture,.001,x.cloture-.0008,2)
    def sur_issue(self,i):pass


class TestBras(unittest.TestCase):
    def test_fabriques_reelles_une_instance_par_symbole(self):
        b,_,_,_=composer_bras(ticks=ticks_courts(('EURUSD','GBPUSD')))
        self.assertEqual(len(b.strategies),2)
        self.assertEqual(len({id(v) for v in b.strategies.values()}),2)
        with self.assertRaises(TypeError):b.strategies['x']=None

    def test_fabrique_non_conforme_ou_objet_reutilise_refuse(self):
        ident=C.technique.london['strategy_id']
        for f in (FabriqueStrategie(ident,lambda *a:object()),FabriqueStrategie('INCONNU',fabriquer_strategie)):
            with self.assertRaises(ErreurOrchestration):composer_bras(fabriques=[f])
        partage=fabriquer_strategie(C,{'EURUSD':D('.00001'),'GBPUSD':D('.00001')})
        with self.assertRaises(ErreurOrchestration):composer_bras(ticks=ticks_courts(('EURUSD','GBPUSD')),
            fabriques=[FabriqueStrategie(ident,lambda *a:partage)])

    def test_comptes_et_cles_de_deploiement_distincts_en_ab(self):
        mode=C.ia.parametres['default_evaluation_mode']
        a,pa,_,_=composer_bras(mode=mode);b,pb,_,_=composer_bras('IA',mode=mode)
        self.assertIsNot(a.coordinateur,b.coordinateur);self.assertIsNot(pa,pb)
        self.assertNotEqual(a.identifiant,b.identifiant)
        self.assertTrue(a.identifiant.endswith(':REFERENCE'));self.assertTrue(b.identifiant.endswith(':IA'))
        self.assertEqual(pa.etat_compte().solde,pb.etat_compte().solde)
        self.assertEqual(pa.etat_compte().solde,D(str(C.technique.commun.initial_equity_usd)))

    def test_reference_ne_prend_pas_le_lecteur_fourni(self):
        lecteur=LecteurContexte(parametres(),PolitiqueVeto(True))
        lecteur.recevoir(octets(snapshot(genere=T,evenements=[evenement(debut=T,fin=T+3600000)])),T)
        f=FabriqueStrategie(SignalPort.identifiant,lambda *a:SignalPort())
        for nom,attendu in (('REFERENCE',1),('IA',0)):
            b,p,h,per=composer_bras(nom,lecteur=lecteur,fabriques=[f])
            _,_,reponses=executer_bras(b,p,ticks_courts(),h,per)
            self.assertEqual(sum(r.nature is NatureReponse.REMPLISSAGE for r in reponses),attendu)

    def test_politique_papier_interdite_en_execution_reelle(self):
        lecteur=LecteurContexte(parametres(),PolitiqueVeto(True,False,False))
        with self.assertRaises(ErreurOrchestration):composer_bras('IA',mode='DEMO',lecteur=lecteur)

    def test_historique_public_et_reprise(self):
        ticks=ticks_courts();b,p,h,per=composer_bras(ticks=ticks)
        executer_bras(b,p,ticks,h,per);e=b.etat
        self.assertTrue(e.historique)
        r=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,p.instant_ms,
            observation=p.observation(),base_utc=p.base_utc(),etat=e)
        self.assertEqual(r.etat.historique,e.historique);self.assertEqual(r.etat.numero,e.numero)
        with self.assertRaises(FrozenInstanceError):e.numero=0

    def test_reprise_refuse_historique_perdu_et_signature_alteree(self):
        ticks=ticks_courts();b,p,h,per=composer_bras(ticks=ticks);executer_bras(b,p,ticks,h,per);e=b.etat
        for faux in (replace(e,historique=()),replace(e,signature=()),replace(e,numero=e.numero+1)):
            with self.assertRaises(ErreurOrchestration):construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,
                p.instant_ms,observation=p.observation(),base_utc=p.base_utc(),etat=faux)

    def test_etat_mal_type_refuse(self):
        b,p,_,_=composer_bras()
        with self.assertRaises(ErreurOrchestration):construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,T,etat={})
        with self.assertRaises(ErreurOrchestration):EtatBras('autre',(),b.coordinateur.etat)

    def test_journal_numerote_et_sans_doublon_d_intention(self):
        b,p,_,_=composer_bras();lot=b.coordinateur.traiter(T,base_utc=p.base_utc())
        s=b.consommer(lot,T);s2=b.consommer(lot,T)
        self.assertFalse(s2.commandes)
        self.assertFalse(any(e.type.value=='INTENTION' for e in s2.enregistrements))
        al=b.alerte('CONTROLE_TEST',T);self.assertEqual(al.enveloppe.numero,len(s.enregistrements)+len(s2.enregistrements)+1)
        self.assertEqual(al.enveloppe.bras,b.nom)

    def test_bougie_inconnue_et_issue_future_refusees(self):
        b,p,h,per=composer_bras()
        with self.assertRaises(ErreurOrchestration):b.sur_bougie({})
        with self.assertRaises(ErreurOrchestration):b.appliquer_issue({})
        k=CleIntention(b.identifiant,C.technique.london['strategy_id'],'EURUSD',T,'ACHAT')
        with self.assertRaises(ErreurOrchestration):b.appliquer_issue(Issue(k,'REMPLIE',T+1))
        self.assertEqual(len(b.etat.historique),0)

    def test_etat_scelle_d_un_autre_deploiement_refuse(self):
        b,p,_,_=composer_bras();etat=b.etat
        d=replace(b.deploiement,identifiant='autre_deploiement')
        with self.assertRaises(ErreurOrchestration):construire_bras(C,d,b.nom,p.profils,p,b.fondamental,T,
            observation=p.observation(),base_utc=p.base_utc(),etat=etat)

    def test_bougie_pas_encore_disponible_refusee(self):
        ticks=ticks_courts();b,p,h,per=composer_bras(ticks=ticks)
        f=flux(h,per)['EURUSD'];v=tuple(e for t in ticks[:2] for e in f.sur_tick(t) if hasattr(e,'bougie'))
        self.assertTrue(v)
        with self.assertRaises(ErreurOrchestration):b.sur_bougie(v[0])

    def test_appels_de_calcul_rejoues_sans_backend(self):
        _,p,_,_=composer_bras();j=PortCalculJournalise(p)
        compte=j.etat_compte();profil=j.specifications('EURUSD')
        gain=j.profit(profil,'ACHAT',D('.1'),D('1.1'),D('1.101'))
        traces=j.drainer();self.assertEqual([a.nom for a in traces],['etat_compte','specifications','profit'])
        class Interdit:
            def __getattr__(self,n):raise AssertionError('backend de calcul appelé')
        r=PortCalculJournalise(Interdit());r.debut_rejeu(traces)
        self.assertEqual(r.etat_compte(),compte);self.assertEqual(r.specifications('EURUSD'),profil)
        self.assertEqual(r.profit(profil,'ACHAT',D('.1'),D('1.1'),D('1.101')),gain)
        r.terminer_rejeu();self.assertEqual(r.drainer(),traces)

    def test_divergence_non_avalee_par_le_coordinateur(self):
        _,p,_,_=composer_bras();j=PortCalculJournalise(p);j.specifications('EURUSD');traces=j.drainer()
        j.debut_rejeu(traces)
        self.assertIsInstance(appeler_calcul(j,'specifications','GBPUSD'),RefusExecution)
        with self.assertRaises(ErreurOrchestration):j.terminer_rejeu()
        j=PortCalculJournalise(p);j.debut_rejeu(traces)
        with self.assertRaises(ErreurOrchestration):j.terminer_rejeu()

    def test_erreur_backend_normalisee_sans_message_brut(self):
        class Panne:
            def etat_compte(self):raise OSError('message à ne pas conserver')
        j=PortCalculJournalise(Panne());r=j.etat_compte()
        self.assertIsInstance(r,RefusExecution)
        a,=j.drainer();self.assertEqual(a.resultat,r)
        self.assertNotIn('message à ne pas conserver',str(a))

    def test_journal_cloture_avec_etat_public_reconstruit(self):
        ticks=ticks_courts();b,p,h,per=composer_bras(ticks=ticks);f=flux(h,per)['EURUSD']
        f.sur_tick(ticks[0]);evenements=f.sur_tick(ticks[1]);bougie=next(v for v in evenements if hasattr(v,'bougie'))
        p.avancer_au(ticks[1].instant_reception_ms)
        lot=b.coordinateur.traiter(p.instant_ms,base_utc=p.base_utc());b.consommer(lot,p.instant_ms)
        resultat,=b.sur_bougie(bougie)
        r=b.journaliser_cloture(bougie,resultat,lot.compte,permission={'scenario':'TECHNICAL_CONTROL_NEUTRAL'})
        self.assertEqual(r.type.value,'CLOTURE')
        self.assertEqual(r.vers_dict()['etat_strategie']['bougies'],1)
        self.assertEqual(r.vers_dict()['permission']['scenario'],'TECHNICAL_CONTROL_NEUTRAL')
        self.assertEqual(r.enveloppe.bras,b.nom)
