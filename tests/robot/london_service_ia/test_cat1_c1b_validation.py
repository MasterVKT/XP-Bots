"""Catégorie 1, couche 1b : schémas, preuves et limites exactes A05/A11."""
from copy import deepcopy
import unittest
from xpbots.service_ia.c0_types import ErreurService, canonique
from xpbots.service_ia.c1b_validation import valider_extraction, valider_note
from .support import ressources, document, extraction

def note(kind='JOURNAL'):
    return dict(schema_version='fx-advisory-v1',kind=kind,
        observations=[dict(text='Evidence remains limited.',evidence_ids=['e1'])],
        uncertainties=['Synthetic coverage.'],hypotheses=[])

def sortie(v):return canonique(v).decode('utf-8')

class ValidationSorties(unittest.TestCase):
    def setUp(self):self.r=ressources();self.d=document();self.item=self.d.item(self.d.texte)

    def test_extraction_nominale_vide_historique_et_conditionnelle(self):
        for changements in ({},{'evidence_quote':''},{'temporal_status':'HISTORICAL'},
                             {'temporal_status':'CONDITIONAL'},{'event_class':'UNCLEAR'}):
            with self.subTest(changements=changements):
                v=extraction(self.d,**changements)
                self.assertEqual(valider_extraction(self.r,sortie(v),self.item),v)

    def test_extraction_refuse_cles_types_enums_et_item(self):
        v=extraction(self.d)
        mauvais=[]
        for cle in v:
            a=deepcopy(v);del a[cle];mauvais.append(a)
            a=deepcopy(v);a[cle]=None;mauvais.append(a)
        mauvais += [dict(v,extra='order'),dict(v,item_id='autre'),dict(v,event_class='ORDER'),
            dict(v,temporal_status='FUTURE'),dict(v,policy_actor='UNKNOWN'),dict(v,stance='BUY')]
        for a in mauvais:
            with self.subTest(a=a),self.assertRaises(ErreurService):valider_extraction(self.r,sortie(a),self.item)

    def test_json_duplique_tronque_non_fini_et_non_objet(self):
        s=sortie(extraction(self.d))
        for mauvais in (s[:-1],s[:-1]+',"item_id":"article-synthetique"}',
                        '[]','null','{"x":NaN}','{"x":1e999}','',s+' trailing'):
            with self.subTest(mauvais=mauvais[:40]),self.assertRaises(ErreurService):
                valider_extraction(self.r,mauvais,self.item)

    def test_citation_uniquement_dans_texte_reellement_fourni(self):
        v=extraction(self.d)
        with self.assertRaises(ErreurService):valider_extraction(self.r,sortie(v),dict(self.item,provided_text='Different excerpt.'))
        with self.assertRaises(ErreurService):valider_extraction(self.r,sortie(dict(v,evidence_quote='invented quote')),self.item)
        n=self.r.p['evidence_quote_max_characters'];item=dict(self.item,provided_text='é'*(n+1))
        self.assertEqual(valider_extraction(self.r,sortie(dict(v,evidence_quote='é'*n)),item)['evidence_quote'],'é'*n)
        with self.assertRaises(ErreurService):valider_extraction(self.r,sortie(dict(v,evidence_quote='é'*(n+1))),item)

    def test_taille_reponse_inclusive(self):
        s=sortie(extraction(self.d));n=self.r.p['max_response_bytes']-len(s.encode('utf-8'))
        self.assertEqual(valider_extraction(self.r,s+' '*n,self.item),extraction(self.d))
        with self.assertRaises(ErreurService):valider_extraction(self.r,s+' '*(n+1),self.item)

    def test_notes_nominales_et_hypotheses_bornees(self):
        for kind in ('BRIEFING','JOURNAL','WEEKLY_REVIEW'):
            v=note(kind)
            if kind!='BRIEFING':v['hypotheses']=[dict(statement='Check a fixed hypothesis.',validation_plan='Offline causal replay.')]
            self.assertEqual(valider_note(self.r,sortie(v),kind,('e1',)),v)

    def test_listes_et_textes_aux_bornes(self):
        p=self.r.p;n=p['advisory_max_text_characters'];v=note()
        v['observations']=[dict(text='é'*n,evidence_ids=['e1']*p['advisory_max_evidence_ids_per_observation'])]*p['advisory_max_observations']
        v['uncertainties']=['x'*n]*p['advisory_max_uncertainties']
        v['hypotheses']=[dict(statement='x'*n,validation_plan='x'*n)]*p['advisory_max_hypotheses']
        self.assertEqual(valider_note(self.r,sortie(v),'JOURNAL',('e1',)),v)
        for champ in ('observations','uncertainties','hypotheses'):
            a=deepcopy(v);a[champ].append(a[champ][0])
            with self.subTest(champ=champ),self.assertRaises(ErreurService):valider_note(self.r,sortie(a),'JOURNAL',('e1',))
        for cible in ('observation','uncertainty','statement','validation_plan'):
            a=deepcopy(v)
            if cible=='observation':a['observations'][0]['text']+='x'
            elif cible=='uncertainty':a['uncertainties'][0]+='x'
            else:a['hypotheses'][0][cible]+='x'
            with self.subTest(cible=cible),self.assertRaises(ErreurService):valider_note(self.r,sortie(a),'JOURNAL',('e1',))

    def test_notes_refuse_preuves_etrangeres_et_champs(self):
        v=note();mauvais=[dict(v,extra=True),dict(v,kind='BRIEFING'),dict(v,observations={}),
            dict(v,uncertainties=[False]),dict(v,hypotheses=[{'statement':'x','validation_plan':'y','order':'BUY'}])]
        for ids in ([],['invented'],['e1']*(self.r.p['advisory_max_evidence_ids_per_observation']+1),[True]):
            a=deepcopy(v);a['observations'][0]['evidence_ids']=ids;mauvais.append(a)
        for a in mauvais:
            with self.subTest(a=a),self.assertRaises(ErreurService):valider_note(self.r,sortie(a),'JOURNAL',('e1',))
        with self.assertRaises(ErreurService):valider_note(self.r,sortie(dict(note('BRIEFING'),hypotheses=[dict(statement='x',validation_plan='y')])),'BRIEFING',('e1',))

    def test_doublon_imbrique_et_sortie_note_trop_longue(self):
        s=sortie(note())
        a=s.replace('"text":"Evidence remains limited."','"text":"Evidence remains limited.","text":"again"')
        with self.assertRaises(ErreurService):valider_note(self.r,a,'JOURNAL',('e1',))
        n=self.r.p['max_response_bytes']-len(s.encode('utf-8'))
        self.assertEqual(valider_note(self.r,s+' '*n,'JOURNAL',('e1',)),note())
        with self.assertRaises(ErreurService):valider_note(self.r,s+' '*(n+1),'JOURNAL',('e1',))
