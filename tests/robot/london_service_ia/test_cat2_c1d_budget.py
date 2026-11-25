"""Catégorie 2, couche 1d : oracles monétaires et reprise du vrai registre pur."""
from datetime import datetime, timezone
from decimal import Decimal as D
import unittest
from reference.llm_contracts import reserve_cost_usd, budget_admits
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.service_ia.c0_types import iso
from xpbots.service_ia.c1d_budget import cout_maximal, budget_admet, RegistreBudget
from .support import ressources
from .support_budget import registre, demande


class JonctionBudget(unittest.TestCase):
    def test_cout_maximal_egal_oracle_aux_bornes(self):
        r=ressources();i=r.p['max_input_tokens_upper_bound'];o=r.p['max_output_tokens_including_reasoning']
        for entree in (0,i//2,i):
            for sortie in (0,o//2,o):
                with self.subTest(entree=entree,sortie=sortie):
                    self.assertEqual(cout_maximal(r,entree,sortie),reserve_cost_usd(entree,sortie))
        self.assertEqual(cout_maximal(r),reserve_cost_usd())

    def test_budget_admet_egal_oracle_sur_matrice_et_bornes(self):
        r=ressources();api=D(r.p['monthly_paid_api_subcap_usd']);total=D(r.p['monthly_total_budget_usd'])
        cout=cout_maximal(r);epsilon=D(1).scaleb(cout.as_tuple().exponent-1)
        for depense in (D(0),api-cout,api-cout+epsilon,api):
            for reserve in (D(0),cout):
                for autres in (D(0),total-api,total-api+epsilon):
                    for taxes in (D(0),cout):
                        with self.subTest(depense=depense,reserve=reserve,autres=autres,taxes=taxes):
                            self.assertEqual(budget_admet(r,depense,reserve,cout,autres,taxes),
                                budget_admits(depense,reserve,cout,autres,taxes))

    def test_reserve_persistante_et_reconciliation_egal_oracle(self):
        r,m,b,p,t=registre(payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        self.assertEqual(a.reserve_usd,reserve_cost_usd(n,r.p['max_output_tokens_including_reasoning']))
        b.rapprocher(a.tentative_id,None,None,{},t+1)
        b=RegistreBudget(r,m)
        v=b.rapprocher(a.tentative_id,n,0,dict(input_tokens=n,output_tokens=0),t+2)
        self.assertEqual(D(v['actual_cost']),reserve_cost_usd(n,0))
        self.assertEqual(D(b.consulter(a.mois)['reserved_usd']),D(0))

    def test_reponse_mois_suivant_debite_le_mois_de_la_tentative(self):
        t=instant_depuis_datetime(datetime(2026,11,30,23,59,30,tzinfo=timezone.utc))
        r,m,b,p,t=registre(t,payant=True);n=r.p['max_input_tokens_upper_bound']
        a=b.reserver(demande(t),p,n,t,paiement_autorise=True).reservation
        reception=t+r.p['provider_min_request_spacing_seconds']*1000
        self.assertNotEqual(iso(t)[:7],iso(reception)[:7])
        b.rapprocher(a.tentative_id,n,0,dict(input_tokens=n,output_tokens=0),reception)
        self.assertEqual(D(b.consulter(a.mois)['spent_usd']),reserve_cost_usd(n,0))
        self.assertEqual(D(b.consulter(iso(reception)[:7])['spent_usd']),D(0))

    def test_compteurs_utc_repris_sans_remise_a_zero_implicite(self):
        t=instant_depuis_datetime(datetime(2026,11,30,23,59,30,tzinfo=timezone.utc))
        r,m,b,p,t=registre(t);n=r.p['max_input_tokens_upper_bound'];jour=iso(t)[:10]
        m.tables['schedule_state']['quota:'+jour]=dict(attempts=r.p['max_api_attempts_per_utc_day'],event_attempts=0,reserved_tokens=0)
        self.assertFalse(RegistreBudget(r,m).reserver(demande(t),p,n,t).acceptee)
        suivant=t+r.p['provider_min_request_spacing_seconds']*1000
        self.assertTrue(RegistreBudget(r,m).reserver(demande(suivant,'nouveau'),p,n,suivant).acceptee)
