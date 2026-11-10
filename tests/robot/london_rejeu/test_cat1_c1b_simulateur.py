"""Prix, latence, livre natif et frais calculés indépendamment."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C,cas_simulateur,cotation_test
from xpbots.noyau.c1c_domaine import Sens,CauseCloture
from xpbots.execution.c4_cycle import NatureReponse,StatutAccuse
from xpbots.rejeu.c0a_types import ErreurRejeu,TarifCommission,ConditionContrat
from xpbots.rejeu.c1b_simulateur import SimulateurExecution,PlanExecution


class TestSimulateur(unittest.TestCase):
    def test_entree_premier_tick_au_delai_exact_achat_ask_vente_bid(self):
        for sens,prix in ((Sens.ACHAT,D('1.10011')),(Sens.VENTE,D('1.09999'))):
            b,e,c=cas_simulateur(sens);t=b.signal.cloture_ms
            self.assertIs(e.soumettre((c,))[0].donnees['statut'],StatutAccuse.ACCEPTE)
            self.assertEqual(e.sur_tick(cotation_test(b,t+249)),())
            r=e.sur_tick(cotation_test(b,t+250))[0]
            self.assertEqual(r.donnees['prix_moyen'],prix)
            self.assertEqual(r.donnees['execution_ms'],t+250)

    def test_stress_bid_intact_spread_fois_1_25_et_deux_increments(self):
        b,e,c=cas_simulateur(scenario='STRESS');t=b.signal.cloture_ms
        q=e.tick_decision(cotation_test(b,t));self.assertEqual((q.bid,q.ask),(1.1,1.100125))
        e.soumettre((c,));self.assertEqual(e.sur_tick(cotation_test(b,t+999)),())
        r=e.sur_tick(cotation_test(b,t+1000))[0]
        self.assertEqual(r.donnees['prix_moyen'],D('1.100145'))

    def test_tp_limite_au_niveau_ou_mieux_sans_glissement(self):
        for sens,bid,ask,prix in ((Sens.ACHAT,'1.2','1.2001',D('1.2')),(Sens.VENTE,'1.0','1.0001',D('1.0001'))):
            b,e,c=cas_simulateur(sens);t=b.signal.cloture_ms;e.soumettre((c,));e.sur_tick(cotation_test(b,t+250))
            r=e.sur_tick(cotation_test(b,t+251,bid,ask))[0]
            self.assertIs(r.donnees['cause'],CauseCloture.TAKE_PROFIT)
            self.assertEqual(r.donnees['prix'],prix)
            self.assertGreaterEqual(sens.signe*(prix-c.donnees['tp']),0)

    def test_gap_stop_natif_sans_second_delai(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms;e.soumettre((c,));e.sur_tick(cotation_test(b,t+250))
        r=e.sur_tick(cotation_test(b,t+251,'1.09','1.0901'))[0]
        self.assertEqual((r.donnees['cause'],r.donnees['prix']),(CauseCloture.STOP_LOSS,D('1.08999')))
        self.assertLess(r.donnees['prix'],c.donnees['sl'])

    def test_sl_tp_meme_milliseconde_departages_par_sequence(self):
        for premier,cause in ((True,CauseCloture.STOP_LOSS),(False,CauseCloture.TAKE_PROFIT)):
            b,e,c=cas_simulateur();t=b.signal.cloture_ms;e.soumettre((c,));e.sur_tick(cotation_test(b,t+250))
            prix=('1.09','1.2') if premier else ('1.2','1.09')
            r=e.sur_tick(cotation_test(b,t+251,prix[0],str(D(prix[0])+D('.0001')),1))
            suite=e.sur_tick(cotation_test(b,t+251,prix[1],str(D(prix[1])+D('.0001')),2))
            self.assertEqual(r[0].donnees['cause'],cause);self.assertEqual(suite,())

    def test_cloture_marche_attend_delai_et_sl_reste_prioritaire(self):
        for sl in (False,True):
            b,e,c=cas_simulateur();t=b.signal.cloture_ms;e.soumettre((c,));r=e.sur_tick(cotation_test(b,t+250))[0]
            b.cycle.sur_reponse(r)
            fermeture=b.cycle.demander_cloture(t+251,CauseCloture.DUREE_MAXIMALE,peut_envoyer=True).commandes[0]
            e.avancer_au(t+251);e.soumettre((fermeture,))
            if sl:
                r=e.sur_tick(cotation_test(b,t+252,'1.09','1.0901'))[0]
                self.assertIs(r.donnees['cause'],CauseCloture.STOP_LOSS)
            else:
                self.assertEqual(e.sur_tick(cotation_test(b,t+500,'1.101','1.1011')),())
                r=e.sur_tick(cotation_test(b,t+501,'1.101','1.1011'))[0]
                self.assertEqual(r.donnees['prix'],D('1.10099'))

    def test_aucune_execution_inventee_sur_minuterie(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms;e.soumettre((c,));e.avancer_au(t+10000)
        self.assertFalse(e.positions_ouvertes);self.assertEqual(len(e.observation().ordres),1)
        self.assertEqual(len(e.reponses),1)

    def test_ttl_actif_a_l_envoi_pas_effacement_fictif_d_un_ordre_accepte(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms
        e.avancer_au(c.donnees['expire_ms']);r=e.soumettre((c,))[0]
        self.assertIs(r.donnees['statut'],StatutAccuse.REFUSE)
        b,e,c=cas_simulateur();e.soumettre((c,));r=e.sur_tick(cotation_test(b,c.donnees['expire_ms']+1))[0]
        self.assertIs(r.nature,NatureReponse.REMPLISSAGE)

    def test_flottant_frais_marge_et_profit_sans_reserve_g(self):
        tarif=TarifCommission('REEL_SYNTHETIQUE',D(0),D('.03'),D(0),D('.04'))
        b,e,c=cas_simulateur(tarif=tarif);t=b.signal.cloture_ms;e.soumettre((c,));e.sur_tick(cotation_test(b,t+250))
        compte=e.etat_compte();v=c.donnees['volume'];contrat=b.profil.taille_contrat
        self.assertEqual(compte.solde,D('99.97'))
        self.assertEqual(compte.fonds_propres,compte.solde+v*contrat*D('-.00011'))
        self.assertEqual(compte.marge_utilisee,v*contrat*D('1.10011')/D(100))
        e.sur_tick(cotation_test(b,t+251,'1.2','1.2001'));trade=e.trades[0]
        brut=v*contrat*(D('1.2')-D('1.10011'))
        self.assertEqual((trade.profit_brut,trade.net),(brut,brut-D('.07')))
        self.assertEqual(e.etat_compte().solde,D(100)+trade.net)

    def test_commission_minimale_appliquee_une_fois_sur_les_partiels(self):
        b,_,c=cas_simulateur();c=replace(c,donnees={**c.donnees,'volume':D('.2')})
        plan=PlanExecution(fractions=(D('.5'),D('.5')),retards_ms=(0,1))
        tarif=TarifCommission('MINIMUM',D('.1'),D('.05'),D(0),D(0))
        b,e,_=cas_simulateur(tarif=tarif,plans={c.reference:plan});t=b.signal.cloture_ms
        e.soumettre((c,));a=e.sur_tick(cotation_test(b,t+250))[0];z=e.sur_tick(cotation_test(b,t+251))[0]
        self.assertEqual((a.donnees['volume_cumule'],z.donnees['volume_cumule']),(D('.1'),D('.2')))
        self.assertEqual((a.donnees['frais_entree'],z.donnees['frais_entree']),(D('.05'),D('.05')))
        self.assertEqual(e.etat_compte().solde,D('99.95'))

    def test_accuse_inconnu_conserve_l_ordre_et_deduplication(self):
        b,_,c=cas_simulateur();plan=PlanExecution(statut=StatutAccuse.INCONNU)
        b,e,c=cas_simulateur(plans={c.reference:plan});t=b.signal.cloture_ms
        r=e.soumettre((c,c));self.assertEqual(len(r),1);self.assertIs(r[0].donnees['statut'],StatutAccuse.INCONNU)
        self.assertEqual(len(e.observation().ordres),1);self.assertEqual(e.soumettre((c,)),())
        self.assertEqual(len(e.sur_tick(cotation_test(b,t+250))),1)

    def test_accuse_differe_est_une_echeance_sans_cotation(self):
        b,_,c=cas_simulateur();b,e,c=cas_simulateur(plans={c.reference:PlanExecution(retard_accuse_ms=100)})
        t=b.signal.cloture_ms;self.assertEqual(e.soumettre((c,)),())
        self.assertEqual(e.prochaine_echeance_ms,t+100)
        self.assertEqual(e.extraire_reponses(t+99),())
        self.assertEqual(e.extraire_reponses(t+100)[0].instant_ms,t+100)
        self.assertIsNone(e.prochaine_echeance_ms);self.assertFalse(e.positions_ouvertes)

    def test_protections_absentes_sont_des_faits_natifs(self):
        b,_,c=cas_simulateur();b,e,c=cas_simulateur(plans={c.reference:PlanExecution(protections=False)})
        t=b.signal.cloture_ms;e.soumettre((c,));r=e.sur_tick(cotation_test(b,t+250))[0]
        self.assertIsNone(r.donnees['sl']);self.assertIsNone(e.observation().positions[0].sl)

    def test_conditions_datees_et_connaissance_sans_anticipation(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms;creation=e.creation_ms
        tarif=TarifCommission('APRES',D(0),D('.02'),D(0),D('.03'))
        avant=ConditionContrat(creation,t+500,creation,b.profil,TarifCommission('AVANT',D(0),D(0),D(0),D(0)))
        profil=replace(b.profil,tick_size=D('.0001'),releve_ms=t+500)
        apres=ConditionContrat(t+500,creation+86400000,t+500,profil,tarif)
        e=SimulateurExecution(C,(avant,apres),creation,e.scenario);e.avancer_au(t+499)
        self.assertEqual(e.specifications(c.cle.symbole).tick_size,b.profil.tick_size)
        e.avancer_au(t+500);self.assertEqual(e.specifications(c.cle.symbole).tick_size,D('.0001'))
        self.assertEqual(e.frais_aller_retour(profil,Sens.ACHAT,D('.1')),D('.05'))
        with self.assertRaises(ErreurRejeu):SimulateurExecution(C,(avant,avant),creation,e.scenario)

    def test_horloge_ordre_et_blackout_refuses(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms
        with self.assertRaises(ErreurRejeu):e.avancer_au(t-1)
        e.soumettre((c,));e.sur_tick(cotation_test(b,t+250))
        with self.assertRaises(ErreurRejeu):e.sur_tick(cotation_test(b,t+250))
        with self.assertRaisesRegex(ErreurRejeu,'BLACKOUT'):e.avancer_au(e.creation_ms+21*3600000)

    def test_deux_livres_sont_independants(self):
        b,a,c=cas_simulateur();_,z,_=cas_simulateur();a.soumettre((c,));a.sur_tick(cotation_test(b,b.signal.cloture_ms+250))
        self.assertTrue(a.positions_ouvertes);self.assertFalse(z.positions_ouvertes)
        self.assertEqual(z.etat_compte().solde,D(100));self.assertEqual(z.reponses,())

    def test_contexte_copie_a_l_enregistrement_et_frais_sans_remboursement_fictif(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms
        contexte={'stop':{'composantes':[D('1.09')]}}
        e.enregistrer_contexte(c.cle,contexte);contexte['stop']['composantes'].clear()
        e.soumettre((c,));e.sur_tick(cotation_test(b,t+250));e.sur_tick(cotation_test(b,t+251,'1.2','1.2001'))
        self.assertEqual(e.trades[0].contexte['stop']['composantes'],(D('1.09'),))

    def test_baisse_du_tarif_entre_partiels_ne_cree_pas_un_remboursement(self):
        b,e,c=cas_simulateur();t=b.signal.cloture_ms;creation=e.creation_ms
        c=replace(c,donnees={**c.donnees,'volume':D('.2')})
        avant=ConditionContrat(creation,t+251,creation,b.profil,TarifCommission('A',D(0),D('.05'),D(0),D(0)))
        apres=ConditionContrat(t+251,creation+86400000,t+251,replace(b.profil,releve_ms=t+251),
            TarifCommission('B',D(0),D('.01'),D(0),D(0)))
        plan=PlanExecution(fractions=(D('.5'),D('.5')),retards_ms=(0,1))
        e=SimulateurExecution(C,(avant,apres),creation,e.scenario,{c.reference:plan});e.avancer_au(t);e.soumettre((c,))
        a=e.sur_tick(cotation_test(b,t+250))[0];z=e.sur_tick(cotation_test(b,t+251))[0]
        self.assertEqual((a.donnees['frais_entree'],z.donnees['frais_entree']),(D('.05'),D('.05')))
        self.assertEqual(e.etat_compte().solde,D('99.95'))
