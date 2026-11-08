"""Catégorie 1 : compte unique, P-08, persistance et relecture avant envoi."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.coordinateur_execution import (bloc_coordinateur,traiter,confirmer,bloc_remplissage,positionner)
from robot.outils.execution_partagee import T,signal,cotation
from robot.outils.cycle_execution import remplissage
from robot.doublures.permissions_execution import PermissionSynthetique
from xpbots.execution.c0a_types import EtatIntention,adapter_signal_ema
from xpbots.execution.c4_cycle import NatureCommande,NatureReponse,ReponseCourtier,StatutAccuse,PreuvePersistance,identifier_courtier
from xpbots.execution.c5b_reprise import ObservationNative,PositionNative
from xpbots.noyau.c1b_instrument import HorairesCotation,Intervalle
from xpbots.noyau.c1c_domaine import DecisionFondamentale,DecisionContexteIA,ContexteIA,Motif,NatureIssue
from xpbots.noyau.decisions import Signal as SignalEMA,Sens as SensEMA


class ContexteSynthetique:
    def __init__(self): self.decision=DecisionContexteIA(ContexteIA.NEUTRAL); self.indisponible=False
    def evaluer(self,symbole,instant_ms):
        if self.indisponible: raise OSError('indisponible')
        return self.decision


class TestCoordinateurCompte(unittest.TestCase):
    def test_sl_supprime_sur_eurusd_bloque_nouvelle_entree_gbpusd_jusqu_a_securisation(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        v=bloc_remplissage(b,lot); confirmer(b,lot)
        positionner(b,v,T+1); traiter(b,T+1,reponses=(remplissage(v),))
        identite=identifier_courtier(v.plan.reservation.cle,16)
        n=PositionNative('position-1',v.profil.symbole_courtier,v.plan.volume,identite.magic,identite.commentaire,
            sl=None,tp=v.plan.niveaux.objectif)
        o=ObservationNative(replace(b.port.compte,instant_ms=T+2,positions=()),T,True,(n,))
        q=replace(cotation(symbole='GBPUSD'),instant_fournisseur_ms=T+2,instant_reception_ms=T+2)
        lot=traiter(b,T+2,observation=o,signaux=(signal(symbole='GBPUSD'),),cotations=(q,))
        self.assertFalse(lot.preparations)
        self.assertEqual((lot.issues[0].motif,lot.issues[0].detail),(Motif.PROTECTION_ERROR,'SL_ABSENT'))
        self.assertTrue(any(c.nature is NatureCommande.CLOTURE for c in lot.commandes))
        self.assertEqual(lot.etat.reprise.reservations.reservations[0].risque_initial,v.plan.risque)

    def test_timeout_accuse_mesure_depuis_transmission_apres_persistance(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        envoi=confirmer(b,lot,T+1000)
        self.assertEqual(envoi.etat.reprise.cycles[0].etat.envoi_ms,T+1000)
        self.assertEqual(b.coordinateur.prochaine_echeance_ms,T+6000)
        self.assertEqual(envoi.compte.instant_ms,T+1000)
        self.assertEqual(envoi.etat.intentions[0].tentatives[-1].instant_ms,T+1000)
        self.assertEqual(traiter(b,T+5000).etat.reprise.cycles[0].etat.statut,EtatIntention.ENVOYEE)
        self.assertEqual(traiter(b,T+6000).etat.reprise.cycles[0].etat.statut,EtatIntention.INCONNUE)

    def test_horaires_natifs_fermes_ou_sortie_deja_due_refusent_avant_reservation(self):
        for fin,instant,detail in ((T,T,'horaires'),(T+30000,T,'echeance_sortie_atteinte')):
            b=bloc_coordinateur()
            h=HorairesCotation((Intervalle(T-86400000,fin),),(),T-86400000,T+86400000)
            b.port.profils['EURUSD']=replace(b.profils['EURUSD'],horaires=h)
            lot=traiter(b,instant,signaux=(signal(),),cotations=(cotation(),))
            self.assertEqual(lot.issues[0].detail,detail)
            self.assertFalse(lot.etat.reprise.reservations.reservations)

    def test_mode_remplissage_inconnu_et_mode_change_avant_envoi_sont_non_prets(self):
        b=bloc_coordinateur(); b.port.profils['EURUSD']=replace(b.profils['EURUSD'],modes_remplissage=frozenset({'INCONNU'}))
        lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        self.assertEqual(lot.issues[0].detail,'mode_remplissage')
        self.assertFalse(lot.etat.reprise.reservations.reservations)
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        b.port.profils['EURUSD']=replace(b.profils['EURUSD'],modes_remplissage=frozenset({'FOK'}))
        fin=confirmer(b,lot)
        self.assertEqual(fin.issues[0].detail,'specifications_modifiees')
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in fin.commandes))

    def test_accuse_natif_deja_accepte_retire_preparation_sans_deuxieme_envoi(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        c=lot.preparations[0]
        ack=ReponseCourtier(NatureReponse.ACCUSE,c.cle,'ack-connu',T+1,
            dict(commande=c.reference,statut=StatutAccuse.ACCEPTE,code_natif='native',definitif=False,ordre='ordre-1'))
        fin=traiter(b,T+1,reponses=(ack,))
        self.assertFalse(fin.preparations); self.assertFalse(fin.issues)
        preuve=PreuvePersistance(lot.etat.revision,(c.reference,))
        self.assertFalse(b.coordinateur.confirmer_persistance(preuve,T+1).commandes)

    def test_observation_positive_retire_toute_preparation_deja_executee(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        v=bloc_remplissage(b,lot); positionner(b,v,T+1)
        identite=identifier_courtier(v.plan.reservation.cle,16)
        native=PositionNative('position-1',v.profil.symbole_courtier,v.plan.volume,identite.magic,identite.commentaire,
            sl=v.plan.niveaux.stop,tp=v.plan.niveaux.objectif)
        o=ObservationNative(replace(b.port.compte,positions=()),T,True,(native,),reponses=(remplissage(v),))
        lot=traiter(b,T+1,observation=o)
        self.assertFalse(lot.preparations)
        self.assertEqual([i.nature for i in lot.issues],[NatureIssue.REMPLIE])
        self.assertEqual(lot.etat.intentions[0].statut,EtatIntention.OUVERTE)

    def test_profil_compte_incomplet_ou_futur_est_non_pret(self):
        modele=bloc_coordinateur().profil_compte
        for pc in (replace(modele,mode_marge=None),replace(modele,releve_ms=T+1)):
            b=bloc_coordinateur(profil_compte=pc)
            lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
            self.assertEqual(lot.issues[0].detail,'qualification_compte')
            self.assertFalse(lot.preparations)

    def test_observation_courante_remplace_une_erreur_de_compte_ancienne(self):
        b=bloc_coordinateur(); b.coordinateur.traiter(T+1)
        b.port.compte=replace(b.port.compte,instant_ms=T+2)
        o=ObservationNative(b.port.compte,T,True)
        q=replace(cotation(),instant_fournisseur_ms=T+2,instant_reception_ms=T+2)
        lot=traiter(b,T+2,signaux=(signal(),),cotations=(q,),observation=o)
        self.assertTrue(lot.preparations)

    def test_panne_liste_c05_a_la_relecture_finale_interdit_transmission(self):
        class Fondamental(PermissionSynthetique):
            panne_liste=False
            def clotures_obligatoires(self,t):
                if self.panne_liste: raise OSError('liste indisponible')
                return super().clotures_obligatoires(t)
        f=Fondamental(); b=bloc_coordinateur(fondamental=f)
        lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        f.panne_liste=True; fin=confirmer(b,lot)
        self.assertEqual(fin.issues[0].detail,'controle_fondamental')
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in fin.commandes))

    def test_entree_conditionnee_par_persistance_puis_transmise_une_seule_fois(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),signal()),cotations=(cotation(),))
        self.assertEqual(len(lot.preparations),1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
        self.assertEqual(len(lot.etat.reprise.reservations.reservations),1)
        self.assertFalse(lot.issues)
        with self.assertRaises(ValueError): b.coordinateur.confirmer_persistance(None,T)
        preuve=PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations))
        envoi=b.coordinateur.confirmer_persistance(preuve,T)
        self.assertEqual([c.nature for c in envoi.commandes],[NatureCommande.ENTREE])
        self.assertFalse(envoi.preparations)
        self.assertFalse(b.coordinateur.confirmer_persistance(preuve,T).commandes)
        self.assertGreaterEqual(sum(a[0]=='specifications' for a in b.port.appels),2)

    def test_preuve_incomplete_etrangere_ou_perimee_n_autorise_rien(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        avant=b.coordinateur.etat
        for preuve in (PreuvePersistance(lot.etat.revision,()),PreuvePersistance(lot.etat.revision,('etrangere',)),
                       PreuvePersistance(lot.etat.revision+1,tuple(c.reference for c in lot.preparations))):
            with self.assertRaises(ValueError): b.coordinateur.confirmer_persistance(preuve,T)
            self.assertEqual(b.coordinateur.etat,avant)

    def test_seul_premier_fill_natif_consomme_quota_accuse_seul_n_a_pas_d_issue(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        v=bloc_remplissage(b,lot); envoi=confirmer(b,lot)
        entree=envoi.commandes[0]
        ack=ReponseCourtier(NatureReponse.ACCUSE,entree.cle,'ack',T+1,
            dict(commande=entree.reference,statut=StatutAccuse.ACCEPTE,code_natif='synthetique',definitif=False,ordre='ordre-1'))
        self.assertFalse(traiter(b,T+1,reponses=(ack,)).issues)
        positionner(b,v,T+2)
        r=remplissage(v,instant_ms=T+2)
        lot=traiter(b,T+2,reponses=(r,))
        self.assertEqual([i.nature for i in lot.issues],[NatureIssue.REMPLIE])
        self.assertTrue(lot.etat.reprise.reservations.reservations[0].remplie)
        self.assertFalse(traiter(b,T+3,reponses=(replace(r,reference='autre-reception'),)).issues)
        self.assertEqual(len(b.coordinateur.etat.intentions),1)

    def test_l18_spread_s_ameliore_avant_ttl_ou_expire_exactement(self):
        mauvais=cotation(ask=D('1.1006'))
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(mauvais,))
        self.assertFalse(lot.preparations)
        self.assertEqual(lot.etat.intentions[0].derniere_cause,'SPREAD_CAP')
        q=replace(cotation(),instant_fournisseur_ms=T+4999,instant_reception_ms=T+4999)
        lot=traiter(b,T+4999,cotations=(q,))
        self.assertEqual(len(lot.preparations),1)
        self.assertEqual(len(lot.etat.intentions[0].tentatives),2)
        self.assertEqual([c.nature for c in confirmer(b,lot,T+4999).commandes],[NatureCommande.ENTREE])
        b=bloc_coordinateur(); traiter(b,signaux=(signal(),),cotations=(mauvais,))
        lot=traiter(b,T+5000,cotations=(replace(cotation(),instant_fournisseur_ms=T+5000,instant_reception_ms=T+5000),))
        self.assertFalse(lot.preparations)
        self.assertEqual((lot.issues[0].motif,lot.issues[0].detail),(Motif.SIGNAL_EXPIRED,'SPREAD_CAP'))
        self.assertFalse(lot.etat.reprise.reservations.reservations)

    def test_l19_ecart_borne_incluse_et_juste_au_dessus_attend_puis_expire(self):
        s=signal(atr_reference=.0004)
        b=bloc_coordinateur(); q=cotation(bid=D('1.1004'),ask=D('1.1005'))
        self.assertEqual(len(traiter(b,signaux=(s,),cotations=(q,)).preparations),1)
        b=bloc_coordinateur(); q=replace(q,bid=q.bid+D('.000000001'),ask=q.ask+D('.000000001'))
        lot=traiter(b,signaux=(s,),cotations=(q,))
        self.assertFalse(lot.preparations)
        self.assertEqual(lot.etat.intentions[0].derniere_cause,'ENTRY_GAP')
        lot=traiter(b,T+5000)
        self.assertEqual((lot.issues[0].motif,lot.issues[0].detail),(Motif.SIGNAL_EXPIRED,'ENTRY_GAP'))

    def test_c05_recontrole_apres_preparation_sans_transmission_ni_quota(self):
        f=PermissionSynthetique(); b=bloc_coordinateur(fondamental=f)
        lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        f.decision=DecisionFondamentale(False,Motif.FUNDAMENTAL_DIRECTION,'RISK_STATE_NO_NEW')
        fin=confirmer(b,lot)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in fin.commandes))
        self.assertEqual(fin.issues[0].motif,Motif.FUNDAMENTAL_DIRECTION)
        self.assertFalse(fin.etat.reprise.reservations.reservations)

    def test_ia_memoire_recontrolee_et_panne_neutre_sans_lever_veto_du_socle(self):
        ia=ContexteSynthetique(); b=bloc_coordinateur(contexte=ia)
        lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        ia.decision=DecisionContexteIA(ContexteIA.BLOCK,'preuve_synthetique')
        fin=confirmer(b,lot)
        self.assertEqual(fin.issues[0].motif,Motif.AI_CONTEXT_VETO)
        self.assertFalse(fin.commandes)
        ia.indisponible=True; b=bloc_coordinateur(contexte=ia)
        self.assertTrue(traiter(b,signaux=(signal(),),cotations=(cotation(),)).preparations)
        f=PermissionSynthetique(DecisionFondamentale(False,Motif.NEWS_WINDOW,'CALENDRIER_PERIME'))
        b=bloc_coordinateur(contexte=ia,fondamental=f)
        self.assertEqual(traiter(b,signaux=(signal(),),cotations=(cotation(),)).issues[0].motif,Motif.NEWS_WINDOW)

    def test_fondamental_absent_ou_indisponible_ne_devient_pas_neutre(self):
        for f in (None,PermissionSynthetique()):
            if f is not None: f.indisponible=True
            b=bloc_coordinateur(fondamental=f)
            lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
            self.assertFalse(lot.preparations)
            self.assertEqual(lot.issues[0].motif,Motif.FUNDAMENTAL_INVALID)

    def test_l17_priorite_london_puis_univers_et_rerelecture_des_reserves(self):
        b=bloc_coordinateur()
        ema=adapter_signal_ema(SignalEMA('EMA_V3','EURUSD',T,SensEMA.ACHAT,D('1.1003'),.0005,1.0998,1.5))
        lot=traiter(b,signaux=(ema,signal(symbole='GBPUSD'),signal()),cotations=(cotation(),cotation(symbole='GBPUSD')))
        self.assertEqual([(c.cle.strategie,c.cle.symbole) for c in lot.preparations],[('LONDON_V3','EURUSD'),('LONDON_V3','GBPUSD')])
        self.assertEqual(lot.issues[0].motif,Motif.SYMBOL_BUSY)
        self.assertEqual(len(lot.etat.reprise.reservations.reservations),2)

    def test_qualification_compte_et_exclusivite_netting_obligatoires(self):
        modele=bloc_coordinateur().profil_compte
        b=bloc_coordinateur(profil_compte=replace(modele,levier=200))
        self.assertEqual(traiter(b,signaux=(signal(),),cotations=(cotation(),)).issues[0].detail,'qualification_compte')
        b=bloc_coordinateur(profil_compte=replace(modele,mode_marge='NETTING'))
        self.assertEqual(traiter(b,signaux=(signal(),),cotations=(cotation(),)).issues[0].detail,'VERROU_PROPRIETE')
        b=bloc_coordinateur(profil_compte=replace(modele,mode_marge='NETTING'),exclusivites=('EURUSD',))
        self.assertTrue(traiter(b,signaux=(signal(),),cotations=(cotation(),)).preparations)

    def test_scenario_technique_est_explicitement_interdit_en_demo_et_reel(self):
        for mode in ('DEMO','REEL'):
            b=bloc_coordinateur(mode=mode)
            self.assertEqual(traiter(b,signaux=(signal(),),cotations=(cotation(),)).issues[0].detail,'scenario_technique_interdit')

    def test_preparation_non_transmise_expire_sans_attendre_un_accuse(self):
        b=bloc_coordinateur(); traiter(b,signaux=(signal(),),cotations=(cotation(),))
        lot=traiter(b,T+5000)
        self.assertEqual(lot.issues[0].nature,NatureIssue.EXPIREE)
        self.assertFalse(lot.preparations)
        self.assertFalse(lot.etat.reprise.reservations.reservations)

    def test_reprise_apres_envoi_ne_retransmet_pas_la_preparation(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        reprise=bloc_coordinateur(t=T+1,etat=lot.etat,observation=None)
        lot2=traiter(reprise,T+1)
        self.assertFalse(lot2.preparations)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot2.commandes))
        self.assertIn('EURUSD',lot2.etat.reprise.reservations.verrous)
        with self.assertRaises(ValueError):
            reprise.coordinateur.confirmer_persistance(PreuvePersistance(lot.etat.revision,tuple(c.reference for c in lot.preparations)),T+1)

    def test_compte_et_frais_revalides_sur_le_volume_exact_avant_envoi(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),))
        b.port.autres_frais=D('.5')
        fin=confirmer(b,lot)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in fin.commandes))
        self.assertEqual(fin.issues[0].motif,Motif.MIN_VOLUME_OR_RISK_REJECT)
        self.assertFalse(fin.etat.reprise.reservations.reservations)

    def test_inconnu_verrouille_eurusd_et_garde_risque_mais_pas_gbpusd(self):
        b=bloc_coordinateur(); lot=traiter(b,signaux=(signal(),),cotations=(cotation(),)); confirmer(b,lot)
        lot=traiter(b,T+5000)
        self.assertIn('EURUSD',lot.etat.reprise.reservations.verrous)
        t=T+900000
        lot=traiter(b,t,signaux=(signal(symbole='GBPUSD',cloture_ms=t),),cotations=(cotation(symbole='GBPUSD',instant_fournisseur_ms=t,instant_reception_ms=t),))
        self.assertEqual([c.cle.symbole for c in lot.preparations],['GBPUSD'])
        self.assertEqual(len(lot.etat.reprise.reservations.reservations),2)
        self.assertTrue(any(c.nature is NatureCommande.ALERTE for c in lot.commandes))

    def test_cotation_future_et_signal_revise_sont_refuses(self):
        b=bloc_coordinateur(); etat=b.coordinateur.etat
        with self.assertRaises(ValueError): traiter(b,cotations=(replace(cotation(),instant_reception_ms=T+1),))
        self.assertEqual(b.coordinateur.etat,etat)
        traiter(b,signaux=(signal(),),cotations=(cotation(),))
        with self.assertRaises(ValueError): traiter(b,signaux=(signal(stop_technique=1.0997),))
