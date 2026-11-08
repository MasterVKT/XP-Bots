"""Catégorie 1, sorties C08 et bornes exactes de L-14."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.cycle_execution import bloc_cycle, remplissage
from robot.outils.execution_partagee import configuration, profil, signal
from robot.doublures.permissions_execution import PermissionSynthetique
from xpbots.execution.c1b_gardes import GardesCompte
from xpbots.execution.c5a_sorties import evaluer_sorties
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import CauseCloture, DecisionFondamentale, Motif


def ouvert(t=None, **kwargs):
    s=signal() if t is None else signal(cloture_ms=t)
    t=s.cloture_ms
    h=HorairesCotation((Intervalle(t-86400000,t+86400000),),(),t-86400000,t+172800000)
    b=bloc_cycle(signal_=s,profil_=profil(horaires=h,releve_ms=t),**kwargs)
    b.cycle.preparer_envoi(t)
    e=b.cycle.sur_reponse(remplissage(b))
    for i in e.issues: b.registre.sur_issue(i)
    return b


def evaluer(b, t, *, fondamental=None, technique=None, profils=None, gardes=None):
    return evaluer_sorties((b.cycle,), technique or configuration(), profils or {b.signal.symbole:b.profil},
        gardes or b.garde, fondamental or PermissionSynthetique(), t)


class TestSortiesObligatoires(unittest.TestCase):
    def test_duree_mesuree_depuis_premier_fill_et_borne_exacte(self):
        b=ouvert(); fin=b.signal.cloture_ms+1+7200000
        self.assertFalse(evaluer(b,fin-1).demandes)
        self.assertEqual(evaluer(b,fin-1).prochaine_echeance_ms,fin)
        self.assertEqual(evaluer(b,fin).demandes[0].cause,CauseCloture.DUREE_MAXIMALE)
        self.assertFalse(b.cycle.etat.cause_sortie)

    def test_sortie_locale_ete_hiver_et_egalite_avec_duree(self):
        technique=configuration(); heure=technique.london['force_exit_local']
        for jour, decalage in (('2026-01-12',0),('2026-07-01',1)):
            t=instant_depuis_iso(jour+'T10:30:00.000Z')
            b=ouvert(t)
            hh,mm,ss=(int(x) for x in heure.split(':'))
            attendu=instant_depuis_iso(f'{jour}T{hh-decalage:02}:{mm:02}:{ss:02}.000Z')
            self.assertFalse(evaluer(b,attendu-1).demandes)
            self.assertEqual(evaluer(b,attendu).demandes[0].cause,CauseCloture.HEURE_SORTIE)
        b=ouvert(); fin=b.signal.cloture_ms+1+7200000
        technique=replace(configuration(),london={**configuration().london,'force_exit_local':'10:15:00.001'})
        self.assertEqual(evaluer(b,fin,technique=technique).demandes[0].cause,CauseCloture.HEURE_SORTIE)

    def test_fermeture_native_et_parametres_charges(self):
        b=ouvert(); t=b.signal.cloture_ms
        h=HorairesCotation((Intervalle(t-1000,t+120000),),(),t-1000,t+240000)
        p=replace(b.profil,horaires=h)
        self.assertFalse(evaluer(b,t+59999,profils={'EURUSD':p}).demandes)
        self.assertEqual(evaluer(b,t+60000,profils={'EURUSD':p}).demandes[0].cause,CauseCloture.FERMETURE_NATIVE)
        conf=replace(configuration(),commun=replace(b.params,max_position_wallclock_seconds=3))
        self.assertFalse(evaluer(b,t+3000,technique=conf).demandes)
        self.assertEqual(evaluer(b,t+3001,technique=conf).demandes[0].cause,CauseCloture.DUREE_MAXIMALE)

    def test_gardes_priment_sur_flatten_annonce_et_horaires(self):
        b=ouvert(); t=b.signal.cloture_ms+8000000
        f=PermissionSynthetique(DecisionFondamentale(False,Motif.FUNDAMENTAL_DIRECTION,'RISK_STATE_FLATTEN',True),('EURUSD',))
        for global_,attendu in ((False,CauseCloture.GARDE_QUOTIDIENNE),(True,CauseCloture.ARRET_GLOBAL)):
            g=GardesCompte(b.params,replace(b.garde.etat,verrou_quotidien=True,arret_global=global_))
            self.assertEqual(evaluer(b,t,fondamental=f,gardes=g).demandes[0].cause,attendu)

    def test_flatten_et_annonce_seules_decisions_fondamentales_liquidantes(self):
        b=ouvert(); t=b.signal.cloture_ms+2
        for motif,detail,cause in ((Motif.FUNDAMENTAL_DIRECTION,'RISK_STATE_FLATTEN',CauseCloture.FLATTEN),
                                   (Motif.NEWS_WINDOW,'ANNONCE_HIGH',CauseCloture.ANNONCE)):
            f=PermissionSynthetique(DecisionFondamentale(False,motif,detail,True),('EURUSD',))
            self.assertEqual(evaluer(b,t,fondamental=f).demandes[0].cause,cause)
        for motif,detail in ((Motif.FUNDAMENTAL_INVALID,'PERIMEE'),(Motif.FUNDAMENTAL_DIRECTION,'RISK_STATE_NO_NEW'),
                             (Motif.NEWS_WINDOW,'CALENDRIER_PERIME')):
            f=PermissionSynthetique(DecisionFondamentale(False,motif,detail))
            self.assertFalse(evaluer(b,t,fondamental=f).demandes)

    def test_panne_c05_ne_masque_pas_la_sortie_et_profil_absent_est_conservateur(self):
        b=ouvert(); t=b.signal.cloture_ms
        f=PermissionSynthetique(); f.indisponible=True
        e=evaluer(b,t+7200001,fondamental=f)
        self.assertEqual(e.refus.motif,Motif.ENVIRONMENT_NOT_READY)
        self.assertEqual(e.demandes[0].cause,CauseCloture.DUREE_MAXIMALE)
        e=evaluer_sorties((b.cycle,),configuration(),{},b.garde,f,t+2)
        self.assertEqual(e.demandes[0].cause,CauseCloture.PROTECTION)

    def test_trames_mal_formees_et_cycle_futur_refuses(self):
        b=ouvert(); t=b.signal.cloture_ms
        for cycles,instant in (((b.cycle,b.cycle),t+2),((b.cycle,),t)):
            with self.assertRaises(ValueError):
                evaluer_sorties(cycles,configuration(),{'EURUSD':b.profil},b.garde,PermissionSynthetique(),instant)
