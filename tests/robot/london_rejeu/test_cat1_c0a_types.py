"""Catégorie 1, couche 0a : valeurs et provenance ; noyau réel."""
from dataclasses import FrozenInstanceError,replace
from datetime import date,datetime
from decimal import Decimal as D,Context,localcontext
import unittest
from robot.outils.orchestration import T,composer_bras
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import CleIntention,CauseCloture
from xpbots.rejeu.c0a_types import (ErreurRejeu,TarifCommission,ConditionContrat,ManifesteTicks,
    Trade,PointCompte,JourMarche,ValeurJour,FactureIA,EcartRejeu,instant,entier,texte,montant)


def tarif():return TarifCommission('tarif_fixture',D('2'),D('.5'),D('3'),D('.4'))


def manifeste():
    b,_,h,_=composer_bras()
    return ManifesteTicks('fixture',{'EURUSD':'EURUSD'},Intervalle(T,T+3600000),
        (Intervalle(T,T+3600000),),(),'a'*64,date(2026,11,10),'fabrique','DECIMALE_NATIVE',h)


def trade(**options):
    v=dict(cle=CleIntention('essai','LONDON_V3','EURUSD',T,'ACHAT'),entree_ms=T+1,sortie_ms=T+10,
        volume=D('.1'),prix_entree=D('1.1'),prix_sortie=D('1.2'),profit_brut=D('2'),
        frais_entree=D('.1'),frais_sortie=D('.2'),risque_initial=D('.5'),cause=CauseCloture.TAKE_PROFIT)
    v.update(options);return Trade(**v)


class TestTypesRejeu(unittest.TestCase):
    def test_primitives_refusent_bool_types_et_non_finis(self):
        for fonction,valeurs in ((instant,(True,-1,1.5)),(entier,(False,-1,'2')),
            (texte,('',None,'\ud800')),(montant,(1,.5,True,D('NaN'),D('Infinity')))):
            for v in valeurs:
                with self.subTest(f=fonction.__name__,v=repr(v)),self.assertRaises(ErreurRejeu):fonction(v)
        self.assertEqual((instant(T),entier(0),texte('source'),montant(D('-2'))),(T,0,'source',D('-2')))

    def test_commissions_minimales_non_lineaires(self):
        t=tarif();self.assertEqual(t.entree(D('.1')),D('.5'));self.assertEqual(t.entree(D(1)),D(2))
        self.assertEqual(t.sortie(D('.1')),D('.4'));self.assertEqual(t.sortie(D(1)),D(3))
        with self.assertRaises(FrozenInstanceError):t.minimum_entree=D(0)

    def test_commissions_inconnues_negatives_et_volume_nul_refuses(self):
        for v in (None,0,D('-1'),D('NaN')):
            with self.subTest(v=v),self.assertRaises(ErreurRejeu):replace(tarif(),minimum_entree=v)
        for v in (D(0),D('-1'),True):
            with self.assertRaises(ErreurRejeu):tarif().entree(v)

    def test_condition_dates_effet_et_connaissance(self):
        b,_,_,_=composer_bras();c=ConditionContrat(T,T+1000,T+1,b.profils['EURUSD'],tarif())
        self.assertFalse(c.connue_a(T));self.assertTrue(c.connue_a(T+1));self.assertFalse(c.connue_a(T+1000))
        for kw in ({'fin_ms':T},{'connu_ms':T+1000},{'profil':None},{'tarif':None}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):replace(c,**kw)

    def test_manifeste_fige_liaisons_couverture_et_horaires(self):
        m=manifeste();s=dict(m.symboles);h=dict(m.horaires);c=list(m.couverture)
        copie=replace(m,symboles=s,horaires=h,couverture=c)
        s.clear();h.clear();c.clear();self.assertEqual(copie,m)
        with self.assertRaises(TypeError):copie.symboles['EURUSD']='autre'

    def test_manifeste_refuse_integrite_ordre_resolution_conversion(self):
        for kw in ({'sha256':'A'*64},{'sha256':'x'},{'sequence_origine':'DEVINE'},
            {'resolution_ms':True},{'resolution_ms':1000},{'conversion_utc_qualifiee':False},
            {'date_recuperation':datetime(2026,11,10)},{'usage':'TEST_INDEPENDANT'},
            {'source':''},{'precision_prix':''}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):replace(manifeste(),**kw)

    def test_manifeste_refuse_symboles_doubles_et_horaires_incomplets(self):
        for kw in ({'symboles':{}},{'symboles':{'EURUSD':'m','GBPUSD':'m'}},{'horaires':{}},
            {'horaires':{'EURUSD':None}},{'symboles':{'EURUSD':''}}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):replace(manifeste(),**kw)

    def test_couverture_trous_separes_sans_invention(self):
        m=replace(manifeste(),couverture=(Intervalle(T,T+10),Intervalle(T+20,T+3600000)),trous=(Intervalle(T+10,T+20),))
        self.assertEqual(m.trous,(Intervalle(T+10,T+20),))
        for kw in ({'couverture':(Intervalle(T+1,T+100),Intervalle(T,T+2))},
            {'trous':(Intervalle(T+1,T+2),)}, {'couverture':(Intervalle(T-1,T+2),)}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):replace(manifeste(),**kw)

    def test_trade_net_et_r_sans_seconde_reserve(self):
        t=trade();self.assertEqual(t.net,D('1.7'));self.assertEqual(t.r_net,D('3.4'))
        self.assertEqual(trade(profit_brut=D('-2')).net,D('-2.3'))

    def test_trade_causal_et_montants_valides(self):
        for kw in ({'entree_ms':T-1},{'sortie_ms':T},{'volume':D(0)},{'prix_sortie':D('-1')},
            {'risque_initial':D(0)},{'profit_brut':D('NaN')},{'frais_entree':D('-1')},{'cause':'TP'}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):trade(**kw)

    def test_contexte_immuable_en_profondeur(self):
        v={'mesures':{'composantes':[D('1.1'),D('1.2')]}}
        t=trade(contexte=v);v['mesures']['composantes'].clear()
        self.assertEqual(t.contexte['mesures']['composantes'],(D('1.1'),D('1.2')))
        with self.assertRaises(TypeError):t.contexte['mesures']['autre']=1
        with self.assertRaises(ErreurRejeu):trade(contexte={'v':float('nan')})

    def test_fonds_propres_distinguent_flottant_et_solde_meme_negatifs(self):
        p=PointCompte(T,D('-1'),D(100),D('.1'));self.assertNotEqual(p.fonds_propres,p.solde)
        with self.assertRaises(ErreurRejeu):replace(p,marge_utilisee=D('-1'))

    def test_jour_zero_et_frontieres_de_periodes(self):
        j=date(2026,11,9);self.assertEqual(ValeurJour(j,'validation',D(0),0).trades_clos,0)
        self.assertNotEqual(JourMarche(j,'validation'),JourMarche(j,'reserve'))
        with self.assertRaises(ErreurRejeu):ValeurJour(j,'validation',D(0),True)
        with self.assertRaises(ErreurRejeu):JourMarche(datetime(2026,11,9),'x')

    def test_allocation_facture_exacte_et_copie_des_methodes(self):
        methodes=['LONDON_V3','EMA_V3'];f=FactureIA('facture',T,D('.03'),methodes,'EVENEMENT')
        methodes.clear();self.assertEqual(dict(f.allocation()),{'LONDON_V3':D('.015'),'EMA_V3':D('.015')})
        trois=replace(f,methodes=('a','b','c'),montant_usd=D(1))
        with localcontext(Context(prec=48)):
            self.assertEqual(sum(trois.allocation().values()),D(1))
        with self.assertRaises(TypeError):f.allocation()['a']=D(0)

    def test_facture_refuse_doublons_cout_inconnu_et_nature(self):
        f=FactureIA('f',T,D(0),('LONDON_V3',),'JOURNAL',False)
        for kw in ({'methodes':('a','a')},{'methodes':()},{'montant_usd':None},{'montant_usd':D('-1')},
            {'nature':'PREDICTION'},{'reelle':1}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):replace(f,**kw)

    def test_ecarts_de_rejeu_types_sans_autorisation_implicite(self):
        self.assertEqual(EcartRejeu('objectif','OBJECTIF',D('.9')).champ,'OBJECTIF')
        self.assertEqual(EcartRejeu('duree','DUREE',6480).valeur,6480)
        for champ,v in (('DUREE',True),('DUREE',0),('OBJECTIF',.9),('BUFFER',D(0)),('RISQUE',D(2))):
            with self.subTest(champ=champ,v=v),self.assertRaises(ErreurRejeu):EcartRejeu('ecart',champ,v)
