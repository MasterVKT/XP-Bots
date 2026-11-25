"""Catégorie 2 : collecte, routeur, calendrier, veto et dérive réels."""
import unittest
from dataclasses import replace
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.service_ia.c0_types import JobIA, canonique, decoder, utc
from xpbots.service_ia.c1f_snapshot import EcrivainSnapshot
from xpbots.service_ia.c3_planificateur import PlanificateurIA
from xpbots.contexte_ia.c0_types import PolitiqueVeto, charger_parametres
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from .support_planificateur import composer, cas_fixes
from .support_calendrier import garde, mapping, CorrespondanceCalendrier, evenement
from .test_cat1_c3_planificateur import enfiler_note


def frais():return composer(instant_depuis_iso('2026-11-17T08:08:00Z'))


def auditer(*,changements=0,citations=False,extraire=None):
    cs=cas_fixes();e=composer(instant_depuis_iso('2026-11-20T16:44:59Z'),cas=cs)
    e.http.nouvelles=False;e.http.changer={c.case_id for c in cs[:changements]};e.http.citations_seules=citations
    e.http.extraire=extraire
    e.p.planifier();e.h.t+=1000;e.p.planifier()
    for _ in cs:
        r=e.p.executer_un()
        if r is None:raise AssertionError('Un cas admissible n’a pas été planifié')
        e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
    return e


class JonctionPlanificateur(unittest.TestCase):
    def test_evenement_actif_retire_apres_changement_modele_et_reprise(self):
        e=frais();e.p.collecter();e.p.executer_un();avant=e.p.evenements(e.h.t)
        self.assertEqual(len(avant),1);archives=dict(e.m.tables['policy_events'])
        w=EcrivainSnapshot(e.r,e.m,lambda b:None)
        lecteur=LecteurContexte(charger_parametres(e.r.configuration),PolitiqueVeto(True))
        lecteur.recevoir(w.publier(e.h.t,avant).octets,e.h.t)
        self.assertEqual(lecteur.evaluer('EURUSD',e.h.t).etat.value,'BLOCK')
        e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
        e.http.modele='synthetic-new-version';enfiler_note(e,'changement');e.p.executer_un()
        self.assertLess(e.h.t,utc(avant[0]['valid_until_utc']))
        self.assertFalse(e.p.evenements(e.h.t))
        nouveau_snapshot=w.publier(e.h.t,e.p.evenements(e.h.t))
        lecteur.recevoir(nouveau_snapshot.octets,e.h.t)
        # A10 : un heartbeat vide ne révoque pas une preuve déjà acceptée.
        self.assertEqual(lecteur.evaluer('EURUSD',e.h.t).etat.value,'BLOCK')
        lecteur_neuf=LecteurContexte(charger_parametres(e.r.configuration),PolitiqueVeto(True))
        lecteur_neuf.recevoir(nouveau_snapshot.octets,e.h.t)
        self.assertEqual(lecteur_neuf.evaluer('EURUSD',e.h.t).etat.value,'NEUTRAL')
        nouveau=PlanificateurIA(e.r,e.m,e.rt,e.c,e.h,e.cal);nouveau.reprendre()
        self.assertFalse(nouveau.evenements(e.h.t));self.assertEqual(e.m.tables['policy_events'],archives)
        self.assertIn('changement',e.m.tables['advisories'])
        fin=utc(avant[0]['valid_until_utc'])
        self.assertEqual(lecteur.evaluer('EURUSD',fin).etat.value,'NEUTRAL')

    def test_evenement_encore_actif_retire_pour_deux_derives_pas_une(self):
        for n in (1,2):
            with self.subTest(changements=n):
                cs=cas_fixes();e=composer(instant_depuis_iso('2026-11-20T16:43:58Z'),cas=cs)
                e.p.collecter();self.assertIsNone(e.p.executer_un().erreur)
                avant=e.p.evenements(e.h.t);self.assertEqual(len(avant),1)
                e.http.nouvelles=False;e.http.changer={c.case_id for c in cs[:n]}
                e.h.t=instant_depuis_iso('2026-11-20T16:44:59Z');e.p.planifier();e.h.t+=1000;e.p.planifier()
                for _ in cs:
                    self.assertIsNone(e.p.executer_un().erreur)
                    e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
                self.assertLess(e.h.t,utc(avant[0]['valid_until_utc']))
                self.assertEqual(bool(e.p.evenements(e.h.t)),n==1)
                self.assertEqual(len(e.m.tables['policy_events']),1)

    def test_article_classe_une_fois_et_partage_sans_double_facturation(self):
        e=frais();e.p.collecter();a=e.p.executer_un()
        self.assertIsNone(a.erreur);self.assertEqual(len(e.p.evenements(e.h.t)),1)
        e.h.t+=e.r.p['rss_poll_seconds']*1000;e.p.collecter();self.assertIsNone(e.p.executer_un())
        self.assertEqual(len([q for q in e.http.requetes if q.methode=='POST']),1)
        self.assertEqual(len(e.m.tables['api_attempts']),1)
    def test_article_a_son_expiration_reste_documentaire_sans_nouvelle_inference(self):
        e=frais();e.http.d=replace(e.http.d,publie_ms=e.h.t-e.r.p['unscheduled_policy_veto_seconds_from_publication']*1000)
        e.p.collecter();self.assertIsNone(e.p.executer_un())
        self.assertTrue(e.m.tables['source_items']);self.assertFalse(e.m.tables['api_attempts'])
    def test_calendrier_programme_ou_indisponible_n_ajoute_pas_veto(self):
        for programme in (False,True):
            e=frais()
            if programme:
                ev=evenement(e.http.d.publie_ms)
                e.cal.g=garde(e.r,e.http.d,annonces=[ev])
                e.cal.table=mapping(e.http.d,correspondances=[CorrespondanceCalendrier(ev['id_evenement'],'FED',e.r.p['calendar_matching_event_kind'])])
            else:e.cal.disponible=False
            e.p.collecter();r=e.p.executer_un();self.assertIsNone(r.erreur);self.assertFalse(e.p.evenements(e.h.t))
            preuve=e.m.tables['schedule_state']['processed:'+r.job_id]
            self.assertEqual(preuve['calendar']['valide'],programme)
            self.assertEqual(preuve['calendar']['correspondance'],programme)
            self.assertIsNotNone(preuve['document'])
    def test_condition_historique_discours_ou_citation_inventee_sans_veto(self):
        for kw in ({'temporal_status':'CONDITIONAL'},{'temporal_status':'HISTORICAL'},
                {'event_class':'CENTRAL_BANK_SPEECH'},{'evidence_quote':'invented evidence not in source'}):
            e=frais();e.http.extraire=lambda q,d,v:dict(v,**kw)
            e.p.collecter();e.p.executer_un();self.assertFalse(e.m.tables['policy_events'])
    def test_heartbeat_reel_ne_prolonge_pas_evenement(self):
        e=frais();e.p.collecter();e.p.executer_un();event=e.p.evenements(e.h.t)[0]
        lecteur=LecteurContexte(charger_parametres(e.r.configuration),PolitiqueVeto(True))
        w=EcrivainSnapshot(e.r,e.m,lambda b:None);a=w.publier(e.h.t,e.p.evenements(e.h.t))
        self.assertTrue(lecteur.recevoir(a.octets,e.h.t).acceptee)
        fin=utc(event['valid_until_utc']);e.h.t=fin-1
        b=w.publier(e.h.t,e.p.evenements(e.h.t));lecteur.recevoir(b.octets,e.h.t)
        self.assertEqual(lecteur.evaluer('EURUSD',e.h.t).etat.value,'BLOCK')
        e.h.t=fin;self.assertFalse(e.p.evenements(e.h.t))
        self.assertEqual(lecteur.evaluer('EURUSD',e.h.t).etat.value,'NEUTRAL')
    def test_reprise_preserve_fenetre_et_annule_file_sans_reinference(self):
        e=frais();e.p.collecter();e.p.executer_un();avant=e.p.evenements(e.h.t);enfiler_note(e)
        nouveau=PlanificateurIA(e.r,e.m,e.rt,e.c,e.h,e.cal);nombre=len(e.http.requetes)
        self.assertFalse(nouveau.reprendre());self.assertIsNone(nouveau.executer_un())
        self.assertEqual(nouveau.evenements(e.h.t),avant);self.assertEqual(len(e.http.requetes),nombre)
    def test_crash_entre_reponse_et_preuve_calendrier_n_invente_pas_veto_passe(self):
        e=frais();e.p.collecter();j=e.rt.en_attente()[0]
        self.assertIsNone(e.rt.executer(j).erreur);self.assertFalse(e.m.tables['policy_events'])
        nouveau=PlanificateurIA(e.r,e.m,e.rt,e.c,e.h,e.cal);nombre=len(e.http.requetes)
        nouveau.reprendre();self.assertIsNone(nouveau.executer_un())
        self.assertFalse(e.m.tables['policy_events']);self.assertEqual(len(e.http.requetes),nombre)
    def test_un_changement_materiel_admis_deux_suspendent_persistant(self):
        for n in (1,2):
            e=auditer(changements=n);pid=e.r.p['providers'][0]['id']
            audit=next(v for k,v in e.m.tables['golden_cases'].items() if k.startswith('audit:'))
            self.assertTrue(audit['complete']);self.assertEqual(audit['changed'],n)
            self.assertEqual(e.m.tables['provider_state']['veto:'+pid]['suspended'],n>1)
            self.assertFalse(e.m.tables['policy_events'])
            nouveau=PlanificateurIA(e.r,e.m,e.rt,e.c,e.h,e.cal,cas_derives=cas_fixes(e.r),routes_auditees=(pid,))
            self.assertEqual(e.m.tables['provider_state']['veto:'+pid]['suspended'],n>1)
    def test_citation_seule_differe_mais_aucune_derive_materielle(self):
        e=auditer(citations=True)
        a=next(v for k,v in e.m.tables['golden_cases'].items() if k.startswith('audit:'))
        self.assertTrue(a['complete']);self.assertEqual(a['changed'],0)
    def test_sortie_invalide_donne_audit_incomplet_pas_stabilite(self):
        e=auditer(extraire=lambda q,d,v:dict(v,item_id='invented') if d['item_id']=='case-0' else v)
        a=next(v for k,v in e.m.tables['golden_cases'].items() if k.startswith('audit:'))
        self.assertFalse(a['complete']);self.assertEqual(a['status'],'INCOMPLETE');self.assertEqual(a['changed'],0)
    def test_quota_atteint_report_au_jour_suivant_sans_fausse_derive(self):
        cs=cas_fixes();e=composer(instant_depuis_iso('2026-11-20T16:20:00Z'),cas=cs);e.http.nouvelles=False
        for i in range(e.r.p['max_api_attempts_per_utc_day']):
            d=decoder(cs[0].dossier);j=JobIA('preload-'+str(i),'GOLDEN',d['item_id'],e.h.t,
                e.h.t+e.r.p['job_deadline_seconds']*1000,cs[0].dossier,fournisseur=e.r.p['providers'][0]['id'])
            self.assertIsNone(e.rt.executer(j).erreur)
            e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
        e.h.t=instant_depuis_iso('2026-11-20T16:44:59Z');e.p.planifier();e.h.t+=1000;e.p.planifier()
        avant=len(e.http.requetes);self.assertEqual(e.p.executer_un().erreur,'AUCUNE_ROUTE_ADMISSIBLE')
        self.assertEqual(len(e.http.requetes),avant)
        e.h.t=instant_depuis_iso('2026-11-21T00:00:00Z')
        self.assertIsNone(e.p.executer_un().erreur)
        audit=next(v for k,v in e.m.tables['golden_cases'].items() if k.startswith('audit:'))
        self.assertTrue(all(v['valid'] for v in audit['results'].values()))
    def test_articles_prioritaires_sur_note_deja_en_attente(self):
        e=frais();note=enfiler_note(e);e.p.collecter();r=e.p.executer_un()
        self.assertNotEqual(r.job_id,note.job_id)
        self.assertEqual([j.job_id for j in e.rt.en_attente()],[note.job_id])
    def test_modele_change_suspend_nouveaux_vetos_et_conserve_notes(self):
        e=frais();e.p.collecter();e.p.executer_un();self.assertEqual(len(e.m.tables['policy_events']),1)
        e.h.t+=e.r.p['provider_min_request_spacing_seconds']*1000
        e.http.modele='synthetic-new-version';enfiler_note(e,'apres');e.p.executer_un()
        pid=e.r.p['providers'][0]['id'];self.assertTrue(e.m.tables['provider_state']['veto:'+pid]['suspended'])
        self.assertIn('apres',e.m.tables['advisories'])
        e.h.t+=e.r.p['rss_poll_seconds']*1000;e.http.d=replace(e.http.d,texte=e.http.d.texte+' A correction.')
        e.p.collecter();e.p.executer_un();self.assertEqual(len(e.m.tables['policy_events']),1)
    def test_prompt_change_exige_qualification_sans_reinferer(self):
        e=frais();prompts=decoder(e.r.prompts);prompts['extraction']+=' Synthetic version change.'
        r=replace(e.r,prompts=canonique(prompts));n=len(e.http.requetes)
        PlanificateurIA(r,e.m,e.rt,e.c,e.h,e.cal)
        self.assertTrue(all(v['suspended'] for k,v in e.m.tables['provider_state'].items() if k.startswith('veto:')))
        self.assertEqual(len(e.http.requetes),n)
