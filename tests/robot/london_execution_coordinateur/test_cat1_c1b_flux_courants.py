"""Les fonds identifies ne modifient pas le resultat de trading de la garde."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import T,commun
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c1b_gardes import GardesCompte,MouvementCompte,reconstituer_base_utc
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif

MINUIT=T//86400000*86400000


def compte(t,eq):return EtatCompte(t,D(eq),D(eq),D(0))
def base(c,mouvements=(),*,debut=MINUIT,depuis=None):
    options={} if depuis is None else dict(depuis_flux_ms=depuis)
    return reconstituer_base_utc(c,mouvements,Intervalle(debut,c.instant_ms+1),aucune_position_minuit=True,**options)
def garde():
    g=GardesCompte(commun());c=compte(T,100);g.observer(c,base(c));return g


class TestFluxCourants(unittest.TestCase):
    def test_apport_qualifie_translate_base_et_pic_avant_seuil_quotidien(self):
        g=garde();m=MouvementCompte('depot',T+1,D(100),True);c=compte(T+1,200)
        self.assertIsNone(g.observer(c,base(c,(m,))))
        self.assertEqual((g.etat.base_quotidienne,g.etat.pic,g.etat.references),(D(200),D(200),('depot',)))
        c=compte(T+2,196);b=base(c,(m,MouvementCompte('perte',T+2,D(-4))))
        self.assertEqual(g.observer(c,b).motif,Motif.DAILY_LOSS_LOCK)

    def test_retrait_qualifie_ne_ressemble_pas_a_une_perte(self):
        g=garde();m=MouvementCompte('retrait',T+1,D(-50),True);c=compte(T+1,50)
        self.assertIsNone(g.observer(c,base(c,(m,))))
        self.assertEqual((g.etat.base_quotidienne,g.etat.pic),(D(50),D(50)))
        self.assertFalse(g.etat.arret_global)
        c=compte(T+2,49)
        self.assertEqual(g.observer(c,base(c,(m,MouvementCompte('perte',T+2,D(-1))))).motif,Motif.DAILY_LOSS_LOCK)

    def test_flux_repete_reprise_et_neutralisation_explicite_restent_idempotents(self):
        for explicite in (False,True):
            g=garde();m=MouvementCompte('depot',T+1,D(50),True)
            if explicite:g.neutraliser_flux(D(50),'depot')
            for t in (T+1,T+2):
                c=compte(t,150);self.assertIsNone(g.observer(c,base(c,(m,))))
                g=GardesCompte(commun(),g.etat)
                self.assertEqual((g.etat.base_quotidienne,g.etat.pic),(D(150),D(150)))
                self.assertEqual(g.etat.references,('depot',))

    def test_retrait_survenu_hier_pendant_arret_translate_ancien_pic(self):
        g=garde();m=MouvementCompte('retrait-hier',T+1,D(-50),True)
        c=compte(T+86400000,50);b=base(c,(m,),depuis=T)
        self.assertEqual(b.base_neutralisee,D(50));self.assertEqual(b.references_flux,('retrait-hier',))
        self.assertIsNone(g.observer(c,b))
        self.assertEqual((g.etat.base_quotidienne,g.etat.pic),(D(50),D(50)))

    def test_depot_survenu_hier_nefface_pas_le_drawdown_du_pic_anterieur(self):
        g=garde();g.observer(compte(T+1,110));g.observer(compte(T+2,100))
        m=MouvementCompte('depot-hier',T+3,D(100),True);c=compte(T+86400000,200)
        self.assertIsNone(g.observer(c,base(c,(m,),depuis=T+2)))
        self.assertEqual(g.etat.base_quotidienne,D(200));self.assertEqual(g.etat.pic,D(210))

    def test_minuit_exact_reste_equite_mais_conserve_le_pic_translate(self):
        g=garde();m=MouvementCompte('retrait-hier',T+1,D(-50),True)
        c=compte(MINUIT+86400000,50)
        self.assertIsNone(g.observer(c,base(c,(m,),depuis=T)))
        self.assertEqual((g.etat.base_quotidienne,g.etat.pic,g.etat.references),(D(50),D(50),('retrait-hier',)))

    def test_arrets_persistants_ne_sont_pas_leves_par_un_apport(self):
        g=garde();g.observer(compte(T+1,90));self.assertTrue(g.etat.arret_global)
        m=MouvementCompte('depot',T+2,D(100),True);c=compte(T+2,190)
        g.observer(c,base(c,(MouvementCompte('perte',T+1,D(-10)),m)))
        self.assertTrue(g.etat.arret_global);self.assertTrue(g.etat.verrou_quotidien)
        c=compte(T+86400000,190);g.observer(c,base(c,(m,),depuis=T+1))
        self.assertTrue(g.etat.arret_global)

    def test_preuve_future_ou_dun_autre_instant_et_flux_inconnu_ne_mutent_rien(self):
        g=garde();avant=g.etat;m=MouvementCompte('depot',T+1,D(50),True);c=compte(T+1,150)
        b=base(c,(m,))
        self.assertEqual(g.observer(c,replace(b,instant_ms=T+2)).motif,Motif.ENVIRONMENT_NOT_READY)
        self.assertEqual(g.etat,avant)
        self.assertEqual(g.observer(replace(c,flux_externe_non_neutralise=True),b).motif,Motif.ENVIRONMENT_NOT_READY)
        self.assertEqual(g.etat,avant)
        with self.assertRaises(ValueError):replace(b,flux_identifies=(MouvementCompte('depot',T+2,D(50),True),))
        with self.assertRaises(ValueError):base(c,(m,),depuis=T+2)
        r=base(compte(T+86400000,150),(m,),debut=MINUIT+86400000,depuis=T)
        self.assertEqual(r.motif,Motif.ENVIRONMENT_NOT_READY)

    def test_pic_de_solde_prouve_pendant_interruption_nest_pas_oublie(self):
        mouvements=(MouvementCompte('profit',T+1,D(20)),MouvementCompte('perte',T+2,D(-12)))
        for t in (T+3,MINUIT+86400000,T+86400000):
            with self.subTest(reprise=t):
                g=garde();c=compte(t,108);b=base(c,mouvements,depuis=T)
                self.assertEqual(b.pic_solde_neutralise,D(120))
                r=g.observer(c,b)
                self.assertIsNotNone(r)
                self.assertEqual(r.motif,Motif.GLOBAL_DRAWDOWN_HALT)
                self.assertEqual(g.etat.pic,D(120))
