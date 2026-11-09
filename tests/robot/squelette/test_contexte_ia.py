"""Couture phase 8 : lecteur réel, C05 réel, coordinateur et London sans doublure interne."""
from dataclasses import replace
from datetime import date,time
from decimal import Decimal as D
import unittest

from robot.outils.contexte_ia import evenement as veto,octets,snapshot,parametres
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.fabrique_ticks import ticks_de_bougies,lignes_csv
from robot.squelette.test_fondamental import C,T,S,SignalUnique,ticks_courts,composer,permission,export
from xpbots.app.rejeu_squelette import composer_rejeu_papier
from xpbots.contexte_ia.c0_types import PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.execution.c4_cycle import NatureReponse
from xpbots.noyau.c1a_marche import Tick
from xpbots.rejeu.squelette import (PaquetSnapshot,SourceSnapshotScenario,StockageMemoirePapier,
    ContratPapier,analyser_lignes_ticks,rejouer)


def paquet(t=S,fin=S+120000,sequence=1):
    return PaquetSnapshot(t,octets(snapshot(sequence=sequence,genere=t,
        evenements=[veto(debut=t,fin=fin)])))


def construire(ticks=None,paquets_ia=(),paquets_c05=None,lecteur=None,strategie=None):
    ticks=ticks_courts() if ticks is None else ticks
    l=lecteur if lecteur is not None else LecteurContexte(parametres(),PolitiqueVeto(True))
    source=SourceSnapshotScenario(l,paquets_ia)
    m,e,s,p=composer(ticks,[export(),permission()] if paquets_c05 is None else paquets_c05,
        SignalUnique() if strategie is None else strategie,lecteur_ia=l,source_ia=source)
    return m,e,s,p,l


def lancer(**options):
    ticks=options.get('ticks',ticks_courts());m,e,s,p,l=construire(**options)
    r=rejouer(ticks,m,e,s)
    return r,[x.vers_dict() for x in r.enregistrements],e,l


class TestCoutureContexteIA(unittest.TestCase):
    def test_veto_reel_refuse_avec_preuve_journalisee(self):
        r,l,e,ia=lancer(paquets_ia=[paquet()])
        self.assertFalse(any(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses))
        refus=next(v for v in l if v.get('motif')=='AI_CONTEXT_VETO')
        self.assertEqual((refus['detail'],refus['bras']),('evenement_1','IA'))
        d=refus['snapshot_ia'];self.assertEqual(d['decision'],'BLOCK')
        self.assertEqual((d['vetos'][0]['event_id'],d['vetos'][0]['connu_ms']),('evenement_1',S))
        self.assertEqual(d['vetos'][0]['provider_id'],next(iter(sorted(parametres().fournisseurs))))
        self.assertTrue(any(v.get('alerte')=='SNAPSHOT_ACCEPTE' and v['sequence']==1 for v in l))
        self.assertEqual(r.nombre_ticks,len(ticks_courts()))

    def test_neutral_n_autorise_jamais_c05_absent(self):
        for paquets in ([],[PaquetSnapshot(S,b'{')]):
            r,l,_,_=lancer(paquets_ia=paquets,paquets_c05=[export()])
            self.assertFalse(any(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses))
            self.assertTrue(any(v.get('motif')=='FUNDAMENTAL_INVALID' for v in l))
            self.assertFalse(any(v.get('motif')=='AI_CONTEXT_VETO' for v in l))

    def test_snapshot_corrompu_preserve_veto_et_ne_cree_pas_de_bougie(self):
        r,l,_,_=lancer(paquets_ia=[paquet(S-1000),PaquetSnapshot(S,b'{')])
        self.assertTrue(any(v.get('motif')=='AI_CONTEXT_VETO' for v in l))
        self.assertTrue(any(v.get('alerte')=='SNAPSHOT_REJETE' for v in l))
        self.assertEqual(sum(v['type']=='CLOTURE' for v in l),1)
        self.assertEqual(r.nombre_ticks,len(ticks_courts()))

    def test_echeances_ia_sans_tick_ni_rafraichissement_cotation(self):
        ticks=ticks_courts();m,e,s,p,l=construire(ticks,paquets_ia=[paquet(S-1000,S-500)])
        # La réception et l'expiration sont deux minuteries distinctes entre les ticks.
        r=rejouer(ticks,m,e,s)
        lignes=[v.vers_dict() for v in r.enregistrements]
        self.assertTrue(any(v.get('alerte')=='SNAPSHOT_ACCEPTE' and v['instant_utc_ms']==S-1000 for v in lignes))
        self.assertEqual(len([v for v in r.reponses if v.nature is NatureReponse.REMPLISSAGE]),1)
        self.assertEqual(l.etat.dernier_ms,ticks[-1].instant_reception_ms)
        self.assertEqual(r.nombre_ticks,len(ticks))

    def test_revalidation_avant_envoi_voit_veto_arrive_pendant_persistance(self):
        ticks=ticks_courts();m,e,_,p,l=construire(ticks)
        class ArriveePendantPersistance(StockageMemoirePapier):
            def persister(self,lot):
                preuve=super().persister(lot)
                if lot.preparations:l.recevoir(paquet().octets,S)
                return preuve
        r=rejouer(ticks,m,e,ArriveePendantPersistance())
        self.assertFalse(any(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses))
        self.assertTrue(any(v.vers_dict().get('motif')=='AI_CONTEXT_VETO' for v in r.enregistrements))

    def test_veto_apres_fill_ne_cloture_pas_et_flatten_reste_obligatoire(self):
        for flatten in (False,True):
            t=S+30000
            ticks=ticks_courts()+[Tick('EURUSD','EURUSD',t-1,t-1,20,1.1,1.1001)]
            ticks.sort(key=lambda v:v.instant_reception_ms)
            c05=[export(),permission()]
            if flatten:c05.append(permission(t,2,risk_state='FLATTEN'))
            r,l,e,_=lancer(ticks=ticks,paquets_ia=[paquet(t)],paquets_c05=c05)
            self.assertEqual(sum(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses),1)
            closes=[v for v in r.reponses if v.nature is NatureReponse.CLOTURE]
            self.assertEqual(bool(closes),flatten)
            if flatten:self.assertEqual(closes[0].donnees['cause'].value,'FLATTEN')
            self.assertEqual(bool(e.positions_ouvertes),not flatten)

    def test_bras_reference_conserve_complement_absent(self):
        ticks=ticks_courts();m,e,s,p=composer(ticks,[export(),permission()],SignalUnique())
        r=rejouer(ticks,m,e,s);l=[v.vers_dict() for v in r.enregistrements]
        self.assertEqual(sum(v.nature is NatureReponse.REMPLISSAGE for v in r.reponses),1)
        self.assertTrue(all(v['bras']=='REFERENCE' for v in l))
        self.assertTrue(all(v['snapshot_ia'] is None for v in l if v['type'] in ('CLOTURE','INTENTION')))

    def test_source_refuse_recul_retard_type_et_mauvaise_liaison(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True))
        with self.assertRaises(ValueError):SourceSnapshotScenario(l,[paquet(),paquet(S-1)])
        with self.assertRaises(ValueError):SourceSnapshotScenario(l,[None])
        with self.assertRaises(ValueError):PaquetSnapshot(True,b'{}')
        with self.assertRaises(ValueError):PaquetSnapshot(S,'{}')
        source=SourceSnapshotScenario(l,[paquet()])
        with self.assertRaises(ValueError):source.recevoir(S+1)
        args=(C,ticks_courts(),{'EURUSD':D('.00001')},{'EURUSD':ContratPapier(D('1000'),D('.1'),D('1'),D('.1'))})
        with self.assertRaises(ValueError):composer_rejeu_papier(*args,scenario='TECHNICAL_CONTROL_NEUTRAL',source_ia=source)
        with self.assertRaises(ValueError):composer_rejeu_papier(*args,scenario='TECHNICAL_CONTROL_NEUTRAL',
            lecteur_ia=l,source_ia=SourceSnapshotScenario(l,[paquet(T-1)]))

    def test_reprise_ancienne_sans_recul_et_etat_futur_refuse(self):
        l=LecteurContexte(parametres(),PolitiqueVeto(True));l.recevoir(paquet(T,S+60000).octets,T)
        reprise=LecteurContexte(parametres(),l.politique,l.etat)
        ticks=[Tick('EURUSD','EURUSD',t,t,i,1.1,1.1001) for i,t in enumerate((T+120000,S,S+60000))]
        m,e,s,p,_=construire(ticks,lecteur=reprise,paquets_c05=[export(T+120000),permission()])
        r=rejouer(ticks,m,e,s)
        self.assertEqual(r.nombre_ticks,len(ticks))
        self.assertTrue(all(v.enveloppe.instant_utc_ms>=ticks[0].instant_reception_ms for v in r.enregistrements))
        self.assertEqual(reprise.evaluer('EURUSD',S+60000).etat.value,'NEUTRAL')
        l.avancer(S+120000)
        with self.assertRaises(ValueError):construire(ticks,lecteur=l)

    def test_rejeu_causal_deterministe_et_heartbeat_ne_prolonge_pas(self):
        premier=paquet(S-60000,S+30000)
        suivant=PaquetSnapshot(S+1000,octets(snapshot(sequence=2,genere=S+1000,
            evenements=[veto(debut=S-60000,fin=S+30000)])))
        options=dict(paquets_ia=[premier,suivant])
        r,l,_,ia=lancer(**options);r2,l2,_,_=lancer(**options)
        self.assertEqual(l,l2);self.assertEqual(r.reponses,r2.reponses)
        self.assertEqual(ia.evaluer('EURUSD',S+30000).etat.value,'NEUTRAL')
        self.assertTrue(any(v.get('motif')=='AI_CONTEXT_VETO' for v in l))

    def test_l15_vrai_london_ete_hiver_expiration_et_reception_tardive(self):
        cal=CalendrierLondres.depuis_parametres(C.technique.commun)
        for jour in (date(2026,7,15),date(2026,1,14)):
            session=cal.instant_local(jour,time(8));premier=session+900000;second=session+1800000
            bougies,_=journee_london_prechargee(jour,C.technique,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
            bougies=[replace(b,ouverture='1.10110',haut='1.10190',bas='1.10100',cloture='1.10180')
                if b.debut_ms==premier else replace(b,ouverture='1.10180',haut='1.10200',bas='1.10170',cloture='1.10180')
                if b.debut_ms>premier else b for b in bougies]
            ticks=list(analyser_lignes_ticks(lignes_csv(ticks_de_bougies('EURUSD',bougies))))
            # Publication 08:07, classification reçue 08:08, fin 08:22 ; aucun renouvellement.
            recu=session+8*60000;fin=session+22*60000
            evenement=veto(debut=recu,fin=fin)
            for tardif in (False,True):
                with self.subTest(jour=jour,tardif=tardif):
                    t=session+23*60000 if tardif else recu
                    l=LecteurContexte(parametres(),PolitiqueVeto(True));source=SourceSnapshotScenario(l,[
                        PaquetSnapshot(t,octets(snapshot(genere=t,evenements=[evenement])))])
                    m,e,s,p=composer(ticks,[export(session),permission(premier-60000),permission(second-60000,2)],
                        lecteur_ia=l,source_ia=source)
                    r=rejouer(ticks,m,e,s);lignes=[v.vers_dict() for v in r.enregistrements]
                    fills=[v for v in r.reponses if v.nature is NatureReponse.REMPLISSAGE]
                    self.assertEqual(len(fills),1)
                    attendue=premier if tardif else second
                    self.assertGreater(fills[0].instant_ms,attendue)
                    self.assertLess(fills[0].instant_ms,attendue+900000)
                    vetos=[v for v in lignes if v.get('motif')=='AI_CONTEXT_VETO']
                    if tardif:self.assertFalse(vetos)
                    else:
                        self.assertTrue(vetos)
                        self.assertEqual(vetos[0]['instant_utc_ms'],premier)
                    # Pas de rattrapage à 08:22 et pas de veto sur l'ancienne bougie à 08:23.
                    self.assertFalse(any(v['type']=='ORDRE' and v.get('commande')=='ENTREE'
                        and fin<=v['instant_utc_ms']<second for v in lignes))
                    self.assertEqual(r.nombre_ticks,len(ticks))
