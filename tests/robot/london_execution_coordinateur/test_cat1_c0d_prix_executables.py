"""Catégorie 1, couche 0d (prix_executables) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D,getcontext,localcontext
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0d_prix import *
from xpbots.noyau.c1c_domaine import Sens,Motif

class TestPrix(unittest.TestCase):
    def test_exemple_s02_et_oracle_deux_sens(self):
        from reference.technical import rounded_levels
        for sens in Sens:
            s=signal(sens); q=cotation(); n=construire_niveaux(s,q,profil(),commun())
            r=rounded_levels({'side':sens.signe,'stop_chart_bid':s.stop_technique,'strategy':s.strategie,'atr_reference':s.atr_reference},float(q.bid),float(q.ask),float(profil().tick_size))
            for nom,champ in (('entree','entry'),('stop','stop'),('objectif','target'),('distance','distance')):
                self.assertAlmostEqual(float(getattr(n,nom)),r[champ],places=12)
        n=construire_niveaux(signal(),cotation(),profil(),commun())
        self.assertEqual((n.entree,n.stop,n.distance,n.objectif),(D('1.1004'),D('1.09980'),D('.00060'),D('1.10160')))
    def test_arrondis_asymetriques_sur_pas_non_decimal_simple(self):
        p=profil(tick_size=D('.00005'))
        for sens,raw,want in ((Sens.ACHAT,1.09983,D('1.09980')),(Sens.VENTE,1.10083,D('1.10095'))):
            n=construire_niveaux(signal(sens,stop_technique=raw),cotation(),p,commun())
            self.assertEqual(n.stop,want)
    def test_distances_natives_et_gel_sans_deplacer_stop(self):
        s=signal();q=cotation()
        self.assertIsInstance(construire_niveaux(s,q,profil(distance_stops_min_points=50),commun()),NiveauxExecutables)
        for p in (profil(distance_stops_min_points=51),profil(niveau_gel_points=50)):
            r=construire_niveaux(s,q,p,commun());self.assertEqual((r.motif,r.detail),(Motif.PROTECTION_ERROR,'CONTRAINTE_NATIVE_AVANT_ORDRE'))
    def test_profil_non_pret_et_cotation_non_croisee(self):
        for p in (None,profil(protections_a_l_entree=False),profil(convention_declenchement_verifiee=False)):
            self.assertIs(construire_niveaux(signal(),cotation(),p,commun()).motif,Motif.ENVIRONMENT_NOT_READY)
        q=cotation(ask=D('1.100401'))
        self.assertEqual(construire_niveaux(signal(),q,profil(),commun()).entree,q.ask)
        q=cotation(ask=D('1.099'))
        self.assertIs(construire_niveaux(signal(),q,profil(),commun()).motif,Motif.ENVIRONMENT_NOT_READY)
    def test_stress_c10_ask_fractionnaire_entree_exacte_protections_sur_grille(self):
        q=cotation(bid=D('1.1'),ask=D('1.100125'))
        s=signal(stop_technique=1.0992,cloture_prix=1.1,atr_reference=.001)
        n=construire_niveaux(s,q,profil(tick_size=D('.00001')),commun())
        self.assertEqual((n.entree,n.stop,n.distance,n.objectif),
            (D('1.100125'),D('1.09920'),D('.000925'),D('1.10198')))
    def test_objectif_depuis_fill_reel_sl_fixe_et_depasse(self):
        for sens in Sens:
            n=construire_niveaux(signal(sens),cotation(),profil(),commun())
            prix=n.entree+D('.0001')*sens.signe
            r=recalculer_objectif(n,prix)
            self.assertEqual(r.stop,n.stop)
            self.assertEqual(r.distance,sens.signe*(prix-n.stop))
            q=cotation(bid=r.objectif,ask=r.objectif)
            self.assertTrue(recalculer_objectif(n,prix,q).objectif_depasse)
            q=cotation(bid=r.objectif-D('.00001')*sens.signe,ask=r.objectif-D('.00001')*sens.signe)
            self.assertFalse(recalculer_objectif(n,prix,q).objectif_depasse)
    def test_distance_technique_maximum_et_contexte_global(self):
        s=signal(stop_technique=1.1,cloture_prix=1.1005,atr_reference=.0002)
        self.assertIsInstance(construire_niveaux(s,cotation(bid=D('1.1005'),ask=D('1.1005')),profil(),commun()),NiveauxExecutables)
        self.assertIs(construire_niveaux(replace(s,stop_technique=1.09999),cotation(),profil(),commun()).motif,Motif.STOP_TOO_WIDE)
        before=getcontext().copy(); construire_niveaux(signal(),cotation(),profil(),commun())
        self.assertEqual(getcontext().prec,before.prec)
