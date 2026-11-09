"""Phase 9 : façade, pilote et composition réels, sans courtier ni service distant."""
from dataclasses import replace
from datetime import date,time
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from robot.outils.contexte_ia import parametres
from robot.outils.couture_execution import journee_executable
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.fabrique_ticks import lignes_csv,ticks_de_bougies,ecrire_csv
from robot.squelette.test_fondamental import C,T,S,SignalUnique,permission,export,ticks_courts
from robot.squelette.test_contexte_ia import paquet
from robot.squelette.test_s7_point_entree import executer
from robot.outils.chemins import RACINE_DEPOT
from robot.outils.fondamental import ConversionServeurScenario
from xpbots.app.rejeu_squelette import composer_rejeu_papier_ab
from xpbots.contexte_ia.c0_types import PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.noyau.c1a_marche import Tick
from xpbots.orchestration.c0_contrats import FabriqueStrategie
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.rejeu.squelette import (ContratPapier,SourceFondamentaleScenario,SourceSnapshotScenario,
    StockageMemoirePapier,analyser_lignes_ticks,rejouer_ab)


def composer(ticks,paquets_c05=(),paquets_ia=(),*,neutre=False,fabriques=None):
    ia=LecteurContexte(parametres(),PolitiqueVeto(True))
    fond=None if neutre else PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
    source=None if neutre else SourceFondamentaleScenario(fond,paquets_c05)
    m,e,s=composer_rejeu_papier_ab(C,ticks,{'EURUSD':D('.00001')},
        {'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))},
        controle_fondamental=fond,source_fondamentale=source,
        scenario='TECHNICAL_CONTROL_NEUTRAL' if neutre else None,lecteur_ia=ia,
        source_ia=SourceSnapshotScenario(ia,paquets_ia),fabriques=fabriques)
    return m,e,s


def fabrique(classe=SignalUnique):return (FabriqueStrategie(SignalUnique.identifiant,lambda c,t:classe()),)


class TestOrchestrationAB(unittest.TestCase):
    def test_cli_vraie_journee_ab(self):
        _,fab=journee_executable(date(2026,7,15),C.technique)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=ecrire_csv(p/'ticks.csv',fab)
            code,sortie,erreurs=executer(['--racine-depot',str(RACINE_DEPOT),'--ticks',str(f),
                '--sortie',str(p/'sortie'),'--tick-size','EURUSD=0.00001','--mode','PAPER_AB'])
            self.assertEqual((code,erreurs),(0,''));r=json.loads(sortie)
            self.assertEqual((r['entrees_remplies'],r['positions_closes'],r['positions_ouvertes']),(2,2,0))
            lignes=[json.loads(l) for l in (p/'sortie/decisions.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual({x['bras'] for x in lignes},{'REFERENCE','IA'})
            self.assertEqual({x['mode'] for x in lignes},{C.ia.parametres['default_evaluation_mode']})

    def test_l15_london_ab_ete_hiver_positions_et_quotas_independants(self):
        cal=CalendrierLondres.depuis_parametres(C.technique.commun)
        for jour in (date(2026,7,15),date(2026,1,14)):
            with self.subTest(jour=jour):
                session=cal.instant_local(jour,time(8));premier=session+900000;second=session+1800000
                b,_=journee_london_prechargee(jour,C.technique,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
                b=[replace(v,ouverture='1.10110',haut='1.10190',bas='1.10100',cloture='1.10180') if v.debut_ms==premier else
                    replace(v,ouverture='1.10180',haut='1.10200',bas='1.10170',cloture='1.10180') if v.debut_ms>premier else v for v in b]
                ticks=list(analyser_lignes_ticks(lignes_csv(ticks_de_bougies('EURUSD',b))))
                m,e,s=composer(ticks,[export(session),permission(premier-60000),permission(second-60000,2)],
                    [paquet(session+8*60000,session+22*60000)])
                r=rejouer_ab(ticks,m,e,s);lignes=[x.vers_dict() for x in r.enregistrements]
                for n,t in (('REFERENCE',premier),('IA',second)):
                    fills=[v for v in r.reponses[n] if v.nature is NatureReponse.REMPLISSAGE]
                    self.assertEqual(len(fills),1);self.assertEqual(fills[0].cle.cloture_ms,t)
                    self.assertTrue(any(v.nature=='ISSUE' and v.valeur.nature.value=='REMPLIE' for v in m.bras[n].etat.historique))
                self.assertTrue(any(v.get('motif')=='AI_CONTEXT_VETO' and v['bras']=='IA' for v in lignes))
                self.assertFalse(any(v.get('motif')=='AI_CONTEXT_VETO' and v['bras']=='REFERENCE' for v in lignes))
                self.assertFalse(any(v.get('commande')=='ENTREE' and session+22*60000<=v['instant_utc_ms']<second for v in lignes))
                self.assertNotEqual(e['IA'].etat_compte().fonds_propres,e['REFERENCE'].etat_compte().fonds_propres)

    def test_journal_recu_c05_ia_rejoue_sans_backend(self):
        ticks=ticks_courts();m,e,s=composer(ticks,[export(),permission()],[paquet()],fabriques=fabrique())
        r=rejouer_ab(ticks,m,e,s)
        self.assertEqual(sum(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses['REFERENCE']),1)
        self.assertFalse(r.reponses['IA'])
        copie,p,_=composer(ticks,fabriques=fabrique())
        def interdit(*a,**kw):raise AssertionError('backend consulté')
        for port in p.values():
            for n in ('profit','marge','frais_aller_retour','frais_sortie','controler','specifications','etat_compte'):setattr(port,n,interdit)
        lignes=[]
        for j in m.entrees:lignes.extend(copie.rejouer(j).enregistrements)
        self.assertEqual(tuple(lignes),r.enregistrements);self.assertEqual(copie.entrees,m.entrees)
        self.assertTrue(any(j.entree.receptions for j in m.entrees))

    def test_natif_stop_avant_flatten_et_bougie_du_meme_instant(self):
        class ChaqueBougie(SignalUnique):
            def sur_bougie(self,b):self.signale=False;return super().sur_bougie(b)
        n=S+900000;ticks=[Tick('EURUSD','EURUSD',t,t,i,prix,prix+.0001)
            for i,(t,prix) in enumerate(((T,1.1),(S,1.1),(S+1,1.1),(n,1.098),(n+1,1.098)))]
        m,e,s=composer(ticks,[export(),permission(),permission(n,2,risk_state='FLATTEN')],fabriques=fabrique(ChaqueBougie))
        r=rejouer_ab(ticks,m,e,s)
        for nom in e:
            closes=[x for x in r.reponses[nom] if x.nature is NatureReponse.CLOTURE]
            self.assertEqual(len(closes),1);self.assertEqual(closes[0].donnees['cause'].value,'STOP_LOSS')
            self.assertEqual(sum(x.nature is NatureReponse.REMPLISSAGE for x in r.reponses[nom]),1)
            l=[x.vers_dict() for x in r.enregistrements if x.enveloppe.bras==nom and x.enveloppe.instant_utc_ms==n]
            fermeture=next(i for i,x in enumerate(l) if x['type']=='INTENTION' and any(v['nature']=='CLOTUREE' for v in x['issues_nouvelles']))
            bougie=next(i for i,x in enumerate(l) if x['type']=='CLOTURE')
            self.assertLess(fermeture,bougie)
            self.assertTrue(any(x.get('detail')=='RISK_STATE_FLATTEN' for x in l))

    def test_panne_stockage_d_un_bras_ne_bloque_pas_l_autre(self):
        ticks=ticks_courts();m,e,s=composer(ticks,[export(),permission()],fabriques=fabrique())
        class Panne:
            def persister(self,lot):raise OSError('panne synthétique')
        s['REFERENCE']=Panne();r=rejouer_ab(ticks,m,e,s)
        self.assertFalse(r.reponses['REFERENCE'])
        self.assertEqual(sum(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses['IA']),1)
        self.assertTrue(any(v.vers_dict().get('alerte')=='STOCKAGE_PAPIER_INDISPONIBLE' and v.enveloppe.bras=='REFERENCE' for v in r.enregistrements))

    def test_sorties_obligatoires_malgre_panne_stockage(self):
        ticks=ticks_courts();m,e,s=composer(ticks,[export(),permission(),permission(S+30000,2,risk_state='FLATTEN')],fabriques=fabrique())
        class PanneApresFill(StockageMemoirePapier):
            def persister(self,lot):
                if any(d.issue is not None and d.issue.nature.value in ('REMPLIE','CLOTUREE') for d in lot.etat.intentions):raise OSError('panne synthétique après fill')
                return super().persister(lot)
        s={n:PanneApresFill() for n in e};r=rejouer_ab(ticks,m,e,s)
        for n in e:
            self.assertTrue(any(x.nature is NatureReponse.CLOTURE and x.donnees['cause'].value=='FLATTEN' for x in r.reponses[n]))
            self.assertFalse(e[n].positions_ouvertes)

    def test_stockage_partage_refuse(self):
        ticks=ticks_courts();m,e,s=composer(ticks,neutre=True)
        with self.assertRaises(ValueError):rejouer_ab(ticks,m,e,{n:s['IA'] for n in e})
