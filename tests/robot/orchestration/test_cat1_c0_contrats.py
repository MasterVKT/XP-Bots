"""Catégorie 1 : contrats et frontières, sans moteur interne doublé."""
from dataclasses import FrozenInstanceError
from decimal import Decimal as D
from datetime import date
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.fondamental import table_importance
from xpbots.london.c2_moteur import fabriquer_strategie
from xpbots.execution.c4_cycle import PreuvePersistance
from xpbots.execution.c1b_gardes import BaseReconstituee
from xpbots.noyau.c2_journal import Enveloppe,TypeEnregistrement,enregistrement,empreintes_regles
from xpbots.noyau.c1a_marche import Tick
from xpbots.orchestration.c0_contrats import (ErreurOrchestration,Strategie,FabriqueStrategie,
    Deploiement,ReceptionExterne,MiseAJourBras,EntreeMoteur,SortieMoteur,SortieEvenement,entier,instant,texte,
    AppelCalcul,EntreeJournalisee)

C=configuration_figee()
F=FabriqueStrategie(C.technique.london['strategy_id'],fabriquer_strategie)


class TestContrats(unittest.TestCase):
    def test_fabrique_reelle_structurelle(self):
        self.assertIsInstance(F.construire(C,{'EURUSD':D('.00001')}),Strategie)
        with self.assertRaises(ErreurOrchestration):FabriqueStrategie('x',None)

    def test_deploiement_copie_collections_et_ne_construit_rien(self):
        appels=[];f=FabriqueStrategie('x',lambda *a:appels.append(a))
        tailles={'EURUSD':D('.00001')};fabriques=[f]
        d=Deploiement('d','REJEU',fabriques,tailles,16)
        tailles.clear();fabriques.clear()
        self.assertEqual(tuple(d.tailles_tick),('EURUSD',));self.assertEqual(d.fabriques,(f,));self.assertFalse(appels)
        with self.assertRaises(TypeError):d.tailles_tick['autre']=D(1)
        with self.assertRaises(FrozenInstanceError):d.mode='autre'

    def test_deploiement_invalides(self):
        for args in (('', 'REJEU',(F,),{'EURUSD':D(1)},16),('d','AUTRE',(F,),{'EURUSD':D(1)},16),
            ('d','REJEU',(F,F),{'EURUSD':D(1)},16),('d','REJEU',(),{'EURUSD':D(1)},16),
            ('d','REJEU',(F,),{'EURUSD':1.0},16),('d','REJEU',(F,),{'EURUSD':D('NaN')},16),
            ('d','REJEU',(F,),{'EURUSD':D(0)},16),('d','REJEU',(F,),{},16),('d','REJEU',(F,),{'EURUSD':D(1)},True)):
            with self.subTest(args=args),self.assertRaises(ErreurOrchestration):Deploiement(*args)

    def test_entiers_stricts(self):
        for v in (True,-1,1.0,'1'):
            with self.assertRaises(ErreurOrchestration):instant(v)
            with self.assertRaises(ErreurOrchestration):entier(v)
        with self.assertRaises(ErreurOrchestration):EntreeMoteur(0,0)

    def test_ticks_meme_reception_et_groupe_non_vide(self):
        t=Tick('EURUSD','EURUSD',0,0,1,1.1,1.1001)
        e=EntreeMoteur(0,1,'TICKS',[t]);self.assertEqual(e.ticks,(t,))
        for kwargs in ({'ticks':[t]},{'nature':'TICKS'},{'nature':'TICKS','ticks':[object()]},
            {'nature':'TICKS','ticks':[Tick('EURUSD','EURUSD',1,1,1,1.1,1.1001)]}):
            with self.assertRaises(ErreurOrchestration):EntreeMoteur(0,1,**kwargs)

    def test_mises_a_jour_typees_et_noms_uniques(self):
        m=MiseAJourBras();e=EntreeMoteur(0,1,mises_a_jour={'REFERENCE':m})
        self.assertEqual(e.mises_a_jour,(('REFERENCE',m),))
        for p in ((('AUTRE',m),),(('REFERENCE',m),('REFERENCE',m)),(('IA',object()),),('IA',)):
            with self.assertRaises(ErreurOrchestration):EntreeMoteur(0,1,mises_a_jour=p)
        for kwargs in ({'reponses':[object()]},{'observation':{}},{'base_utc':{}},{'preuve':{}}):
            with self.assertRaises(ErreurOrchestration):MiseAJourBras(**kwargs)

    def test_preuve_evenement_distinct(self):
        m=MiseAJourBras(preuve=PreuvePersistance(1,()))
        e=EntreeMoteur(0,1,'PERSISTANCE',mises_a_jour={'IA':m});self.assertEqual(e.mises_a_jour[0][1],m)
        for e in (lambda:EntreeMoteur(0,1,mises_a_jour={'IA':m}),
            lambda:EntreeMoteur(0,1,'PERSISTANCE'),lambda:EntreeMoteur(0,1,'PERSISTANCE',mises_a_jour={'IA':MiseAJourBras()})):
            with self.assertRaises(ErreurOrchestration):e()

    def test_receptions_formes_externes(self):
        table=table_importance()
        for r in (ReceptionExterne('SNAPSHOT',None),ReceptionExterne('PERMISSION',b'{}','EURUSD'),
            ReceptionExterne('CALENDRIER',b'{}',table=table),ReceptionExterne('INTERRUPTION',symbole='EURUSD')):
            self.assertEqual(EntreeMoteur(0,1,receptions=[r]).receptions,(r,))

    def test_receptions_incoherentes_refusees(self):
        for args in (('AUTRE',b'',None,None),('PERMISSION',None,'EURUSD',None),('PERMISSION',b'',None,None),
            ('INTERRUPTION',b'{}','EURUSD',None),('CALENDRIER',b'{}',None,None),('SNAPSHOT',b'{}','EURUSD',None)):
            with self.assertRaises(ErreurOrchestration):ReceptionExterne(*args)
        with self.assertRaises(ErreurOrchestration):EntreeMoteur(0,1,receptions=[{}])

    def test_collections_entree_independantes(self):
        r=[ReceptionExterne('SNAPSHOT',None)];m={'IA':MiseAJourBras()}
        e=EntreeMoteur(0,1,receptions=r,mises_a_jour=m);r.clear();m.clear()
        self.assertEqual(len(e.receptions),1);self.assertEqual(len(e.mises_a_jour),1)
        with self.assertRaises(FrozenInstanceError):e.numero=9

    def test_sorties_canoniques_et_vue_par_bras(self):
        s=SortieMoteur([],[]);o=SortieEvenement(1,0,{'REFERENCE':s,'IA':s})
        self.assertEqual(o.enregistrements,());self.assertEqual(o.par_bras['IA'],s)
        with self.assertRaises(TypeError):o.par_bras['x']=s
        for f in (lambda:SortieMoteur([{}],[]),lambda:SortieMoteur([],[],{}),
            lambda:SortieEvenement(1,0,{'AUTRE':s}),lambda:SortieEvenement(1,0,ignoree=1)):
            with self.assertRaises(ErreurOrchestration):f()

    def test_base_native_future_refusee(self):
        b=BaseReconstituee(date(1970,1,1),1,D('100'),D('100'),D('100'))
        with self.assertRaises(ErreurOrchestration):EntreeMoteur(0,1,mises_a_jour={'IA':MiseAJourBras(base_utc=b)})
        self.assertEqual(EntreeMoteur(1,1,mises_a_jour={'IA':MiseAJourBras(base_utc=b)}).instant_ms,1)

    def test_sortie_ignoree_ne_reemet_pas_de_journal(self):
        e=enregistrement(TypeEnregistrement.ALERTE,Enveloppe('d','REFERENCE','REJEU',1,0,empreintes_regles(C)),{'alerte':'x'})
        with self.assertRaises(ErreurOrchestration):SortieEvenement(1,0,{'IA':SortieMoteur([e],[])},True)

    def test_textes_utf8_explicites(self):
        self.assertEqual(texte('déploiement'),'déploiement')
        for v in (None,'','  ','\ud800'):
            with self.assertRaises(ErreurOrchestration):texte(v)

    def test_appels_calcul_immutables_et_options_uniques(self):
        args=[D('1')];a=AppelCalcul('profit',args,(('x',True),),D('-1'));args.clear()
        self.assertEqual(a.arguments,(D('1'),))
        with self.assertRaises(FrozenInstanceError):a.nom='autre'
        for nom,resultat,options in (('inconnue',D(1),()),('marge',D('-1'),()),('profit',D('NaN'),()),
            ('etat_compte',D(1),()),('profit',D(1),(('x',True),('x',False)))):
            with self.assertRaises(ErreurOrchestration):AppelCalcul(nom,(),options,resultat)

    def test_entree_journalisee_separe_les_calculs_par_bras(self):
        a=AppelCalcul('profit',(),(),D(0));e=EntreeMoteur(0,1)
        j=EntreeJournalisee(e,{'REFERENCE':(a,),'IA':()})
        self.assertEqual(dict(j.calculs)['REFERENCE'],(a,));self.assertEqual(j.entree,e)
        for nom,valeur in (('AUTRE',(a,)),('IA',({},)),('IA',[a])):
            with self.assertRaises(ErreurOrchestration):EntreeJournalisee(e,{nom:valeur})
        with self.assertRaises(ErreurOrchestration):EntreeJournalisee({},())
