"""Contrat de collecte : occurrences, préfixes, reprise et trous natifs."""
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import unittest
import numpy as np
from robot.outils.faux_mt5 import FauxMT5,TICK_DTYPE
from robot.outils.qualification_mt5 import T,JOUR,iso
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,SegmentServeur
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2b_flux import FluxMT5


class TestFluxMT5(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk=FauxMT5(Path(self.temp.name).resolve(),instant_ms=T)
        self.session=SessionMT5(self.sdk,'PAPER');self.session.attacher();self.addCleanup(self.session.fermer)
        self.table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(T-1000),('S01_SYNTHETIQUE',),
            (SegmentServeur(T-2*JOUR,T+2*JOUR,0),))
        self.lignes=self.sdk.ticks['EURUSD.micro']

    def flux(self,*,taille=4,maximum=32,preuve=True,etat=None,table=None,convention_ticks='SERVEUR_S01'):
        return FluxMT5(self.session,table or self.table,{'EURUSD':'EURUSD.micro'},{'EURUSD':T},
            taille_lot=taille,max_ticks_lot=maximum,historique_complet={'EURUSD':preuve},etat=etat,
            convention_ticks=convention_ticks)

    def test_occurrences_identiques_a_la_meme_ms_et_aucun_rafraichissement_sans_tick(self):
        self.lignes.extend([(T,1.1,1.1001,6),(T,1.1,1.1001,6),(T+1000,1.1002,1.1003,6)])
        f=self.flux();lot=f.lire(T+2000)
        self.assertEqual([v.numero for v in lot.ticks],[1,2,3])
        self.assertEqual([v.instant_fournisseur_ms for v in lot.ticks],[T,T,T+1000])
        self.assertFalse(lot.erreurs);self.assertEqual(lot.a_jour,(('EURUSD',True),))
        self.assertFalse(f.lire(T+3000).ticks)
        self.lignes.append(self.lignes[-1])
        suivant=f.lire(T+4000)
        self.assertEqual([v.numero for v in suivant.ticks],[4])
        self.assertEqual(suivant.ticks[0].instant_reception_ms,T+4000)

    def test_lot_plein_prefere_ms_complete_et_rattrape_sans_perte(self):
        self.lignes.extend((T+n,1.1+n/100000,1.1001+n/100000,6) for n in range(12))
        f=self.flux(taille=4,maximum=16);sortie=[]
        for _ in range(10):
            lot=f.lire(T+1000);sortie.extend(lot.ticks)
            if dict(lot.a_jour)['EURUSD']:break
            self.assertLess(dict(lot.couvertures)['EURUSD'][-1].fin_ms,T+1000)
        self.assertTrue(dict(lot.a_jour)['EURUSD'])
        self.assertEqual([v.instant_fournisseur_ms for v in sortie],list(range(T,T+12)))
        self.assertEqual([v.numero for v in sortie],list(range(1,13)))

    def test_burst_meme_ms_augmente_compte_et_ne_fait_pas_un_set(self):
        self.lignes.extend([(T,1.1,1.1001,6)]*6+[(T+1,1.2,1.2001,6)])
        f=self.flux(taille=2,maximum=16);lot=f.lire(T+1000)
        self.assertEqual(len(lot.ticks),7)
        self.assertEqual([a[1][2] for a in self.sdk.appels if a[0]=='copy_ticks_from'],[2,4,8])
        for nom,args,kw in self.sdk.appels:
            if nom=='copy_ticks_from':
                self.assertEqual(args[1].utcoffset(),timedelta(0));self.assertEqual(args[1].microsecond,0)
                self.assertEqual(args[-1],self.sdk.COPY_TICKS_ALL)

    def test_burst_hors_plafond_ne_mutera_pas_curseur_ni_couverture(self):
        self.lignes.extend([(T,1.1,1.1001,6)]*9)
        f=self.flux(taille=2,maximum=8);avant=f.exporter_etat();lot=f.lire(T+1000)
        self.assertFalse(lot.ticks);self.assertTrue(lot.erreurs)
        self.assertEqual(f.exporter_etat()['curseurs'],avant['curseurs'])
        self.assertEqual(f.exporter_etat()['numero'],0)

    def test_prefixe_supprime_ou_reecrit_refuse_sans_saut(self):
        self.lignes.extend([(T,1.1,1.1001,6)]*2)
        f=self.flux();f.lire(T);avant=f.exporter_etat()['curseurs']
        self.lignes.pop();lot=f.lire(T+1)
        self.assertTrue(lot.erreurs);self.assertEqual(f.exporter_etat()['curseurs'],avant)
        self.lignes[:]=[(T,1.2,1.2001,6)]*2
        lot=f.lire(T+2);self.assertTrue(lot.erreurs);self.assertFalse(lot.ticks)
        self.assertEqual(f.exporter_etat()['curseurs'],avant)

    def test_none_coupure_reconnexion_rattrape_les_occurrences(self):
        self.lignes.append((T,1.1,1.1001,6));f=self.flux();premier=f.lire(T)
        self.sdk.terminal=self.sdk.terminal._replace(connected=False)
        self.lignes.extend([(T+1,1.1,1.1001,6),(T+1,1.1,1.1001,6)])
        self.assertTrue(f.lire(T+1).erreurs)
        self.sdk.terminal=self.sdk.terminal._replace(connected=True)
        self.sdk.scenarios['copy_ticks_from'].append(None)
        self.assertTrue(f.lire(T+2).erreurs)
        lot=f.lire(T+3)
        self.assertEqual([v.numero for v in premier.ticks+lot.ticks],[1,2,3])
        self.assertEqual([v.instant_fournisseur_ms for v in lot.ticks],[T+1,T+1])
        self.assertFalse(lot.erreurs)

    def test_future_non_fini_ordre_invalide_et_preuve_s08_absente(self):
        f=self.flux()
        for lignes in ([(T+100,1.1,1.1001,6)],[(T,float('nan'),1.1,6)],
                       [(T+1,1.1,1.1001,6),(T,1.1,1.1001,6)],[(T,0.,1.1,6)]):
            self.lignes[:]=lignes;lot=f.lire(T+1)
            self.assertTrue(lot.erreurs);self.assertFalse(lot.ticks);self.assertEqual(f.exporter_etat()['numero'],0)
        self.lignes[:]=[(T,1.1,1.1001,6)]
        self.assertTrue(self.flux(preuve=False).lire(T+1).erreurs)

    def test_silence_ne_produit_pas_de_cotation_ni_de_bougie(self):
        lot=self.flux().lire(T+1000)
        self.assertFalse(lot.ticks);self.assertFalse(lot.erreurs)
        self.assertEqual(dict(lot.couvertures)['EURUSD'][0].fin_ms,T+1000)

    def test_reprise_preserve_prefixe_numero_et_nouvelle_occurrence(self):
        self.lignes.extend([(T,1.1,1.1001,6)]*2)
        f=self.flux();f.lire(T);etat=f.exporter_etat()
        r=self.flux(etat=etat);self.assertEqual(r.exporter_etat(),etat)
        self.lignes.append((T,1.1,1.1001,6))
        self.assertEqual([v.numero for v in r.lire(T+1).ticks],[3])
        for cle,valeur in (('numero',True),('configuration_sha256','x'),('dernier_ms',T-1)):
            mod=deepcopy(etat);mod[cle]=valeur
            with self.assertRaises(ErreurInfra):self.flux(etat=mod)

    def test_table_d12_ne_redecale_pas_les_ticks_sdk_utc(self):
        table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('OFFSET_S01',),
            (SegmentServeur(T-2*JOUR,T+2*JOUR,3600),))
        self.lignes.append((T,1.1,1.1001,6))
        self.assertEqual(self.flux(table=table,convention_ticks='UTC').lire(T).ticks[0].instant_fournisseur_ms,T)
        table=TableHeureServeur('SERVEUR_FIXTURE',3,iso(T-1000),('AMBIGUITE_S01',),
            (SegmentServeur(T-2*JOUR,T,3600),SegmentServeur(T,T+2*JOUR,0)))
        self.lignes[:]=[(T+1000,1.1,1.1001,6)]
        lot=self.flux(table=table,convention_ticks='UTC').lire(T+1000)
        self.assertFalse(lot.erreurs);self.assertEqual(lot.ticks[0].instant_fournisseur_ms,T+1000)

    def test_recherche_et_reprise_utc_avec_offsets_d12_positif_et_negatif(self):
        for offset in (-7200,7200):
            with self.subTest(offset=offset):
                table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('D12_NON_UTC',),
                    (SegmentServeur(T-2*JOUR,T+2*JOUR,offset),))
                self.lignes[:]=[(T,1.1,1.1001,6),(T+1000,1.1002,1.1003,6)]
                f=self.flux(table=table,convention_ticks='UTC');lot=f.lire(T+2000)
                self.assertEqual([q.instant_fournisseur_ms for q in lot.ticks],[T,T+1000])
                recherche=[a[1][1] for a in self.sdk.appels if a[0]=='copy_ticks_from'][-1]
                self.assertEqual(round(recherche.timestamp()*1000),T)
                self.assertEqual(recherche.utcoffset(),timedelta(0))
                r=self.flux(table=table,etat=f.exporter_etat(),convention_ticks='UTC');self.lignes.append(self.lignes[-1])
                suite=r.lire(T+3000)
                self.assertEqual([(q.numero,q.instant_fournisseur_ms) for q in suite.ticks],[(3,T+1000)])

    def test_un_tick_sdk_futur_ne_devient_pas_causal_par_la_table_d12(self):
        table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('D12_PLUS_UNE_HEURE',),
            (SegmentServeur(T-2*JOUR,T+2*JOUR,3600),))
        self.lignes[:]=[(T+1000,1.1,1.1001,6)]
        lot=self.flux(table=table,convention_ticks='UTC').lire(T)
        self.assertTrue(lot.erreurs);self.assertFalse(lot.ticks)

    def test_source_serveur_s01_qualifiee_reste_convertie_et_ambiguite_refusee(self):
        table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('OFFSET_S01',),
            (SegmentServeur(T-2*JOUR,T+2*JOUR,3600),))
        self.lignes[:]=[(T+3600000,1.1,1.1001,6)]
        self.assertEqual(self.flux(table=table).lire(T).ticks[0].instant_fournisseur_ms,T)
        table=TableHeureServeur('SERVEUR_FIXTURE',3,iso(T-1000),('AMBIGUITE_S01',),
            (SegmentServeur(T-2*JOUR,T,3600),SegmentServeur(T,T+2*JOUR,0)))
        self.lignes[:]=[(T+1000,1.1,1.1001,6)]
        lot=self.flux(table=table).lire(T+1000)
        self.assertTrue(lot.erreurs);self.assertFalse(lot.ticks)

    def test_convention_inconnue_refuse_et_reprise_avec_autre_convention_interdite(self):
        for v in ('INCONNUE',None,True):
            with self.subTest(v=v),self.assertRaises(ErreurInfra):self.flux(convention_ticks=v)
        self.lignes[:]=[(T,1.1,1.1001,6)]
        f=self.flux(convention_ticks='UTC');f.lire(T)
        with self.assertRaises(ErreurInfra):self.flux(etat=f.exporter_etat(),convention_ticks='SERVEUR_S01')
