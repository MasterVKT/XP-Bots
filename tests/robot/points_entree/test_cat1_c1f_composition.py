"""Composition réelle, portes de rattrapage et reconstruction sans backend."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.orchestration import C
from robot.points_entree.test_cat1_c1a_livre_papier import livre
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1a_livre_papier import LivrePapier
from xpbots.app.c1f_composition_moteur import PortCompte,composer_moteur,rejouer_incident
from xpbots.execution.c0a_types import RefusExecution,OrdreCalcule
from xpbots.orchestration.c0_contrats import MiseAJourBras
from xpbots.noyau.c1a_marche import Tick


def composition(ab=False):
    b,p,_=livre();p.fixer_disponibilite('EURUSD',True,p.instant_ms)
    ports={'REFERENCE':p}
    if ab:
        v=p.initialisation;q=LivrePapier(C,v['conditions'],v['creation_ms'],v['scenario'])
        q.avancer_au(p.instant_ms);q.fixer_disponibilite('EURUSD',True,q.instant_ms);ports['IA']=q
    i=dict(schema='xp-composition-direct-v1',configuration=C,deploiement='FIXTURE_COMPOSITION',
        mode='PAPER_AB' if ab else 'PAPER',longueur_empreinte=16,profils={'EURUSD':b.profil},
        horaires={'EURUSD':b.profil.horaires},periodes_couvertes={'EURUSD':()},
        initiales={n:dict(profil_compte=q.profil_compte,instant_ms=q.instant_ms,
            observation=q.observation(),base_utc=q.base_utc()) for n,q in ports.items()},
        scenario_fondamental='TECHNICAL_CONTROL_NEUTRAL',table_heure=None,
        politique_ia=dict(bras_ia=ab,execution_reelle=False,validation_financiere=False))
    return i,ports


def evenement(m,ports,n=0):
    t=next(iter(ports.values())).instant_ms+100
    tick=Tick('EURUSD','EURUSD',t,t,n,1.1003,1.1004)
    maj=[]
    for nom,p in ports.items():
        r=p.sur_tick(tick)
        maj.append((nom,MiseAJourBras(reponses=r,observation=p.observation(),base_utc=p.base_utc())))
    return m.traiter_ticks((tick,),mises_a_jour=tuple(maj))


class TestComposition(unittest.TestCase):
    def test_marqueurs_de_reprise_types_scelles_et_ordonnes_requis(self):
        i,p=composition();m=composer_moteur(C,i,p);appels=dict(m.initialisation_calculs)
        avant=m.exporter_checkpoint_journal();evenement(m,p);apres=m.exporter_checkpoint_journal()
        with self.assertRaisesRegex(ErreurApplication,'MARQUEUR_REPRISE_INVALIDE'):
            rejouer_incident(C,i,appels,m.entrees,apres,reprises=({},))
        with self.assertRaisesRegex(ValueError,'altere'):
            rejouer_incident(C,i,appels,m.entrees,apres,reprises=(replace(avant,empreinte='0'*64),))
        with self.assertRaisesRegex(ErreurApplication,'MARQUEUR_REPRISE_HORS_PREFIXE'):
            rejouer_incident(C,i,appels,m.entrees,apres,reprises=(apres,avant))

    def test_configuration_complete_fermee_et_comptes_exacts(self):
        i,p=composition();composer_moteur(C,i,p)
        for mauvais in (dict(i,extra=True),dict(i,schema='INVENTE'),dict(i,initiales={}),dict(i,mode='REJEU')):
            with self.subTest(mauvais=tuple(mauvais)):
                with self.assertRaises(ErreurApplication):composer_moteur(C,mauvais,p)
        faux=replace(C,technique=replace(C.technique,commun=replace(C.technique.commun,account_currency='INVENTEE')))
        with self.assertRaisesRegex(ErreurApplication,'ETRANGERE'):composer_moteur(faux,i,p)

    def test_neutre_interdit_et_politique_native_explicite(self):
        i,p=composition();i['mode']='DEMO'
        with self.assertRaisesRegex(ErreurApplication,'POLITIQUE'):composer_moteur(C,i,p)
        i['politique_ia']['execution_reelle']=True
        with self.assertRaisesRegex(ErreurApplication,'FONDAMENTAL'):composer_moteur(C,i,p)

    def test_rejeu_initialisation_et_corps_sans_backend_et_troncature_refusee(self):
        i,p=composition();m=composer_moteur(C,i,p);sorties=(evenement(m,p),evenement(m,p,1))
        r,ss=rejouer_incident(C,i,dict(m.initialisation_calculs),m.entrees,m.exporter_checkpoint_journal())
        self.assertEqual(ss,sorties);self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
        with self.assertRaisesRegex(ErreurApplication,'DIVERGENT'):
            rejouer_incident(C,i,dict(m.initialisation_calculs),m.entrees[:-1],m.exporter_checkpoint_journal())
        with self.assertRaisesRegex(ErreurApplication,'APPELS_INITIAUX'):
            rejouer_incident(C,i,{},m.entrees,m.exporter_checkpoint_journal())
        with self.assertRaisesRegex(ErreurApplication,'APPELS_INITIAUX'):
            rejouer_incident(C,i,None,m.entrees,m.exporter_checkpoint_journal())

    def test_rattrapage_refuse_admission_conserve_calculs_et_remplacements(self):
        b,p,c=livre();p.fixer_disponibilite('EURUSD',True,p.instant_ms)
        port=PortCompte(p,p.profil_compte)
        o=OrdreCalcule(c.cle,c.donnees['symbole_courtier'],c.donnees['volume'],
            c.donnees['prix'],c.donnees['sl'],c.donnees['tp'])
        self.assertIsInstance(port.controler(o,p.etat_compte()),RefusExecution)
        self.assertEqual(port.profit(b.profil,c.cle.sens,D('.1'),D('1.1'),D('1.101')),
                         p.profit(b.profil,c.cle.sens,D('.1'),D('1.1'),D('1.101')))
        self.assertEqual(port.controler(o,p.etat_compte(),True),p.controler(o,p.etat_compte(),True))
        port.fixer_disponibilite(('EURUSD',))
        self.assertEqual(port.controler(o,p.etat_compte()),p.controler(o,p.etat_compte()))
        with self.assertRaises(ErreurApplication):port.fixer_disponibilite('EURUSD')
