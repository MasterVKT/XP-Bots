"""Catégorie 1 : file persistante, délais et erreurs du routeur A08."""
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from email.utils import format_datetime
from xpbots.service_ia.c0_types import ErreurService, ReponseHTTP, canonique, decoder, iso
from xpbots.service_ia.c2b_routeur import RouteurIA
from .support import document, job
from .support_routeur import composer, timeout


class Routeur(unittest.TestCase):
    def test_succes_un_seul_appel_et_resultat_idempotent_partage(self):
        r,m,h,http,rt=composer();j=job();a=rt.executer(j)
        self.assertIsNone(a.erreur);self.assertEqual(rt.executer(j),a)
        self.assertEqual(len(http.requetes),1)
        self.assertEqual(m.tables['llm_jobs'][j.job_id]['status'],'DONE')
    def test_reutilisation_id_autre_dossier_refusee(self):
        r,m,h,http,rt=composer();j=job();rt.enregistrer(j)
        with self.assertRaises(ErreurService):rt.enregistrer(replace(j,dossier=canonique(dict(autre='contenu'))))
    def test_aucun_profil_qualifie_aucun_transport(self):
        r,m,h,http,rt=composer(profils=[])
        self.assertEqual(rt.executer(job()).erreur,'AUCUNE_ROUTE_ADMISSIBLE')
        self.assertEqual(http.requetes,[]);self.assertEqual(m.tables['api_attempts'],{})
    def test_secours_payant_desactive_par_defaut(self):
        r,m,h,http,rt=composer();paid=tuple(p for p in rt.profils.values() if p.projet_dedie)
        rt.budget.provisionner(iso(h.t)[:7],'0','0')
        rt=RouteurIA(r,m,http,h,paid)
        self.assertIsNotNone(rt.executer(job()).erreur);self.assertFalse(http.requetes)
    def test_trois_fournisseurs_distincts_pauses_et_timeout(self):
        r,m,h,http,rt=composer(payant=True,actions=[timeout,timeout])
        a=rt.executer(job());self.assertIsNone(a.erreur)
        self.assertEqual([q.fournisseur for q in http.requetes],[p['id'] for p in r.p['providers']])
        self.assertEqual(h.attentes,[r.p['http_inference_timeout_seconds'],1,r.p['http_inference_timeout_seconds'],2])
        self.assertEqual(len(m.tables['api_attempts']),r.p['max_provider_attempts_per_job'])
    def test_utilite_courte_reduit_timeout_et_interdit_reponse_a_echeance(self):
        def limite(q,http):
            http.h.attendre(q.timeout_s);return http.reponse(q)
        r,m,h,http,rt=composer(actions=[timeout,limite]);t=h.t
        a=rt.executer(job(utile_jusqua_ms=t+22000))
        self.assertIsNotNone(a.erreur);self.assertEqual(len(http.requetes),2)
        self.assertEqual(http.requetes[-1].timeout_s,1);self.assertEqual(h.t,t+22000)
    def test_aucun_fournisseur_rappele_meme_apres_tous_les_echecs(self):
        r,m,h,http,rt=composer(payant=True,actions=[timeout,timeout,timeout])
        self.assertIsNotNone(rt.executer(job()).erreur)
        self.assertEqual(len({q.fournisseur for q in http.requetes}),3)
        n=len(http.requetes);rt.executer(job());self.assertEqual(len(http.requetes),n)
    def test_401_403_json_invalide_desactivent_et_alertent(self):
        for statut in (401,403):
            def refus(q,http):return http.reponse(q,statut=statut,corps=b'not json')
            r,m,h,http,rt=composer(actions=[refus]);a=rt.executer(job())
            self.assertIsNone(a.erreur);pid=r.p['providers'][0]['id']
            self.assertTrue(rt.budget.etat_route(pid)['disabled'])
            self.assertIn('auth:'+pid,m.tables['alerts'])
    def test_retry_after_secondes_et_date_http_persistes(self):
        for date in (False,True):
            r,m,h,http,rt=composer();fin=h.t+600000
            v=format_datetime(datetime.fromtimestamp(fin/1000,timezone.utc),usegmt=True) if date else '600'
            http.actions=[lambda q,http:http.reponse(q,statut=429,corps=b'{}',entetes=(('Retry-After',v),))]
            self.assertIsNone(rt.executer(job()).erreur)
            self.assertEqual(rt.budget.etat_route(r.p['providers'][0]['id'])['not_before_ms'],fin)
    def test_retry_after_hors_representation_ne_devient_pas_zero(self):
        r,m,h,http,rt=composer();pid=r.p['providers'][0]['id']
        http.actions=[lambda q,http:http.reponse(q,statut=429,corps=b'{}',
            entetes=(('Retry-After','9'*100),))]
        rt.executer(job())
        self.assertGreater(rt.budget.etat_route(pid)['not_before_ms'],h.t+600000)
    def test_route_non_admissible_ne_double_pas_pause_du_secours(self):
        r,m,h,http,rt=composer(payant=True,actions=[timeout])
        pid=r.p['providers'][1]['id'];rt.profils[pid]=replace(rt.profils[pid],cle_disponible=False)
        self.assertIsNone(rt.executer(job()).erreur)
        self.assertEqual(h.attentes,[r.p['http_inference_timeout_seconds'],r.p['provider_fallback_delays_seconds'][0]])
    def test_reponse_tardive_archivee_sans_sortie(self):
        def tardif(q,http):
            http.h.attendre(q.timeout_s+1);return http.reponse(q)
        r,m,h,http,rt=composer(actions=[tardif]);rt.profils={r.p['providers'][0]['id']:rt.profils[r.p['providers'][0]['id']]}
        a=rt.executer(job());self.assertIsNotNone(a.erreur)
        archive=next(iter(m.tables['llm_results'].values()))
        self.assertIsNotNone(archive['raw_response']);self.assertIsNone(archive['validated_json'])
    def test_exception_transport_texte_non_journalise(self):
        def inconnu(q,http):raise OSError('SECRET_SYNTHETIQUE_EXCEPTION')
        r,m,h,http,rt=composer(actions=[inconnu]);rt.executer(job())
        self.assertNotIn('SECRET_SYNTHETIQUE_EXCEPTION',canonique(m.tables).decode())
    def test_file_ordonne_annulation_et_expiration_sans_transport(self):
        r,m,h,http,rt=composer();j=job();rt.enregistrer(j)
        self.assertEqual(rt.en_attente(),(j,));self.assertFalse(rt.enregistrer(j))
        self.assertEqual(rt.annuler(j.job_id,'ANNULE').erreur,'ANNULE');self.assertFalse(rt.en_attente())
        h.t=j.utile_jusqua_ms
        self.assertEqual(rt.executer(replace(j,job_id='expire')).erreur,'JOB_EXPIRE')
        self.assertFalse(http.requetes)
    def test_redemarrage_annule_file_et_ne_reinfere_pas_running(self):
        r,m,h,http,rt=composer();a=job();b=replace(a,job_id='queued')
        rt.enregistrer(a);rt.enregistrer(b)
        m.transaction(lambda t:t['llm_jobs'][a.job_id].update(status='RUNNING'))
        nouveau=RouteurIA(r,m,http,h,rt.profils.values())
        self.assertEqual(nouveau.reprendre(),(a.job_id,))
        self.assertEqual(nouveau.executer(a).erreur,'RESULTAT_INCONNU')
        self.assertEqual(nouveau.executer(b).erreur,'REDEMARRAGE_SANS_RATTRAPAGE')
        self.assertFalse(http.requetes)
    def test_reentree_refusee_et_horloge_en_recul(self):
        r,m,h,http,rt=composer()
        def appel(q,http):
            with self.assertRaises(ErreurService):rt.executer(job())
            return http.reponse(q)
        http.actions=[appel];self.assertIsNone(rt.executer(job()).erreur)
        h.t-=1
        with self.assertRaises(ErreurService):rt.executer(replace(job(),job_id='recul'))
