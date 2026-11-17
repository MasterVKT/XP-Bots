"""Quatre vrais adaptateurs relies au seul faux terminal externe."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
import numpy as np
from robot.outils.qualification_mt5 import T,JOUR,iso,exports,octets,preuve_qualification
from robot.outils.execution_partagee import configuration
from robot.outils.faux_mt5 import FauxMT5,TICK_DTYPE
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,SegmentServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.infra.c2d_execution_mt5 import ExecutionMT5
from xpbots.infra.c3_courtier import CourtierMT5,LotMarcheMT5
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur


class HarnaisCourtier:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.temps=T
        p=patch('time.time_ns',side_effect=lambda:self.temps*1000000);p.start();self.addCleanup(p.stop)
        self.sdk=FauxMT5(Path(self.temp.name).resolve(),instant_ms=T)
        self.session=SessionMT5(self.sdk,'DEMO');self.session.attacher();self.addCleanup(self.session.fermer)
        self.table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(T-1000),('FIXTURE_S01',),(SegmentServeur(T-14*JOUR,T+30*JOUR,0),))
        self.qualification=preuve_qualification(self.sdk)
        self.courtier=self.nouveau();self.addCleanup(lambda:self.courtier.fermer(1000))

    def nouveau(self,etat=None,qualification=None):
        return CourtierMT5(self.session,configuration().commun,self.table,{'EURUSD':'EURUSD.micro'},HorlogeSysteme(),self.temps,
            qualification=self.qualification if qualification is None else qualification,departs_ticks_utc_ms={'EURUSD':T-1000},
            depuis_historique_compte_utc_ms=T//JOUR*JOUR,seances_max_age_ms=7200000,fermetures_max_age_ms=2*JOUR,
            max_jours_horaires=14,ecart_horloges_max_ms=1000,taille_lot=100,max_ticks_lot=10000,
            longueur_empreinte=16,max_taches_natives=4,etat=etat)

    def exports(self):
        s,f=exports()
        return self.courtier.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(f))


class TestCompositionCourtier(HarnaisCourtier,unittest.TestCase):
    def test_parents_reels_et_callbacks_compte_non_rapproche_bloquent(self):
        self.assertIsInstance(self.courtier.specifications,SpecificationsMT5)
        self.assertIsInstance(self.courtier.calculs,CalculsMT5)
        self.assertIsInstance(self.courtier.execution,ExecutionMT5)
        self.exports()
        with self.assertRaises(ErreurInfra):self.courtier.calculs.etat_compte()
        r=self.courtier.observer();self.assertIsNotNone(r.observation,r.alertes)
        self.assertFalse(self.courtier.calculs.etat_compte().flux_externe_non_neutralise)

    def test_reception_ticks_datee_apres_le_retour_sans_etendre_couverture(self):
        def retour(*args):
            self.temps=T+25
            return np.array([(T//1000,1.1003,1.1004,0.,0,T,self.sdk.TICK_FLAG_BID|self.sdk.TICK_FLAG_ASK,0.)],dtype=TICK_DTYPE)
        self.sdk.scenarios['copy_ticks_from'].append(retour)
        lot=self.courtier.lire_marche()
        self.assertEqual(lot.instant_ms,T+25)
        self.assertEqual((lot.ticks[0].instant_fournisseur_ms,lot.ticks[0].instant_reception_ms),(T,T+25))
        self.assertTrue(all(i.fin_ms<=T for s,intervalles in lot.couvertures for i in intervalles))

    def test_reprise_des_curseurs_et_exports_sans_doublon_ni_nouvelle_fraicheur(self):
        self.exports();self.sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
        premier=self.courtier.lire_marche();self.assertEqual(len(premier.ticks),1)
        etat=deserialiser_valeur(serialiser_valeur(self.courtier.exporter_etat()))
        self.temps=T+100
        reprise=self.nouveau(etat);self.addCleanup(lambda:reprise.fermer(1000))
        self.assertEqual(reprise.lire_marche().ticks,())
        self.assertEqual(reprise.exporter_etat()['specifications']['exports'],etat['specifications']['exports'])
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_preuve_s08_expiree_ne_lit_pas_et_ne_rend_pas_un_lot_pret(self):
        self.temps=self.qualification['valid_until_utc_ms']
        self.courtier.actualiser_instant(self.temps)
        n=len(self.sdk.appels);lot=self.courtier.lire_marche()
        self.assertEqual(lot.ticks,());self.assertEqual(lot.couvertures,())
        self.assertEqual(lot.a_jour,(('EURUSD',False),));self.assertTrue(lot.erreurs)
        self.assertFalse(any(a[0]=='copy_ticks_from' for a in self.sdk.appels[n:]))

    def test_etats_partiels_futurs_et_horloge_en_recul_refusent(self):
        e=self.courtier.exporter_etat()
        for erreur in ({},dict(e,schema='autre'),dict(e,dernier_ms=T+1),dict(e,flux=None)):
            with self.assertRaises(ErreurInfra):self.nouveau(erreur)
        erreur=deepcopy(e);erreur['execution']['dernier_ms']=T+1
        with self.assertRaises(ErreurInfra):self.nouveau(erreur)
        with self.assertRaises(ErreurInfra):self.courtier.actualiser_instant(T-1)

    def test_fermeture_ne_possede_pas_la_session(self):
        self.assertTrue(self.courtier.fermer(0));self.assertTrue(self.sdk.attache)
        self.assertEqual(LotMarcheMT5(T).ticks,())
        with self.assertRaises(ErreurInfra):LotMarcheMT5(T,a_jour=(('EURUSD',1),))
