"""Couture S3/S4 : vrai coordinateur, stratégie injectée, journal et persistance."""
from datetime import date
from decimal import Decimal as D
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.couture_execution import composer,enregistrements,journee_executable
from robot.outils.fabrique_ticks import lignes_csv
from robot.outils.london import strategie_squelette
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1c_domaine import SignalTechnique
from xpbots.noyau.c2_journal import TypeEnregistrement
from xpbots.orchestration.squelette import Strategie
from xpbots.rejeu.squelette import analyser_lignes_ticks,rejouer
C=configuration_figee();M15=C.technique.commun.timeframe_seconds*1000
class Signale:
    identifiant='LONDON_V3'
    def __init__(self): self.issues=[]
    def sur_bougie(self,b):
        if b.unite.value!='M15': return None
        x=b.bougie
        return SignalTechnique(self.identifiant,x.symbole,x.fin_ms,'ACHAT',x.cloture,.001,x.cloture-.1,2)
    def sur_issue(self,i): self.issues.append(i)
def suite():
    return [Tick('EURUSD','EURUSD',i*M15,i*M15,i,1.1,1.1001) for i in range(4)]
class TestCoutureCoordinateur(unittest.TestCase):
    def test_strategie_reelle_structurelle(self):
        self.assertIsInstance(strategie_squelette(C),Strategie)
    def test_clotures_et_numerotation(self):
        lignes=enregistrements(suite())
        self.assertEqual([e['type'] for e in lignes],[TypeEnregistrement.RAPPROCHEMENT]+[TypeEnregistrement.CLOTURE]*3)
        self.assertEqual([e['numero'] for e in lignes],[1,2,3,4])
        self.assertEqual(lignes[0]['empreinte_regles']['technique'],C.technique.empreinte_canonique)
    def test_signal_refuse_par_un_vrai_controle(self):
        strategie=Signale();lignes=enregistrements(suite(),strategie)
        intentions=[e for e in lignes if e['type']==TypeEnregistrement.INTENTION]
        self.assertTrue(intentions)
        self.assertTrue(all(e['issue']['nature']=='REFUSEE' for e in intentions))
        self.assertTrue(all(e['motif']=='STOP_TOO_WIDE' for e in intentions),[(e['motif'],e['detail']) for e in intentions])
        self.assertEqual(len(strategie.issues),len(intentions))
        self.assertEqual([i.cle.texte() for i in strategie.issues],[e['cle'] for e in intentions])
    def test_faits_natifs_et_intentions_journalises(self):
        _,fab=journee_executable(date(2026,7,15),C.technique)
        ticks=list(analyser_lignes_ticks(lignes_csv(fab)))
        m,e,s=composer(ticks);r=rejouer(ticks,m,e,s)
        self.assertEqual(sum(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses),1)
        self.assertEqual(sum(x.nature is NatureReponse.CLOTURE for x in r.reponses),1)
        intentions=[x.vers_dict() for x in r.enregistrements if x.type is TypeEnregistrement.INTENTION]
        issues=[i for x in intentions for i in x['issues_nouvelles']]
        self.assertEqual([i['nature'] for i in issues],['REMPLIE','CLOTUREE'])
        self.assertEqual(len({x['cle'] for x in intentions}),1)
        self.assertEqual(intentions[-1]['reservations']['reservations'],())
        self.assertTrue(all(x['permission']['scenario']=='TECHNICAL_CONTROL_NEUTRAL' for x in intentions))
        self.assertTrue(all(x['budget_gele']==D('.5') for x in intentions))
    def test_pas_d_entree_si_transaction_memoire_echoue(self):
        _,fab=journee_executable(date(2026,7,15),C.technique)
        ticks=list(analyser_lignes_ticks(lignes_csv(fab)))
        m,e,_=composer(ticks)
        class StockageIndisponible:
            def persister(self,lot): raise OSError('panne synthétique')
        r=rejouer(ticks,m,e,StockageIndisponible())
        self.assertFalse(any(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses))
        self.assertTrue(any(x.vers_dict().get('alerte')=='STOCKAGE_REJEU_INDISPONIBLE' for x in r.enregistrements))
    def test_symboles_independants(self):
        ticks=[Tick(s,s,t,t,i,1.1,1.1001) for i,(t,s) in enumerate(((0,'GBPUSD'),(0,'EURUSD'),(M15,'GBPUSD'),(M15,'EURUSD')))]
        self.assertEqual({x['symbole'] for x in enregistrements(ticks) if x['type'] is TypeEnregistrement.CLOTURE},{'EURUSD','GBPUSD'})
    def test_groupes_refuses_si_instants_differents(self):
        m,_,_=composer(suite())
        with self.assertRaises(ValueError): m.traiter_ticks(suite())
