"""Catégorie 1 : créneaux Londres, métriques immuables et recherche mensuelle."""
import unittest
from copy import deepcopy
from dataclasses import replace
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.service_ia.c0_types import ErreurService, JobIA, canonique
from xpbots.service_ia.c3_planificateur import PlanificateurIA
from .support_planificateur import composer, cas_fixes, metrique


def enfiler_note(e,ident='note',kind='JOURNAL'):
    j=JobIA(ident,kind,None,e.h.t,e.h.t+e.r.p['job_deadline_seconds']*1000,
        canonique(dict(kind=kind,documents=[],metrics=[])))
    e.rt.enregistrer(j);return j


class Planification(unittest.TestCase):
    def test_brief_ete_hiver_aux_instants_locaux_et_une_seule_fois(self):
        for avant in ('2026-07-15T06:44:59Z','2026-01-14T07:44:59Z'):
            e=composer(instant_depuis_iso(avant));self.assertFalse(e.p.planifier())
            e.h.t+=1000;ids=e.p.planifier();self.assertEqual(len(ids),1)
            self.assertEqual(e.rt.en_attente()[0].kind,'BRIEFING');self.assertFalse(e.p.planifier())
    def test_journal_ete_hiver_au_creneau_exporte(self):
        for avant in ('2026-07-15T15:14:59Z','2026-01-14T16:14:59Z'):
            e=composer(instant_depuis_iso(avant));e.p.planifier();e.h.t+=1000
            self.assertEqual(len(e.p.planifier()),1);self.assertEqual(e.rt.en_attente()[0].kind,'JOURNAL')
    def test_pas_de_rattrapage_brief_au_demarrage_ni_hors_jours_actifs(self):
        for t in ('2026-11-17T07:45:01Z','2026-11-21T07:45:00Z'):
            e=composer(instant_depuis_iso(t));self.assertFalse(e.p.planifier());self.assertFalse(e.rt.en_attente())
    def test_job_note_expire_a_sa_borne_sans_transport(self):
        e=composer(instant_depuis_iso('2026-11-17T07:45:00Z'));e.p.planifier()
        e.h.t+=e.r.p['job_deadline_seconds']*1000
        self.assertEqual(e.p.executer_un().erreur,'JOB_EXPIRE');self.assertFalse(e.http.requetes)
    def test_metriques_signees_idempotentes_et_reutilisation_id_refusee(self):
        e=composer();v=metrique(e)
        self.assertEqual(e.p.recevoir_metriques([v])['metrics_created'],1)
        self.assertEqual(e.p.recevoir_metriques([v])['metrics_created'],0)
        with self.assertRaises(ErreurService):e.p.recevoir_metriques([dict(v,net_pnl='999')])
        self.assertEqual(e.m.tables['experiment_metrics'][v['item_id']]['net_pnl'],'-1.25')
    def test_metriques_futures_personnelles_non_finies_et_axes_refuses(self):
        e=composer();v=metrique(e)
        for kw in ({'known_at_ms':e.h.t+1},{'account_id':'personnel'},{'net_pnl':'NaN'},
                {'equity_drawdown':'-0.01'},{'trade_count':True},{'dimensions':{'positions':1}},
                {'dimensions':{'direction':{'private':'value'}}},{'refusals':{'TEST':-1}},
                {'period':'2099-01-01'}):
            with self.subTest(kw=kw),self.assertRaises(ErreurService):e.p.recevoir_metriques([dict(v,**kw)])
        self.assertFalse(e.m.tables['experiment_metrics'])
    def test_decisions_calculees_archivees_sans_futur_et_atomicite(self):
        e=composer();v=metrique(e)
        d=dict(strategy=v['strategy'],symbol=v['symbol'],bar_close=e.h.t,
            baseline_reasons=[],ai_reason='AI_CONTEXT_VETO',snapshot_id=1,arm='IA',known_at_ms=e.h.t)
        self.assertEqual(e.p.recevoir_metriques([v],decisions=[d]),dict(metrics_created=1,decisions_created=1))
        self.assertEqual(e.p.recevoir_metriques([v],decisions=[d]),dict(metrics_created=0,decisions_created=0))
        with self.assertRaises(ErreurService):
            e.p.recevoir_metriques([metrique(e,'autre')],decisions=[dict(d,bar_close=e.h.t+1)])
        self.assertNotIn('autre',e.m.tables['experiment_metrics'])
    def test_hypotheses_plafond_global_et_note_brute_non_reduite(self):
        e=composer();maximum=e.r.p['new_research_hypotheses_max_per_month']
        hs=[dict(statement='Hypothesis '+str(n),validation_plan='Causal offline experiment.') for n in range(maximum)]
        e.http.hypotheses=hs;enfiler_note(e,'premiere');e.p.executer_un()
        self.assertEqual(len(e.m.tables['research_hypotheses']),maximum)
        e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
        e.http.hypotheses=[dict(statement='One additional proposal',validation_plan='No automatic change.')]
        enfiler_note(e,'seconde');e.p.executer_un();a=e.m.tables['advisories']['seconde']
        self.assertEqual(len(a['raw_validated']['hypotheses']),1);self.assertEqual(a['published']['hypotheses'],[])
        self.assertEqual(a['hypotheses_omitted'],1);self.assertFalse(e.m.tables['policy_events'])
        self.assertTrue(all(v['version']==1 for v in e.m.tables['research_hypotheses'].values()))
    def test_hypothese_identique_non_comptee_comme_nouvelle(self):
        e=composer();h=dict(statement='A fixed proposal.',validation_plan='A fixed experiment.')
        e.http.hypotheses=[h];enfiler_note(e,'un');e.p.executer_un()
        e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
        enfiler_note(e,'deux');e.p.executer_un()
        self.assertEqual(len(e.m.tables['research_hypotheses']),1)
        self.assertEqual(e.m.tables['advisories']['deux']['published']['hypotheses'],[h])
    def test_nouveau_mois_utc_reouvre_seulement_le_plafond_des_nouvelles_hypotheses(self):
        e=composer(instant_depuis_iso('2026-11-30T18:00:00Z'));n=e.r.p['new_research_hypotheses_max_per_month']
        for mois in ('2026-11','2026-12'):
            if mois.endswith('12'):e.h.t=instant_depuis_iso('2026-12-01T18:00:00Z')
            e.http.hypotheses=[dict(statement=mois+' proposal '+str(i),validation_plan='Offline evidence.') for i in range(n)]
            enfiler_note(e,mois);self.assertIsNone(e.p.executer_un().erreur)
        self.assertEqual(len(e.m.tables['research_hypotheses']),n*2)
    def test_corpus_incomplet_duplique_ou_attendu_sans_preuve_refuse(self):
        e=composer();cs=cas_fixes(e.r)
        for cas in (cs[:-1],(cs[0],)*len(cs),tuple([replace(cs[0],attendu=canonique(dict(x='invalid')))]+list(cs[1:]))):
            with self.subTest(cas=cas[:1]),self.assertRaises(ErreurService):
                PlanificateurIA(e.r,e.m,e.rt,e.c,e.h,e.cal,cas_derives=cas)
    def test_corpus_absent_ne_qualifie_aucun_fournisseur(self):
        e=composer();self.assertIn('corpus_derives',e.m.tables['alerts'])
        self.assertTrue(all(v['qualification']=='NON_QUALIFIE' for k,v in e.m.tables['provider_state'].items() if k.startswith('veto:')))
    def test_horloge_en_recul_refusee(self):
        e=composer();e.p.planifier();e.h.t-=1
        with self.assertRaises(ErreurService):e.p.planifier()
