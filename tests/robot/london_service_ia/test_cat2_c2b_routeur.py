"""Catégorie 2 : enveloppes, preuve transmise et registre budgétaire réels."""
import unittest
from dataclasses import replace
from xpbots.service_ia.c0_types import JobIA, canonique, decoder, empreinte, iso, montant
from xpbots.service_ia.c1a_tokens import compter_entree
from xpbots.service_ia.c2b_routeur import RouteurIA
from .support import document, job, extraction
from .support_routeur import composer, timeout
from .support_http import enveloppe


def note(ids=()):return dict(schema_version='fx-advisory-v1',kind='JOURNAL',
    observations=[dict(text='Synthetic fact.',evidence_ids=list(ids))] if ids else [],
    uncertainties=[],hypotheses=[])


class JonctionRouteur(unittest.TestCase):
    def test_reservation_avant_http_corps_complet_usage_et_archives(self):
        r,m,h,http,rt=composer();a=rt.executer(job())
        self.assertIsNone(a.erreur);q=http.requetes[0];archive=next(iter(m.tables['llm_results'].values()))
        self.assertEqual(archive['prompt_hash'],empreinte(r.prompt('EXTRACTION')))
        self.assertEqual(archive['schema_hash'],empreinte(r.schema('EXTRACTION')))
        self.assertEqual(archive['dossier'],decoder(job().dossier))
        self.assertEqual(archive['request'],decoder(q.corps))
        attempt=next(iter(m.tables['api_attempts'].values()))
        self.assertEqual(attempt['input_upper'],compter_entree(r,q.corps))
        self.assertEqual((attempt['actual_input'],attempt['actual_output']),(100,50))
    def test_citation_presente_dans_document_mais_absente_dossier_refusee(self):
        r,m,h,http,rt=composer();d=document();j=job(d,dossier=canonique(dict(item_id=d.item_id,
            title=d.titre,issuer=d.issuer,provided_text='Only this coherent different sentence was sent.')))
        self.assertIsNotNone(rt.executer(j).erreur)
        self.assertTrue(all(a['status']=='KNOWN' for a in m.tables['api_attempts'].values()))
    def test_usage_connu_sortie_incomplete_rapproche_et_inconnu_reste_reserve(self):
        for usage in (True,False):
            r,m,h,http,rt=composer(payant=True);pid=r.p['providers'][-1]['id'];rt.profils={pid:rt.profils[pid]}
            def longueur(q,http):
                v=enveloppe(pid,usage=usage);v.update(status='incomplete')
                return http.reponse(q,corps=canonique(v))
            http.actions=[longueur];self.assertIsNotNone(rt.executer(job()).erreur)
            b=rt.budget.consulter(iso(h.t)[:7])
            self.assertEqual(montant(b['reserved_usd'])==0,usage)
            self.assertEqual(montant(b['spent_usd'])==0,not usage)
    def test_usage_absent_avec_texte_valide_reste_inconnu_au_redemarrage(self):
        r,m,h,http,rt=composer(payant=True);pid=r.p['providers'][-1]['id'];rt.profils={pid:rt.profils[pid]}
        http.actions=[lambda q,http:http.reponse(q,usage=False)]
        self.assertIsNone(rt.executer(job()).erreur)
        nouveau=RouteurIA(r,m,http,h,rt.profils.values())
        self.assertEqual(nouveau.reprendre(),(job().job_id,))
        n=len(http.requetes);nouveau.executer(job());self.assertEqual(len(http.requetes),n)
    def test_depassement_sortie_facturee_desactive_route_et_refuse_resultat(self):
        r,m,h,http,rt=composer(payant=True);pid=r.p['providers'][-1]['id'];rt.profils={pid:rt.profils[pid]}
        def depasse(q,http):
            v=enveloppe(pid);v['usage']['output_tokens']=r.p['max_output_tokens_including_reasoning']+1
            return http.reponse(q,corps=canonique(v))
        http.actions=[depasse];self.assertIsNotNone(rt.executer(job()).erreur)
        self.assertTrue(rt.budget.etat_route(pid)['disabled'])
    def test_reduction_notes_preserve_seulement_preuves_effectivement_envoyees(self):
        for cite_retire in (False,True):
            r,m,h,http,rt=composer();pid=r.p['providers'][0]['id'];rt.profils={pid:rt.profils[pid]}
            docs=[dict(item_id='conserve',provided_text='A coherent source.'),
                dict(item_id='retire',provided_text='x'*r.p['max_input_tokens_upper_bound'])]
            j=JobIA('note','JOURNAL',None,h.t,h.t+75000,canonique(dict(documents=docs)),('conserve','retire'))
            sortie=canonique(note(['retire' if cite_retire else 'conserve'])).decode()
            http.actions=[lambda q,http:http.reponse(q,sortie=sortie)]
            resultat=rt.executer(j)
            self.assertEqual(resultat.valide is None,cite_retire)
            archive=next(iter(m.tables['llm_results'].values()))
            self.assertEqual([d['item_id'] for d in archive['dossier']['documents']],['conserve'])
    def test_texte_trop_long_aucun_appel_ni_troncature(self):
        r,m,h,http,rt=composer();d=document(texte='x'*r.p['max_document_plaintext_bytes'])
        self.assertEqual(rt.executer(job(d)).erreur,'DOSSIER_TROP_LONG')
        self.assertFalse(http.requetes);self.assertFalse(m.tables['api_attempts'])
    def test_memes_profils_reutilises_respectent_espacement_global(self):
        r,m,h,http,rt=composer();a=rt.executer(job());b=rt.executer(replace(job(),job_id='second'))
        self.assertIsNone(a.erreur);self.assertIsNone(b.erreur)
        self.assertNotEqual(a.fournisseur,b.fournisseur)
