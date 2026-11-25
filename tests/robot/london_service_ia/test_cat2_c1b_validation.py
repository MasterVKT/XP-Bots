"""Catégorie 2, couche 1b : égalité réelle des deux validateurs et des oracles."""
from copy import deepcopy
import unittest
from reference.llm_contracts import parse_model_output, parse_advisory_output
from xpbots.service_ia.c1b_validation import valider_extraction, valider_note
from .support import ressources, document, extraction
from .test_cat1_c1b_validation import note, sortie

class JonctionValidation(unittest.TestCase):
    def test_extractions_egales_aux_oracles(self):
        r=ressources();d=document();item=d.item(d.texte)
        for champ,enum in r.schema('EXTRACTION')['properties'].items():
            for valeur in enum.get('enum',[]):
                with self.subTest(champ=champ,valeur=valeur):
                    s=sortie(dict(extraction(d),**{champ:valeur}))
                    self.assertEqual(valider_extraction(r,s,item),parse_model_output(s,item))

    def test_extractions_meme_refus_sur_defauts(self):
        r=ressources();d=document();item=d.item(d.texte);v=extraction(d)
        cas=[sortie(dict(v,evidence_quote='Quotation absent from this supplied document.')),sortie(dict(v,item_id='foreign')),
            sortie(dict(v,extra='x')),sortie(dict(v,stance='BUY')),sortie(v)[:-1],
            sortie(v)[:-1]+',"stance":"EASING"}']
        for s in cas:
            with self.subTest(sortie=s[:30]):
                with self.assertRaises(ValueError):parse_model_output(s,item)
                with self.assertRaises(ValueError):valider_extraction(r,s,item)

    def test_notes_egales_aux_oracles(self):
        r=ressources()
        for kind in ('BRIEFING','JOURNAL','WEEKLY_REVIEW'):
            for vide in (False,True):
                v=note(kind)
                if vide:v.update(observations=[],uncertainties=[])
                s=sortie(v)
                self.assertEqual(valider_note(r,s,kind,('e1',)),parse_advisory_output(s,kind,('e1',)))

    def test_notes_meme_refus_sur_defauts(self):
        r=ressources();v=note();cas=[]
        for cle in v:
            a=deepcopy(v);del a[cle];cas.append(sortie(a))
        a=deepcopy(v);a['observations'][0]['evidence_ids']=['foreign'];cas.append(sortie(a))
        cas += [sortie(dict(v,kind='BRIEFING')),sortie(dict(v,uncertainties=['x'*(r.p['advisory_max_text_characters']+1)]))]
        for s in cas:
            with self.subTest(sortie=s[:30]):
                with self.assertRaises(ValueError):parse_advisory_output(s,'JOURNAL',('e1',))
                with self.assertRaises(ValueError):valider_note(r,s,'JOURNAL',('e1',))
