"""Catégorie 1, couche 4 : cycle C08, construit transition par transition."""
from dataclasses import replace
from decimal import Decimal as D
import hashlib
import unittest

from robot.outils.cycle_execution import bloc_cycle, remplissage, cloture
from xpbots.execution.c0a_types import EtatIntention, PositionCompte
from xpbots.execution.c4_cycle import (
    CommandeExecution, CycleOrdre, EtatCycle, NatureCommande, PreuvePersistance,
    ReponseCourtier, NatureReponse, StatutAccuse, identifier_courtier, PreuveAbsence,
)
from xpbots.noyau.c1c_domaine import NatureIssue, CauseCloture, Sens, Motif


class TestCycleOrdre(unittest.TestCase):
    def test_reponses_tardives_ne_reactivent_pas_un_cycle_clos(self):
        for nature in ('accuse','annulation'):
            b=bloc_cycle();t=b.signal.cloture_ms
            b.cycle.preparer_envoi(t);b.cycle.sur_reponse(remplissage(b))
            commande=b.cycle.demander_cloture(t+2,CauseCloture.DUREE_MAXIMALE,peut_envoyer=True).commandes[0]
            b.cycle.sur_reponse(cloture(b,instant_ms=t+3))
            if nature=='accuse':
                r=ReponseCourtier(NatureReponse.ACCUSE,b.plan.reservation.cle,'late',t+4,
                    dict(commande=commande.reference,statut=StatutAccuse.INCONNU,code_natif='retard',definitif=False,ordre=None))
            else:
                r=ReponseCourtier(NatureReponse.ANNULATION,b.plan.reservation.cle,'late',t+4,
                    dict(ordre='ordre-1',confirmee=False))
            e=b.cycle.sur_reponse(r)
            self.assertEqual(e.commandes,())
            self.assertEqual(e.issues,())
            self.assertIsNone(b.cycle.prochaine_echeance_ms)
            self.assertEqual(e.etat.statut.value,'CLOTUREE')

    def test_reprise_tardive_ne_recommence_pas_la_fenetre_rapide(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t)
        c=CycleOrdre(b.params,b.signal,b.plan,b.profil,16,b.cycle.etat)
        e=c.reprendre(t+60000)
        self.assertEqual(e.etat.inconnu_ms,t+5000)
        self.assertEqual(e.etat.prochain_rapprochement_ms,t+65000)
        self.assertTrue(any(x.nature is NatureCommande.ALERTE for x in c.sur_minuterie(t+60000).commandes))
        self.assertFalse(any(x.nature is NatureCommande.ENTREE for x in e.commandes))

    def test_reduction_en_cours_est_rapprochee_sans_second_envoi(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b))
        cible=b.plan.volume-D('.1')
        e=b.cycle.demander_cloture(t+2,CauseCloture.RISQUE_APRES_REMPLISSAGE,volume_cible=cible,peut_envoyer=True)
        commande=e.commandes[0]
        ack=ReponseCourtier(NatureReponse.ACCUSE,b.plan.reservation.cle,'close-ack',t+3,
            dict(commande=commande.reference,statut=StatutAccuse.ACCEPTE,code_natif='native',definitif=False,ordre=None))
        b.cycle.sur_reponse(ack)
        e=b.cycle.sur_minuterie(t+1002,negociable=True)
        self.assertTrue(any(c.nature is NatureCommande.RAPPROCHEMENT for c in e.commandes))
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in e.commandes))
        e=b.cycle.sur_minuterie(t+2002,negociable=True)
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in e.commandes))

    def test_refus_confirme_autorise_reessai_mais_accuse_inconnu_ne_le_fait_pas(self):
        for statut in (StatutAccuse.REFUSE,StatutAccuse.INCONNU):
            b=bloc_cycle(); t=b.signal.cloture_ms
            b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b))
            e=b.cycle.demander_cloture(t+2,CauseCloture.RISQUE_APRES_REMPLISSAGE,
                volume_cible=b.plan.volume-D('.1'),peut_envoyer=True)
            ack=ReponseCourtier(NatureReponse.ACCUSE,b.plan.reservation.cle,'close-ack',t+3,
                dict(commande=e.commandes[0].reference,statut=statut,code_natif='native',definitif=False,ordre=None))
            b.cycle.sur_reponse(ack)
            e=b.cycle.sur_minuterie(t+1003,negociable=True)
            self.assertEqual(any(c.nature is NatureCommande.CLOTURE for c in e.commandes),statut is StatutAccuse.REFUSE)

    def test_apres_echec_tp_la_prochaine_echeance_est_le_reessai_de_sortie(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b,tp=None))
        e=b.cycle.sur_minuterie(t+15001,negociable=True)
        self.assertEqual(e.etat.cause_sortie,CauseCloture.PROTECTION)
        self.assertEqual(b.cycle.prochaine_echeance_ms,t+16001)
        b.cycle.sur_minuterie(t+16001,negociable=False)
        self.assertEqual(b.cycle.prochaine_echeance_ms,t+17001)

    def test_cotation_future_refusee_et_rapprochement_continue_pendant_la_sortie(self):
        b = bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b))
        avant=b.cycle.etat
        with self.assertRaises(ValueError):
            b.cycle.sur_minuterie(t+2, cotation=replace(b.cotation, instant_reception_ms=t+3))
        self.assertIs(b.cycle.etat, avant)
        b.cycle.demander_cloture(t+2, CauseCloture.DUREE_MAXIMALE, peut_envoyer=True)
        b.cycle.reprendre(t+3)
        e=b.cycle.sur_minuterie(t+1003, negociable=True)
        self.assertTrue(any(c.nature is NatureCommande.RAPPROCHEMENT for c in e.commandes))
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in e.commandes))

    def _remplir_compte(self, b, **changes):
        b.cycle.preparer_envoi(b.signal.cloture_ms)
        e = b.cycle.sur_reponse(remplissage(b, **changes))
        for i in e.issues:
            b.registre.sur_issue(i)
        p = PositionCompte('position-1', b.signal.symbole, b.profil.sous_jacent,
            e.etat.volume_ouvert, b.plan.risque, b.plan.reservation.cle)
        b.port.compte = replace(b.compte, instant_ms=e.etat.dernier_ms,
            positions=(p,), marge_utilisee=e.etat.volume_ouvert)

    def test_risque_apres_fill_reduit_au_plus_grand_volume_et_garde_la_reserve_initiale(self):
        b = bloc_cycle(); self._remplir_compte(b, frais_entree=D('.15'))
        reserve = b.registre.etat
        e = b.cycle.controler_risque(b.registre, b.garde, b.port, b.signal.cloture_ms+1)
        self.assertEqual(e.etat.cause_sortie, CauseCloture.RISQUE_APRES_REMPLISSAGE)
        # Prix réel, seule réserve de sortie .000025, frais réalisés .15 USD.
        volumes = [D(i)/10 for i in range(1, int(b.plan.volume*10)+1)]
        admissibles = [v for v in volumes if v*1000*(b.plan.niveaux.entree-b.plan.niveaux.stop+D('.000025'))+D('.15') <= D('.5')]
        cible = max(admissibles)
        self.assertEqual(e.etat.volume_cible, cible)
        self.assertEqual(e.commandes[0].donnees['volume'], b.plan.volume-cible)
        self.assertEqual(b.registre.etat, reserve)
        self.assertTrue(any(a[0]=='frais_sortie' for a in b.port.appels))

    def test_frais_entree_inconnus_et_minimum_inadmissible_imposent_la_cloture(self):
        for frais in (None, D('1')):
            b = bloc_cycle(); self._remplir_compte(b, frais_entree=frais)
            e = b.cycle.controler_risque(b.registre, b.garde, b.port, b.signal.cloture_ms+1)
            self.assertEqual(e.etat.volume_cible, D(0))
            self.assertEqual(e.commandes[0].donnees['volume'], b.plan.volume)
            self.assertFalse(e.issues)

    def test_budget_et_fonds_propres_initiaux_restent_geles_apres_fill(self):
        b = bloc_cycle(); self._remplir_compte(b, frais_entree=D('.15'))
        b.port.compte = replace(b.port.compte, fonds_propres=D(1000), solde=D(1000))
        e = b.cycle.controler_risque(b.registre, b.garde, b.port, b.signal.cloture_ms+1)
        self.assertLess(e.etat.volume_cible, b.plan.volume)
        self.assertEqual(b.plan.budget_gele, D('.5'))

    def test_fonctions_indisponibles_et_compte_futur_ne_valident_pas_le_risque(self):
        b = bloc_cycle(); self._remplir_compte(b)
        b.port.compte = replace(b.port.compte, instant_ms=b.signal.cloture_ms+2)
        e = b.cycle.controler_risque(b.registre, b.garde, b.port, b.signal.cloture_ms+1)
        self.assertEqual(e.etat.volume_cible, D(0))
        self.assertEqual(e.etat.motif_sortie, Motif.ENVIRONMENT_NOT_READY)

    def test_sl_absent_ou_modifie_impose_une_cloture_immediate(self):
        for sl in (None, D('1.0997')):
            b = bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
            e = b.cycle.sur_reponse(remplissage(b, sl=sl, tp=None))
            self.assertEqual(e.etat.statut, EtatIntention.CLOTURE_DEMANDEE)
            self.assertEqual(e.etat.tentatives_protection, 0)
            self.assertEqual([c.nature for c in e.commandes], [NatureCommande.CLOTURE, NatureCommande.MINUTERIE])
            self.assertEqual(e.commandes[0].donnees['detail'], 'SL_ABSENT')
            self.assertEqual([i.nature for i in e.issues], [NatureIssue.REMPLIE])

    def test_tp_recalcule_au_prix_reel_trois_tentatives_sl_fixe(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t)
        e = b.cycle.sur_reponse(remplissage(b, prix_moyen=b.plan.niveaux.entree+D('.00002')))
        self.assertFalse(e.etat.protections_validees)
        self.assertEqual(e.etat.prochaine_protection_ms, t+251)
        dates = (251, 1251, 4251)
        for indice, date in enumerate(dates, 1):
            self.assertFalse(b.cycle.sur_minuterie(t+date-1, negociable=True).commandes)
            e = b.cycle.sur_minuterie(t+date, negociable=True)
            tp = [c for c in e.commandes if c.nature is NatureCommande.TP]
            self.assertEqual(len(tp), 1)
            self.assertEqual(tp[0].donnees['sl'], b.plan.niveaux.stop)
            self.assertEqual(tp[0].donnees['tp'], e.etat.niveaux_reels.objectif)
            self.assertEqual(e.etat.tentatives_protection, indice)
        self.assertFalse(b.cycle.sur_minuterie(t+15000, negociable=True).commandes)
        e = b.cycle.sur_minuterie(t+15001, negociable=True)
        self.assertEqual([c.nature for c in e.commandes], [NatureCommande.CLOTURE, NatureCommande.MINUTERIE])
        self.assertEqual(e.commandes[0].donnees['detail'], 'TP_NON_RETABLI')

    def test_confirmation_native_arrete_les_corrections_et_reprise_preserve_le_compteur(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b, tp=None))
        b.cycle.sur_minuterie(t+251, negociable=True)
        c = CycleOrdre(b.params, b.signal, b.plan, b.profil, 16, b.cycle.etat)
        c.reprendre(t+300)
        self.assertEqual((c.etat.tentatives_protection, c.etat.prochaine_protection_ms), (1,t+1251))
        e = c.sur_reponse(ReponseCourtier(NatureReponse.PROTECTIONS, c.etat.cle, 'tp-ok', t+301,
            dict(ticket='position-1', sl=b.plan.niveaux.stop, tp=b.plan.niveaux.objectif)))
        self.assertTrue(e.etat.protections_validees)
        self.assertIsNone(e.etat.prochaine_protection_ms)
        self.assertFalse(any(x.nature is NatureCommande.TP for x in c.sur_minuterie(t+16000, negociable=True).commandes))

    def test_tp_depasse_demande_le_marche_sans_inventer_de_cloture(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t)
        q = replace(b.cotation, bid=b.plan.niveaux.objectif, ask=b.plan.niveaux.objectif+D('.0001'),
                    instant_fournisseur_ms=t+1, instant_reception_ms=t+1)
        e = b.cycle.sur_reponse(remplissage(b), q)
        c = next(c for c in e.commandes if c.nature is NatureCommande.CLOTURE)
        self.assertEqual(c.donnees['detail'], 'TP_DEPASSE')
        self.assertNotIn('prix', c.donnees)
        self.assertEqual([i.nature for i in e.issues], [NatureIssue.REMPLIE])

    def test_sortie_sans_cotation_reste_prioritaire_et_sl_tp_natif_fait_foi(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b))
        e = b.cycle.demander_cloture(t+2, CauseCloture.DUREE_MAXIMALE, priorite=4)
        self.assertEqual([c.nature for c in e.commandes], [NatureCommande.MINUTERIE])
        e = b.cycle.demander_cloture(t+3, CauseCloture.PROTECTION,
            motif=Motif.PROTECTION_ERROR, detail='SL_ABSENT', priorite=0)
        self.assertEqual(e.etat.cause_sortie, CauseCloture.PROTECTION)
        self.assertFalse(b.cycle.sur_minuterie(t+1001, negociable=True).commandes)
        e = b.cycle.sur_minuterie(t+1002, negociable=True)
        self.assertEqual(e.commandes[0].nature, NatureCommande.CLOTURE)
        self.assertEqual(e.etat.sl_natif, b.plan.niveaux.stop)
        e = b.cycle.sur_reponse(cloture(b, instant_ms=t+1003, cause=CauseCloture.STOP_LOSS))
        self.assertEqual(e.issues[0].cause, CauseCloture.STOP_LOSS)
        self.assertFalse(b.cycle.sur_minuterie(t+2002, negociable=True).commandes)

    def test_reduction_confirmee_garde_quota_et_ne_vaut_pas_cloture(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_reponse(remplissage(b))
        cible = b.plan.volume-D('.1')
        e = b.cycle.demander_cloture(t+2, CauseCloture.RISQUE_APRES_REMPLISSAGE, volume_cible=cible, peut_envoyer=True)
        self.assertEqual(e.commandes[0].donnees['volume'], D('.1'))
        e = b.cycle.sur_reponse(cloture(b, instant_ms=t+3, volume_restant=cible,
                                       cause=CauseCloture.RISQUE_APRES_REMPLISSAGE))
        self.assertEqual(e.etat.volume_ouvert, cible)
        self.assertIsNone(e.etat.cause_sortie)
        self.assertFalse(e.issues)
        self.assertTrue(e.etat.quota_compte)

    def test_timeout_et_accuse_inconnu_ne_retransmettent_jamais(self):
        for accuse in (None, StatutAccuse.ACCEPTE, StatutAccuse.INCONNU):
            b = bloc_cycle(); t = b.signal.cloture_ms
            entree = b.cycle.preparer_envoi(t).commandes[0]
            if accuse is not None:
                e = b.cycle.sur_reponse(ReponseCourtier(NatureReponse.ACCUSE, entree.cle, 'ack', t+1,
                    dict(commande=entree.reference, statut=accuse, code_natif='native', definitif=False, ordre=None)))
                self.assertFalse(e.issues)
            if accuse is not StatutAccuse.INCONNU:
                self.assertFalse(b.cycle.sur_minuterie(t+4999).commandes)
                e = b.cycle.sur_minuterie(t+5000)
            self.assertEqual(e.etat.statut, EtatIntention.INCONNUE)
            self.assertEqual([c.nature for c in e.commandes], [NatureCommande.RAPPROCHEMENT, NatureCommande.MINUTERIE])
            self.assertFalse(e.issues)
            self.assertFalse(b.cycle.preparer_envoi(t+6000).commandes)

    def test_rapprochement_cadences_bornes_alerte_unique_et_reprise(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_minuterie(t+5000)
        self.assertEqual(b.cycle.prochaine_echeance_ms, t+6000)
        self.assertFalse(b.cycle.sur_minuterie(t+5999).commandes)
        self.assertEqual(b.cycle.sur_minuterie(t+6000).etat.prochain_rapprochement_ms, t+7000)
        e = b.cycle.sur_minuterie(t+35000)
        self.assertEqual(e.etat.prochain_rapprochement_ms, t+40000)
        self.assertFalse(e.etat.alerte_inconnue)
        c = CycleOrdre(b.params, b.signal, b.plan, b.profil, 16, e.etat)
        reprise = c.reprendre(t+35001)
        self.assertEqual(reprise.etat.inconnu_ms, t+5000)
        self.assertFalse(any(x.nature is NatureCommande.ENTREE for x in reprise.commandes))
        e = c.sur_minuterie(t+35002)
        self.assertEqual([x.nature for x in e.commandes], [NatureCommande.ALERTE])
        self.assertFalse(any(x.nature is NatureCommande.ALERTE for x in c.sur_minuterie(t+50000).commandes))

    def test_absence_exige_toutes_les_preuves_et_execution_tardive_fait_foi(self):
        b = bloc_cycle(); t = b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_minuterie(t+5000)
        preuve = PreuveAbsence(b.plan.reservation.cle, t+6000, t, t+6000, True, True, True, True, True, True)
        for nom in ('historique_complet', 'envoi_termine', 'absence_definitive', 'aucun_ordre', 'aucune_position', 'aucune_execution'):
            self.assertFalse(b.cycle.confirmer_absence(replace(preuve, **{nom:False})).issues)
        self.assertFalse(b.cycle.confirmer_absence(replace(preuve, debut_ms=t+1)).issues)
        e = b.cycle.confirmer_absence(preuve)
        self.assertEqual(e.etat.statut, EtatIntention.REFUSEE)
        self.assertFalse(e.etat.quota_compte)
        e = b.cycle.sur_reponse(remplissage(b, instant_ms=t+6001, execution_ms=t+1))
        self.assertEqual([i.nature for i in e.issues], [NatureIssue.REMPLIE])
        self.assertEqual(e.etat.premier_fill_ms, t+1)

    def test_delais_charges_et_non_litteraux(self):
        b = bloc_cycle(commun_=replace(bloc_cycle().params, request_ack_timeout_seconds=2,
            reconcile_fast_poll_seconds=.5, reconcile_fast_window_seconds=4, reconcile_slow_poll_seconds=2))
        t = b.signal.cloture_ms; b.cycle.preparer_envoi(t)
        self.assertEqual(b.cycle.prochaine_echeance_ms, t+2000)
        self.assertEqual(b.cycle.sur_minuterie(t+2000).etat.prochain_rapprochement_ms, t+2500)
        self.assertEqual(b.cycle.sur_minuterie(t+6000).etat.prochain_rapprochement_ms, t+8000)

    def test_partiel_annule_le_reliquat_sans_complement_ni_second_quota(self):
        b = bloc_cycle()
        b.cycle.preparer_envoi(b.signal.cloture_ms)
        r = remplissage(b, volume_cumule=D('.2'), volume_position=D('.2'),
                        reliquat=b.plan.volume-D('.2'), reliquat_annule=False)
        e = b.cycle.sur_reponse(r)
        self.assertEqual(e.etat.statut, EtatIntention.REMPLIE_PARTIELLE)
        self.assertEqual([i.nature for i in e.issues], [NatureIssue.REMPLIE])
        self.assertEqual(len([c for c in e.commandes if c.nature is NatureCommande.ANNULATION]), 1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in e.commandes))
        doublon = replace(r, reference='autre-reception', instant_ms=r.instant_ms+1)
        self.assertFalse(b.cycle.sur_reponse(doublon).issues)
        suite = remplissage(b, reference='fill-2', instant_ms=r.instant_ms+2, transaction='deal-2',
            volume_cumule=D('.3'), volume_position=D('.3'), reliquat=b.plan.volume-D('.3'), reliquat_annule=False)
        ef = b.cycle.sur_reponse(suite)
        self.assertFalse(ef.issues)
        self.assertFalse(any(c.nature in (NatureCommande.ENTREE, NatureCommande.ANNULATION) for c in ef.commandes))
        self.assertEqual(ef.etat.volume_ouvert, D('.3'))

    def test_annulation_confirmee_ne_cloture_pas_la_partie_executee(self):
        b = bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
        b.cycle.sur_reponse(remplissage(b, volume_cumule=D('.2'), volume_position=D('.2'),
            reliquat=b.plan.volume-D('.2'), reliquat_annule=False))
        r = ReponseCourtier(NatureReponse.ANNULATION, b.plan.reservation.cle, 'cancel-ok', b.signal.cloture_ms+2,
                           dict(ordre='ordre-1', confirmee=True))
        e = b.cycle.sur_reponse(r)
        self.assertTrue(e.etat.reliquat_annule)
        self.assertEqual(e.etat.volume_ouvert, D('.2'))
        self.assertFalse(e.issues)
        self.assertFalse(e.commandes)

    def test_cloture_attend_la_fin_du_reliquat_avant_de_liberer_la_reserve(self):
        b = bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
        b.cycle.sur_reponse(remplissage(b, volume_cumule=D('.2'), volume_position=D('.2'),
            reliquat=b.plan.volume-D('.2'), reliquat_annule=False))
        e = b.cycle.sur_reponse(cloture(b, cause=CauseCloture.STOP_LOSS))
        self.assertEqual(e.etat.volume_ouvert, D(0))
        self.assertNotEqual(e.etat.statut, EtatIntention.CLOTUREE)
        self.assertFalse(e.issues)
        r = ReponseCourtier(NatureReponse.ANNULATION, b.plan.reservation.cle, 'cancel-final', b.signal.cloture_ms+3,
                           dict(ordre='ordre-1', confirmee=True))
        fin = b.cycle.sur_reponse(r)
        self.assertEqual(fin.etat.statut, EtatIntention.CLOTUREE)
        self.assertEqual((fin.issues[0].nature, fin.issues[0].cause, fin.issues[0].instant_ms),
                         (NatureIssue.CLOTUREE, CauseCloture.STOP_LOSS, b.signal.cloture_ms+2))

    def test_cloture_native_connue_avant_le_remplissage_reconstitue_le_cycle(self):
        b = bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
        self.assertFalse(b.cycle.sur_reponse(cloture(b)).issues)
        r = remplissage(b, instant_ms=b.signal.cloture_ms+3, execution_ms=b.signal.cloture_ms+1,
                        volume_position=D(0), sl=None, tp=None)
        e = b.cycle.sur_reponse(r)
        self.assertEqual([i.nature for i in e.issues], [NatureIssue.REMPLIE, NatureIssue.CLOTUREE])
        self.assertEqual(e.etat.statut, EtatIntention.CLOTUREE)

    def test_frais_inconnus_conserves_et_volume_nul_n_est_pas_un_fill(self):
        b = bloc_cycle(); b.cycle.preparer_envoi(b.signal.cloture_ms)
        with self.assertRaises(ValueError):
            remplissage(b, volume_cumule=D(0), volume_position=D(0))
        self.assertFalse(b.cycle.etat.quota_compte)
        e = b.cycle.sur_reponse(remplissage(b, frais_entree=None))
        self.assertTrue(e.etat.quota_compte)
        self.assertIsNone(e.etat.frais_entree)

    def test_accuse_accepte_sans_volume_ne_remplit_ni_ne_consomme(self):
        b = bloc_cycle()
        entree = b.cycle.preparer_envoi(b.signal.cloture_ms).commandes[0]
        r = ReponseCourtier(NatureReponse.ACCUSE, entree.cle, 'ack-1', b.signal.cloture_ms+1,
            dict(commande=entree.reference, statut=StatutAccuse.ACCEPTE, code_natif='10008',
                 definitif=False, ordre='ordre-1'))
        e = b.cycle.sur_reponse(r)
        self.assertEqual(e.etat.statut, EtatIntention.ENVOYEE)
        self.assertTrue(e.etat.accuse_recu)
        self.assertEqual(e.etat.ticket_ordre, 'ordre-1')
        self.assertEqual(e.etat.volume_cumule, D(0))
        self.assertFalse(e.etat.quota_compte)
        self.assertFalse(e.issues)

    def test_refus_natif_confirme_ne_retransmet_pas_et_ne_compte_pas_de_quota(self):
        for definitif in (False, True):
            with self.subTest(definitif=definitif):
                b = bloc_cycle()
                entree = b.cycle.preparer_envoi(b.signal.cloture_ms).commandes[0]
                r = ReponseCourtier(NatureReponse.ACCUSE, entree.cle, 'refus-1', b.signal.cloture_ms+1,
                    dict(commande=entree.reference, statut=StatutAccuse.REFUSE, code_natif='10019',
                         definitif=definitif, ordre=None))
                e = b.cycle.sur_reponse(r)
                self.assertEqual(e.etat.statut, EtatIntention.REFUSEE)
                self.assertEqual([i.nature for i in e.issues], [NatureIssue.REFUSEE])
                self.assertFalse(e.etat.quota_compte)
                self.assertFalse(b.cycle.preparer_envoi(b.signal.cloture_ms+2).commandes)
                self.assertFalse(b.cycle.sur_reponse(replace(r, reference='refus-2', instant_ms=r.instant_ms+1)).issues)

    def test_accuse_d_une_commande_etrangere_refuse_sans_changer_l_etat(self):
        b = bloc_cycle()
        b.cycle.preparer_envoi(b.signal.cloture_ms)
        avant = b.cycle.etat
        r = ReponseCourtier(NatureReponse.ACCUSE, avant.cle, 'ack-invalide', b.signal.cloture_ms+1,
            dict(commande='inconnue:ENTREE:1', statut=StatutAccuse.ACCEPTE, code_natif='10008',
                 definitif=False, ordre=None))
        with self.assertRaises(ValueError):
            b.cycle.sur_reponse(r)
        self.assertIs(b.cycle.etat, avant)

    def test_cycle_minimal_entree_protegee_remplissage_et_cloture_confirmes(self):
        b = bloc_cycle()
        e = b.cycle.preparer_envoi(b.signal.cloture_ms)
        self.assertEqual([c.nature for c in e.commandes], [NatureCommande.ENTREE, NatureCommande.MINUTERIE])
        entree = e.commandes[0]
        self.assertEqual((entree.donnees['volume'], entree.donnees['sl'], entree.donnees['tp']),
                         (b.plan.volume, b.plan.niveaux.stop, b.plan.niveaux.objectif))
        self.assertEqual(e.etat.statut, EtatIntention.ENVOYEE)
        self.assertFalse(e.issues)
        rempli = b.cycle.sur_reponse(remplissage(b))
        self.assertEqual(rempli.etat.statut, EtatIntention.OUVERTE)
        self.assertEqual([i.nature for i in rempli.issues], [NatureIssue.REMPLIE])
        self.assertEqual(rempli.etat.premier_fill_ms, b.signal.cloture_ms+1)
        ferme = b.cycle.sur_reponse(cloture(b))
        self.assertEqual((ferme.etat.statut, ferme.etat.volume_ouvert), (EtatIntention.CLOTUREE, D(0)))
        self.assertEqual((ferme.issues[0].nature, ferme.issues[0].cause),
                         (NatureIssue.CLOTUREE, CauseCloture.TAKE_PROFIT))
        self.assertFalse(ferme.commandes)

    def test_idempotence_envoi_et_reponses_sans_second_quota(self):
        b = bloc_cycle()
        b.cycle.preparer_envoi(b.signal.cloture_ms)
        self.assertFalse(b.cycle.preparer_envoi(b.signal.cloture_ms+1).commandes)
        r = remplissage(b)
        b.cycle.sur_reponse(r)
        avant = b.cycle.etat
        self.assertFalse(b.cycle.sur_reponse(r).issues)
        self.assertIs(b.cycle.etat, avant)
        mauvaise = replace(r, donnees={**r.donnees, 'prix_moyen': r.donnees['prix_moyen']+D('.00001')})
        with self.assertRaises(ValueError):
            b.cycle.sur_reponse(mauvaise)
        self.assertIs(b.cycle.etat, avant)

    def test_d08_identite_stable_par_couple_et_commentaire_par_intention(self):
        b = bloc_cycle()
        k = b.plan.reservation.cle
        identite = identifier_courtier(k, 16)
        attendu = int(hashlib.sha256(b'synthetique|LONDON_V3').hexdigest()[:16], 16) % (2**63)
        self.assertEqual(identite.magic, attendu or 1)
        self.assertEqual(identite.commentaire, 'XPB3:'+k.empreinte(16))
        autre = replace(k, symbole='GBPUSD', sens=Sens.VENTE)
        self.assertEqual(identite.magic, identifier_courtier(autre, 16).magic)
        self.assertNotEqual(identite.commentaire, identifier_courtier(autre, 16).commentaire)
        for changement in ({'deploiement': 'autre'}, {'strategie': 'EMA_V3'}):
            self.assertNotEqual(identite.magic, identifier_courtier(replace(k, **changement), 16).magic)

    def test_trames_fermees_et_bornes_sans_modification_du_cycle(self):
        b = bloc_cycle()
        e = b.cycle.preparer_envoi(b.signal.cloture_ms).commandes[0]
        for donnees in ({**e.donnees, 'inconnu': 1}, {k:v for k,v in e.donnees.items() if k!='sl'},
                        {**e.donnees, 'volume': D('NaN')}, {**e.donnees, 'magic': True}):
            with self.subTest(donnees=donnees), self.assertRaises(ValueError):
                replace(e, donnees=donnees)
        r = remplissage(b)
        with self.assertRaises(ValueError):
            replace(r, donnees={**r.donnees, 'execution_ms': r.instant_ms+1})
        with self.assertRaises(ValueError):
            PreuvePersistance(True, ())
        with self.assertRaises(ValueError):
            PreuvePersistance(1, ('x', 'x'))
        with self.assertRaises(ValueError):
            b.cycle.preparer_envoi(True)

    def test_etat_exporte_restaure_ne_retransmet_pas(self):
        b = bloc_cycle()
        b.cycle.preparer_envoi(b.signal.cloture_ms)
        c = CycleOrdre(b.params, b.signal, b.plan, b.profil, 16, b.cycle.etat)
        self.assertFalse(c.preparer_envoi(b.signal.cloture_ms+1).commandes)
        c.sur_reponse(remplissage(b))
        self.assertTrue(c.etat.quota_compte)
        with self.assertRaises(ValueError):
            replace(c.etat, volume_ouvert=D(0))
        with self.assertRaises(ValueError):
            replace(c.etat, reponses_recues=({},))
