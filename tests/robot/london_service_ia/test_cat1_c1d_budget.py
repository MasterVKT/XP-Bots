"""Catégorie 1, couche 1d : coûts, réservations, quotas et rapprochements A09."""
from dataclasses import replace, FrozenInstanceError
from datetime import timedelta
from decimal import Decimal as D
import unittest
from xpbots.service_ia.c0_types import ErreurService, iso
from xpbots.service_ia.c1d_budget import cout_maximal, budget_admet, RegistreBudget
from .support_budget import registre, profil, demande


class BudgetPartage(unittest.TestCase):
    def test_types_stricts_et_reservation_immuable(self):
        r,m,b,p,t=registre();j=demande(t)
        a=b.reserver(j,p,r.p['max_input_tokens_upper_bound'],t)
        self.assertTrue(a.acceptee)
        with self.assertRaises(FrozenInstanceError):a.reservation.reserve_usd=D('1')
        for v in (True,-1,r.p['max_input_tokens_upper_bound']+1):
            with self.subTest(v=v),self.assertRaises(ErreurService):b.reserver(j,p,v,t)
        with self.assertRaises(ErreurService):replace(p,quota_tokens_minute=True)
        for v in ('NaN','Infinity','-1',True):
            with self.subTest(v=v),self.assertRaises(ErreurService):budget_admet(r,v,0,0)

    def test_meme_job_fournisseur_pas_de_seconde_facturation(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];j=demande(t)
        a=b.reserver(j,p,n,t)
        autre=RegistreBudget(r,m).reserver(j,p,n,t)
        self.assertEqual(autre.raison,'DEJA_TENTEE')
        self.assertEqual(len(m.tables['api_attempts']),1)
        self.assertEqual(a.reservation.reserve_usd,D(0))

    def test_profils_non_prets_et_gemini_payant_refuses(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];j=demande(t)
        cas=[replace(p,cle_disponible=False),replace(p,gratuit_confirme=False),
             replace(p,verifie_ms=None),replace(p,verifie_ms=t+1),
             replace(p,modele='outside-allowlist'),replace(p,quota_tokens_minute=0)]
        gemini=r.p['providers'][1]
        cas.append(profil(r,t,fournisseur=gemini['id'],modele=gemini['model'],profil_facturation='DEDICATED_PROJECT'))
        for mauvais in cas:
            with self.subTest(profil=mauvais):self.assertFalse(b.reserver(j,mauvais,n,t).acceptee)
        self.assertFalse(m.tables['api_attempts'])

    def test_payant_desactive_prix_et_provisions_explicitement_verifies(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound'];j=demande(t)
        self.assertEqual(b.reserver(j,p,n,t).raison,'ROUTE_PAYANTE_DESACTIVEE')
        for mauvais in (replace(p,projet_dedie=False),replace(p,prix_entree=p.prix_entree+D(1)),replace(p,prix_sortie=None)):
            with self.subTest(profil=mauvais):self.assertFalse(b.reserver(j,mauvais,n,t,paiement_autorise=True).acceptee)
        m.tables['api_budget'].clear()
        self.assertEqual(b.reserver(j,p,n,t,paiement_autorise=True).raison,'PROVISION_NON_VERIFIEE')
        b.provisionner(iso(t)[:7],'0','0')
        self.assertTrue(b.reserver(j,p,n,t,paiement_autorise=True).acceptee)

    def test_revue_prix_exactement_sept_jours_puis_un_ms_de_plus(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        age=timedelta(days=r.p['paid_price_review_max_age_days'])//timedelta(milliseconds=1)
        self.assertEqual(b.reserver(demande(t),replace(p,verifie_ms=t-age-1),n,t,paiement_autorise=True).raison,'PRIX_PERIMES')
        self.assertTrue(b.reserver(demande(t),replace(p,verifie_ms=t-age),n,t,paiement_autorise=True).acceptee)

    def test_espacement_et_retry_after_ne_raccourcissent_pas_la_pause(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];pas=r.p['provider_min_request_spacing_seconds']*1000
        self.assertTrue(b.reserver(demande(t,'a'),p,n,t).acceptee)
        self.assertEqual(b.reserver(demande(t+pas-1,'b'),p,n,t+pas-1).raison,'ESPACEMENT_FOURNISSEUR')
        self.assertTrue(b.reserver(demande(t+pas,'b'),p,n,t+pas).acceptee)
        b.signaler_echec(p.fournisseur,t+pas,429,retry_after_ms=pas+1)
        self.assertFalse(b.reserver(demande(t+pas+pas,'c'),p,n,t+pas+pas).acceptee)
        self.assertTrue(b.reserver(demande(t+pas+pas+1,'c'),p,n,t+pas+pas+1).acceptee)

    def test_plafond_tentatives_commun_aux_notes_et_modeles(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];pas=r.p['provider_min_request_spacing_seconds']*1000
        for numero in range(r.p['max_api_attempts_per_utc_day']):
            maintenant=t+numero*pas
            self.assertTrue(b.reserver(demande(maintenant,str(numero),'JOURNAL'),p,n,maintenant).acceptee)
        maintenant=t+r.p['max_api_attempts_per_utc_day']*pas
        self.assertEqual(b.reserver(demande(maintenant,'golden','GOLDEN'),p,n,maintenant).raison,'QUOTA_TENTATIVES')
        self.assertEqual(len(m.tables['api_attempts']),r.p['max_api_attempts_per_utc_day'])

    def test_sous_plafond_evenementiel_ne_bloque_pas_une_note(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];pas=r.p['provider_min_request_spacing_seconds']*1000
        for numero in range(r.p['max_event_classification_attempts_per_day']):
            maintenant=t+numero*pas
            self.assertTrue(b.reserver(demande(maintenant,str(numero)),p,n,maintenant).acceptee)
        maintenant=t+r.p['max_event_classification_attempts_per_day']*pas
        self.assertEqual(b.reserver(demande(maintenant,'autre-methode'),p,n,maintenant).raison,'QUOTA_CLASSIFICATIONS')
        self.assertTrue(b.reserver(demande(maintenant,'journal','JOURNAL'),p,n,maintenant).acceptee)

    def test_borne_tokens_independante_sur_compteur_externe(self):
        for excedent in (0,1):
            r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound']
            total=n+r.p['max_output_tokens_including_reasoning']
            # La borne est testée indépendamment : 24 enveloppes maximales
            # restent naturellement sous le plafond de tokens de l’export.
            self.assertLess(r.p['max_api_attempts_per_utc_day']*total,r.p['max_reserved_tokens_per_utc_day'])
            m.tables['schedule_state']['quota:'+iso(t)[:10]]=dict(attempts=0,event_attempts=0,
                reserved_tokens=r.p['max_reserved_tokens_per_utc_day']-total+excedent)
            a=b.reserver(demande(t),p,n,t)
            self.assertEqual(a.acceptee,excedent==0)
            if excedent:self.assertEqual(a.raison,'QUOTA_TOKENS')

    def test_quota_effectif_tokens_minute_avec_marge_exportee(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound']
        mauvais=replace(p,quota_tokens_minute=p.quota_tokens_minute-1)
        self.assertEqual(b.reserver(demande(t),mauvais,n,t).raison,'QUOTA_FOURNISSEUR')
        self.assertTrue(b.reserver(demande(t),p,n,t).acceptee)

    def test_budgets_mensuels_aux_bornes(self):
        r,_,_,_,_=registre(payant=True);cout=cout_maximal(r)
        api=D(r.p['monthly_paid_api_subcap_usd']);total=D(r.p['monthly_total_budget_usd'])
        epsilon=D(1).scaleb(cout.as_tuple().exponent-1)
        for depense,autres,attendu in ((api-cout,D(0),True),(api-cout+epsilon,D(0),False),
                                      (D(0),total-cout,True),(D(0),total-cout+epsilon,False)):
            with self.subTest(depense=depense,autres=autres):
                r,m,b,p,t=registre(payant=True);mois=iso(t)[:7]
                b.provisionner(mois,autres,'0')
                m.tables['api_budget'][mois]['spent_usd']=str(depense)
                a=b.reserver(demande(t),p,r.p['max_input_tokens_upper_bound'],t,paiement_autorise=True)
                self.assertEqual(a.acceptee,attendu)
                if not attendu:self.assertEqual(a.raison,'BUDGET_EPUISE')

    def test_cout_inconnu_garde_reserve_et_compteurs_apres_reprise(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        resultat=b.rapprocher(a.tentative_id,None,None,None,t+1)
        self.assertEqual(resultat['status'],'UNKNOWN');self.assertIsNone(resultat['actual_cost'])
        nouveau=RegistreBudget(r,m)
        self.assertEqual(D(nouveau.consulter(a.mois)['reserved_usd']),a.reserve_usd)
        self.assertEqual(nouveau.reserver(demande(t),p,n,t,paiement_autorise=True).raison,'DEJA_TENTEE')

    def test_rapprochement_connu_libere_une_seule_reserve_et_debite_une_fois(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        i=n//2;o=r.p['max_output_tokens_including_reasoning']//2
        usage=dict(input_tokens=i,output_tokens=o)
        v=b.rapprocher(a.tentative_id,i,o,usage,t+1)
        self.assertEqual(v['status'],'KNOWN');self.assertEqual(D(v['actual_cost']),cout_maximal(r,i,o))
        b.rapprocher(a.tentative_id,i,o,usage,t+2)
        self.assertEqual(D(b.consulter(a.mois)['reserved_usd']),D(0))
        self.assertEqual(D(b.consulter(a.mois)['spent_usd']),cout_maximal(r,i,o))

    def test_depassement_tokens_desactive_meme_si_cout_sous_reserve(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        v=b.rapprocher(a.tentative_id,n+1,0,dict(input_tokens=n+1,output_tokens=0),t+1)
        self.assertLess(D(v['actual_cost']),a.reserve_usd)
        self.assertEqual(v['status'],'BOUND_EXCEEDED');self.assertTrue(b.etat_route(p.fournisseur)['disabled'])

    def test_rapprochement_contradictoire_ne_debite_pas_deux_fois(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        v=b.rapprocher(a.tentative_id,n,0,dict(input_tokens=n,output_tokens=0),t+1)
        b.rapprocher(a.tentative_id,n,1,dict(input_tokens=n,output_tokens=1),t+2)
        self.assertEqual(D(b.consulter(a.mois)['spent_usd']),D(v['actual_cost']))
        self.assertTrue(b.etat_route(p.fournisseur)['disabled'])

    def test_401_et_403_persistants(self):
        for statut in (401,403):
            r,m,b,p,t=registre();b.signaler_echec(p.fournisseur,t,statut)
            self.assertEqual(RegistreBudget(r,m).reserver(demande(t),p,r.p['max_input_tokens_upper_bound'],t).raison,'ROUTE_DESACTIVEE')

    def test_quotas_effectifs_journaliers_et_debit_requetes(self):
        for champ in ('quota_requetes_jour','quota_tokens_jour','quota_requetes_minute'):
            r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound'];pas=r.p['provider_min_request_spacing_seconds']*1000
            if champ=='quota_requetes_jour':p=replace(p,quota_requetes_jour=2)
            elif champ=='quota_tokens_jour':p=replace(p,quota_tokens_jour=p.quota_tokens_minute)
            else:p=replace(p,quota_requetes_minute=1)
            self.assertTrue(b.reserver(demande(t,'a'),p,n,t).acceptee)
            self.assertFalse(b.reserver(demande(t+pas,'b'),p,n,t+pas).acceptee)

    def test_erreurs_et_dates_hors_contrat_sans_debit(self):
        r,m,b,p,t=registre();n=r.p['max_input_tokens_upper_bound']
        self.assertFalse(b.reserver(demande(t+1),p,n,t).acceptee)
        self.assertFalse(b.reserver(replace(demande(t),utile_jusqua_ms=t+1),p,n,t+1).acceptee)
        with self.assertRaises(ErreurService):b.rapprocher('absent',1,1,{},t)
        for mois in ('2026-13','not-a-month','2026-1'):
            with self.subTest(mois=mois),self.assertRaises(ErreurService):b.provisionner(mois,'0','0')
