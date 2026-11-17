"""Jonction native vers le vrai C03 et le moteur unique, sans terminal."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.qualification_mt5 import T,JOUR,iso
from robot.outils.configuration import configuration_figee
from robot.outils.pilote_orchestration import duo
from xpbots.infra.c0a_types import TableHeureServeur,SegmentServeur
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2b_flux import FluxMT5
from xpbots.noyau.c1b_instrument import HorairesCotation,Intervalle
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.donnees.c0a_types import BougieEnrichie,UniteTemps
from xpbots.execution.c4_cycle import NatureCommande
from xpbots.orchestration.c0_contrats import EntreeMoteur


class TestJonctionFluxNative(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk=FauxMT5(Path(self.temp.name).resolve(),instant_ms=T)
        self.session=SessionMT5(self.sdk,'PAPER');self.session.attacher();self.addCleanup(self.session.fermer)
        self.conf=configuration_figee();self.pas=self.conf.technique.commun.timeframe_seconds*1000
        self.fin=T+4*self.pas
        self.sdk.ticks['EURUSD.micro']=[(T,1.1,1.1001,6),(T,1.1002,1.1003,6)]+[
            (T+n*self.pas,1.1+n*.0001,1.1001+n*.0001,6) for n in range(1,5)]
        table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(T-1000),('S01_SYNTHETIQUE',),
            (SegmentServeur(T-JOUR,T+JOUR,7200),))
        source=FluxMT5(self.session,table,{'EURUSD':'EURUSD.micro'},{'EURUSD':T},
            taille_lot=20,max_ticks_lot=40,historique_complet={'EURUSD':True},convention_ticks='UTC')
        self.lot=source.lire(self.fin)
        self.assertFalse(self.lot.erreurs)

    def test_frontiere_m15_h1_ohlc_bid_et_multiplicites_reelles(self):
        h=HorairesCotation((Intervalle(T,self.fin+self.pas),),(),T,self.fin+self.pas)
        f=FluxBougies('EURUSD',self.conf.technique,h,RegistreCouverture(dict(self.lot.couvertures)['EURUSD']))
        ev=[v for t in self.lot.ticks for v in f.sur_tick(t)]
        enrichies=[v for v in ev if isinstance(v,BougieEnrichie)]
        m15=[v for v in enrichies if v.unite is UniteTemps.M15]
        h1=[v for v in enrichies if v.unite is UniteTemps.H1]
        self.assertEqual(len(m15),4);self.assertEqual(len(h1),1)
        self.assertTrue(all(v.bougie.valide for v in enrichies))
        b=m15[0].bougie
        self.assertEqual((b.ouverture,b.haut,b.bas,b.cloture,b.nombre_evenements),(1.1,1.1002,1.1,1.1002,2))
        a_fin=[v.unite for v in enrichies if v.bougie.fin_ms==self.fin]
        self.assertEqual(a_fin,[UniteTemps.H1,UniteTemps.M15])

    def test_moteur_unique_sans_entree_retroactive_et_rejeu_identique_sans_backend(self):
        ticks=self.lot.ticks;m,ports,_,_,_=duo(ticks);sorties=[]
        for i,tick in enumerate(ticks):
            for p in ports.values():p.sur_tick(tick)
            s=m.traiter(EntreeMoteur(self.fin,i+1,'TICKS',(tick,)));sorties.append(s)
            self.assertFalse(any(c.nature is NatureCommande.ENTREE for _,lot in s.sorties for c in lot.commandes))
        r,ports2,_,_,_=duo(ticks)
        def interdit(*a,**kw):raise AssertionError('backend natif au rejeu')
        for p in ports2.values():
            for nom in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
                setattr(p,nom,interdit)
        for entree,sortie in zip(m.entrees,sorties):self.assertEqual(r.rejouer(entree),sortie)
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
