"""Catégorie 1 : propriété, risque restauré et preuves positives C08."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.cycle_execution import bloc_cycle, remplissage
from xpbots.execution.c0a_types import EtatReservations, EtatIntention
from xpbots.execution.c4_cycle import identifier_courtier, NatureCommande, PreuveAbsence
from xpbots.execution.c5b_reprise import (CyclePersiste, EtatReprise, PositionNative, OrdreNatif,
    ObservationNative, restaurer, rapprocher)
from xpbots.noyau.c1c_domaine import Motif, NatureIssue, CauseCloture


def sauvegarde(b):
    return EtatReprise((CyclePersiste(b.signal,b.plan,b.profil,b.cycle.etat),),b.registre.etat,b.garde.etat)


def observation(b, t, *, positions=(), ordres=(), reponses=(), absences=(), **kw):
    return ObservationNative(replace(b.compte,instant_ms=t),b.signal.cloture_ms,True,
        tuple(positions),tuple(ordres),tuple(reponses),tuple(absences),**kw)


def native(b, **kw):
    identite=identifier_courtier(b.plan.reservation.cle,16)
    return replace(PositionNative('position-1',b.profil.symbole_courtier,b.plan.volume,
        identite.magic,identite.commentaire,sl=b.plan.niveaux.stop,tp=b.plan.niveaux.objectif),**kw)


class TestRepriseRapprochement(unittest.TestCase):
    def test_sl_supprime_depuis_journal_declenche_securite_pour_position_possedee_seulement(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        e=b.cycle.sur_reponse(remplissage(b))
        for i in e.issues: b.registre.sur_issue(i)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,positions=(native(b,sl=None),)))
        self.assertEqual(r.etat.cycles[0].etat.cause_sortie,CauseCloture.PROTECTION)
        self.assertTrue(any(c.nature is NatureCommande.CLOTURE for c in r.commandes))
        self.assertFalse(r.issues)
        self.assertEqual(r.etat.reservations.reservations[0].risque_initial,b.plan.risque)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,positions=(native(b,sl=None,magic=0),)))
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in r.commandes))

    def test_ordre_cloture_distinct_ne_remplace_pas_le_ticket_entree(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        e=b.cycle.sur_reponse(remplissage(b))
        for i in e.issues: b.registre.sur_issue(i)
        identite=identifier_courtier(b.plan.reservation.cle,16)
        ordre=OrdreNatif('ordre-sortie',b.profil.symbole_courtier,b.plan.volume,
            identite.magic,identite.commentaire,NatureCommande.CLOTURE)
        avant=sauvegarde(b)
        r=rapprocher(b.params,avant,16,observation(b,t+2,positions=(native(b),),ordres=(ordre,)))
        self.assertFalse(r.prete)
        b.cycle.demander_cloture(t+2,CauseCloture.DUREE_MAXIMALE,peut_envoyer=True)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+3,positions=(native(b),),ordres=(ordre,)))
        self.assertTrue(r.prete); self.assertIsNone(r.refus)
        self.assertEqual(r.etat.cycles[0].etat.ticket_ordre,'ordre-1')
        self.assertEqual(r.etat.reservations.reservations[0].risque_initial,b.plan.risque)
        self.assertIn('EURUSD',r.etat.reservations.verrous)

    def test_redemarrage_apres_envoi_ne_renvoie_pas_et_conserve_risque_et_gardes(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        etat=sauvegarde(b); r=restaurer(b.params,etat,16,t+7000)
        self.assertFalse(r.prete)
        self.assertEqual([c.nature for c in r.commandes],[NatureCommande.RAPPROCHEMENT,NatureCommande.MINUTERIE])
        self.assertEqual(r.etat.reservations.reservations,etat.reservations.reservations)
        self.assertEqual(r.etat.gardes,etat.gardes)
        self.assertIn('EURUSD',r.etat.reservations.verrous)

    def test_risque_absent_ou_reservation_orpheline_interdit_la_reprise(self):
        b=bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
        etat=sauvegarde(b)
        for mauvais in (replace(etat,reservations=EtatReservations()),replace(etat,cycles=())):
            with self.assertRaises(ValueError): restaurer(b.params,mauvais,16,b.signal.cloture_ms+1)

    def test_historique_vide_ne_libere_rien_puis_absence_positive_termine(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        r=restaurer(b.params,sauvegarde(b),16,t+6000)
        o=observation(b,t+7000)
        r=rapprocher(b.params,r.etat,16,o)
        self.assertFalse(r.prete); self.assertEqual(len(r.etat.reservations.reservations),1)
        preuve=PreuveAbsence(b.plan.reservation.cle,t+8000,t,t+8000,True,True,True,True,True,True)
        r=rapprocher(b.params,r.etat,16,observation(b,t+8000,absences=(preuve,)))
        self.assertTrue(r.prete); self.assertFalse(r.etat.reservations.reservations)
        self.assertFalse(r.etat.reservations.verrous)
        self.assertEqual([i.nature for i in r.issues],[NatureIssue.REFUSEE])

    def test_fill_natif_retarde_retablit_quota_risque_et_premier_instant(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        r=restaurer(b.params,sauvegarde(b),16,t+6000)
        o=observation(b,t+7000,positions=(native(b),),reponses=(remplissage(b),))
        r=rapprocher(b.params,r.etat,16,o)
        self.assertTrue(r.prete); self.assertIsNone(r.refus)
        self.assertEqual(r.compte.positions[0].cle,b.plan.reservation.cle)
        self.assertEqual(r.etat.cycles[0].etat.premier_fill_ms,t+1)
        self.assertTrue(r.etat.reservations.reservations[0].remplie)
        self.assertEqual(r.etat.reservations.reservations[0].risque_initial,b.plan.risque)
        self.assertFalse(r.etat.reservations.verrous)
        r2=rapprocher(b.params,r.etat,16,replace(o,compte=replace(o.compte,instant_ms=t+8000)))
        self.assertFalse(r2.issues)

    def test_magic_seul_commentaire_tronque_et_position_non_journalisee_restent_externes(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        for n in (native(b,commentaire='XPB3:'),native(b,magic=0),native(b,ticket='etrangere')):
            r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,positions=(n,),reponses=(remplissage(b),)))
            self.assertIsNone(r.compte.positions[0].cle)
            self.assertEqual(r.refus.motif,Motif.ACCOUNT_RISK_CAP)
            self.assertFalse(any(c.nature in (NatureCommande.CLOTURE,NatureCommande.ANNULATION) for c in r.commandes))
        vide=EtatReprise(gardes=b.garde.etat)
        r=rapprocher(b.params,vide,16,observation(b,t+2,positions=(native(b),)))
        self.assertIsNone(r.compte.positions[0].cle)

    def test_netting_exige_verrou_et_origine_exclusive(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        for exclusivites,origine,admis in (((),True,False),(('EURUSD',),False,False),(('EURUSD',),True,True)):
            o=observation(b,t+2,positions=(native(b,origine_exclusive=origine),),reponses=(remplissage(b),),exclusivites=exclusivites)
            r=rapprocher(b.params,sauvegarde(b),16,o,netting=True)
            self.assertEqual(r.prete,admis)
            self.assertEqual(r.compte.positions[0].cle is not None,admis)

    def test_ordre_identifie_conserve_le_risque_et_le_verrou_ordre_externe_bloque(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        n=native(b)
        ordre=OrdreNatif('ordre-1',n.symbole_courtier,n.volume,n.magic,n.commentaire)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,ordres=(ordre,)))
        self.assertTrue(r.prete); self.assertEqual(len(r.etat.reservations.reservations),1)
        self.assertEqual(r.etat.cycles[0].etat.ticket_ordre,'ordre-1')
        self.assertIn('EURUSD',r.etat.reservations.verrous)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,ordres=(replace(ordre,magic=0),)))
        self.assertFalse(r.prete); self.assertEqual(r.refus.detail,'ordre_externe')
        self.assertFalse(any(c.nature is NatureCommande.ANNULATION for c in r.commandes))

    def test_arret_global_n_est_pas_reinitialise_par_une_equite_retablie(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        etat=EtatReprise(gardes=replace(b.garde.etat,arret_global=True))
        r=rapprocher(b.params,etat,16,observation(b,t+2))
        self.assertTrue(r.etat.gardes.arret_global)
        self.assertEqual(r.refus.motif,Motif.GLOBAL_DRAWDOWN_HALT)

    def test_historique_contradictoire_et_donnees_futures_sont_refuses(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        e=b.cycle.sur_reponse(remplissage(b))
        for i in e.issues: b.registre.sur_issue(i)
        r=remplissage(b,prix_moyen=b.plan.niveaux.entree+D('.00001'))
        with self.assertRaises(ValueError): rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,reponses=(r,)))
        with self.assertRaises(ValueError): observation(b,t,reponses=(remplissage(b),))
        with self.assertRaises(ValueError): observation(b,t+2,positions=(native(b),native(b)))

    def test_absence_contradictoire_avec_position_ne_libere_pas_de_reserve(self):
        b=bloc_cycle(); t=b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        preuve=PreuveAbsence(b.plan.reservation.cle,t+2,t,t+2,True,True,True,True,True,True)
        r=rapprocher(b.params,sauvegarde(b),16,observation(b,t+2,positions=(native(b),),absences=(preuve,)))
        self.assertFalse(r.prete); self.assertEqual(len(r.etat.reservations.reservations),1)
