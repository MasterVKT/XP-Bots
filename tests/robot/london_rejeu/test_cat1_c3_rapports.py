"""Les verdicts exigent leurs preuves ; les nombres restent inspectables."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import json
import unittest
from robot.outils.rejeu import C,experience_courte,fabriques_horloge
from xpbots.rejeu.c0a_types import ErreurRejeu,FactureIA
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c2_executeur import ControlesRejeu,executer_experience,executer_perturbations
from xpbots.rejeu.c3_rapports import (PreuvesValidation,QualificationSemantique,
    ObservationCoutDemo,produire_rapport,rapport_a13,comparer_routes,comparer_couts_demo,serialiser_rapport)
from xpbots.rejeu.c3_rapports._impl import _critere,_qualification_semantique


def cas(**options):
    d,source,c,s,_=experience_courte(**options)
    return executer_experience(C,d,source,c,fabriques=fabriques_horloge((s,)),
        fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))


class TestRapports(unittest.TestCase):
    def test_retention_a13_conditionnelle_ne_masque_aucun_autre_echec(self):
        from xpbots.rejeu.c3_rapports import Critere
        from xpbots.rejeu.c3_rapports import _impl
        gain=Critere('gain',D(1),D(0),'>','SATISFAIT')
        na=Critere('retention:LONDON_V3:GBPUSD',None,D('.8'),'>=','NON_EVALUABLE','N_A')
        faible=replace(na,raison='TROP_FAIBLE')
        self.assertTrue(_impl._criteres_a13_satisfaits((gain,na,faible)))
        self.assertFalse(_impl._criteres_a13_satisfaits((gain,replace(na,nom='jours_marche'))))
        self.assertFalse(_impl._criteres_a13_satisfaits((gain,replace(na,statut='ECHEC',raison='EXPLOITABLE'))))
        self.assertFalse(_impl._criteres_a13_satisfaits(()))
    @classmethod
    def setUpClass(cls):cls.r=cas()

    def test_limites_exactes_et_inconnues(self):
        seuil=charger_protocole(C).seuils.profit_factor_reference
        self.assertEqual(_critere('pf',seuil,seuil,'>=').statut,'SATISFAIT')
        self.assertEqual(_critere('e',D(0),D(0),'>').statut,'ECHEC')
        self.assertEqual(_critere('dd',D('.1'),D('.1'),'<=').statut,'SATISFAIT')
        self.assertEqual(_critere('r',None,D('.8'),'>=').statut,'NON_EVALUABLE')
        with self.assertRaises(ErreurRejeu):_critere('x',1,1,'~=')

    def test_sept_mesures_et_pnl_calcules_a_la_main(self):
        r=self.r;t=r.bras['REFERENCE'].trades[0]
        m=produire_rapport((r,))['criteres_apriori'][0]['bras']['REFERENCE']['global_compte']
        self.assertEqual(tuple(m[k] for k in ('configurations','signaux','entrees','positions_closes')),(1,1,1,1))
        self.assertEqual(m['resultats_nets'],(t.net,))
        self.assertEqual(m['pnl_courtier'],(t.prix_sortie-t.prix_entree)*D(1000)*t.volume)
        self.assertEqual(m['esperance'],t.net);self.assertEqual(m['r_moyen_net'],t.r_net)
        self.assertEqual(m['taux_reussite'],D(1));self.assertEqual(m['refus'],{})

    def test_v1_absente_na_et_reference_petitesse_explicitement_distinctes(self):
        rapport=produire_rapport((self.r,));x=rapport['criteres_apriori'][0]
        self.assertEqual(x['reference_v1'],'N_A')
        ratio=x['bras']['REFERENCE']['retentions'][0]['transactions']
        self.assertIsNone(ratio.ratio)
        comparable=produire_rapport((self.r,),{self.r.demande.identifiant:self.r})['criteres_apriori'][0]
        self.assertEqual(comparable['reference_v1'],'COMPARABLE')
        faible=comparable['bras']['REFERENCE']['retentions'][0]['transactions']
        self.assertEqual((faible.ratio,faible.statut),(D(1),'TROP_FAIBLE'))

    def test_comparabilite_rejette_absence_conditions_et_frais_changes(self):
        for ancien in (replace(self.r,conditions=()),replace(self.r,conditions=(replace(self.r.conditions[0],
            tarif=replace(self.r.conditions[0].tarif,identifiant='AUTRE')),))):
            x=produire_rapport((self.r,),{self.r.demande.identifiant:ancien})['criteres_apriori'][0]
            self.assertEqual(x['reference_v1'],'NON_COMPARABLE')
            self.assertIn('CONDITIONS_CONTRACTUELLES',x['raison_reference'])

    def test_un_hash_ne_vaut_pas_attestation_et_bool_strict(self):
        self.assertFalse(PreuvesValidation(fiche_c04='a'*64).attestee('fiche_c04'))
        for valeur in (1,None,False):
            self.assertFalse(PreuvesValidation(fiche_c04='a'*64,verifier=lambda *_:valeur).attestee('fiche_c04'))
        self.assertTrue(PreuvesValidation(fiche_c04='a'*64,verifier=lambda *_:True).attestee('fiche_c04'))
        with self.assertRaises(ErreurRejeu):PreuvesValidation(gel_robot='pas_un_hash')

    def test_fixture_ne_devient_jamais_qualification_financiere(self):
        preuves=PreuvesValidation(*('a'*64,)*4,verifier=lambda *_:True)
        rapport=produire_rapport((self.r,),{self.r.demande.identifiant:self.r},preuves)
        self.assertEqual(rapport['statut'],'NON_VALIDE')
        self.assertIn('DONNEES_SYNTHETIQUES_CONTREFACTUELLES_OU_INCOMPLETES',rapport['limites'])
        self.assertIn('MATRICE_C05_EXTERNE_INCOMPLETE',rapport['limites'])
        self.assertFalse(rapport['matrice_c10']['fondamental_complet'])
        self.assertEqual(rapport['comparaison_demo'][0]['rapport']['statut'],'PREUVE_MANQUANTE')
        with self.assertRaises(TypeError):rapport['statut']='VALIDE'

    def test_qualification_semantique_humaine_et_seuils_exactes(self):
        p=C.ia.parametres
        q=QualificationSemantique(p['providers'][0]['id'],'b'*64,True,p['model_classification_test_items'],
            D(str(p['model_min_material_event_precision'])),D(str(p['model_min_material_event_recall'])),0)
        self.assertEqual(_qualification_semantique(q,C)['statut'],'QUALIFIE_DECLARE')
        for autre in (replace(q,humain=False),replace(q,nombre_textes=q.nombre_textes-1),
            replace(q,precision=q.precision-D('.0001')),replace(q,citations_non_verifiees=1)):
            self.assertEqual(_qualification_semantique(autre,C)['statut'],'NON_QUALIFIE')
        with self.assertRaises(ErreurRejeu):replace(q,precision=D('NaN'))

    def test_demo_observee_ne_remplace_pas_les_hypotheses(self):
        o=ObservationCoutDemo('fill1','ENTREE','EURUSD',275,D(2),D('.00012'),D('.03'))
        x=comparer_couts_demo(self.r,(o,));self.assertEqual(x['statut'],'PREUVE_MANQUANTE')
        x=comparer_couts_demo(self.r,(o,),PreuvesValidation(journaux_demo='c'*64,verifier=lambda *_:True))
        self.assertEqual(x['statut'],'OBSERVATIONS_ATTESTEES')
        self.assertEqual(x['observations'][0]['delai_ms']['moyenne'],D(275))
        self.assertEqual(x['hypotheses'],charger_protocole(C).scenarios)
        with self.assertRaises(ErreurRejeu):comparer_couts_demo(self.r,(o,o))

    def test_comparaison_routes_bornes_et_annotateur_masque(self):
        p=C.ia.parametres
        q=QualificationSemantique(p['providers'][0]['id'],'b'*64,True,200,D('.95'),D('.80'),0)
        a=replace(q,fournisseur=p['providers'][-1]['id'],precision=D('.97'),rappel=D('.85'))
        options=dict(dossiers='b'*64,prompt='c'*64,regles='d'*64,provenance_masquee=True,attester=lambda *_:True)
        self.assertEqual(comparer_routes(q,a,C,**options)['statut'],'ECARTS_ADMISSIBLES_OBSERVES')
        self.assertEqual(comparer_routes(q,replace(a,precision=D('.97001')),C,**options)['statut'],'ROUTES_NON_EQUIVALENTES')
        options['provenance_masquee']=False
        self.assertEqual(comparer_routes(q,a,C,**options)['statut'],'NON_EVALUABLE')

    def test_comparaison_routes_exige_meme_corpus_effectif_et_routes_distinctes(self):
        p=C.ia.parametres
        q=QualificationSemantique(p['providers'][0]['id'],'b'*64,True,200,D('.95'),D('.80'),0)
        a=replace(q,fournisseur=p['providers'][-1]['id'])
        options=dict(dossiers='b'*64,prompt='c'*64,regles='d'*64,provenance_masquee=True,attester=lambda *_:True)
        for autre in (replace(a,empreinte_corpus='e'*64),replace(a,nombre_textes=201),q):
            self.assertEqual(comparer_routes(q,autre,C,**options)['statut'],'NON_EVALUABLE')

    def test_matrice_c10_ne_qualifie_pas_un_simple_sous_bloc(self):
        rapport=produire_rapport((self.r,))
        # 3 blocs x 2 couts x 3 perimetres, plus 2 continus : aucun n'est entier ici.
        self.assertEqual(len(rapport['matrice_c10']['manquants']),20)

    def test_six_voisins_de_contextes_differents_pas_un_groupe_complet(self):
        d,source,c,s,_=experience_courte(perte=True)
        rs=executer_perturbations(C,d,source,c,fabriques=fabriques_horloge((s,)),
            fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        heterogenes=tuple(replace(r,demande=replace(r.demande,scenario='STRESS')) if i%2 else r
            for i,r in enumerate(rs))
        x=produire_rapport(heterogenes)['voisinage']
        self.assertFalse(x['complet']);self.assertEqual(len(x['experiences']),6)

    def test_factures_origines_reconciliees_une_fois_et_cout_seulement_ia(self):
        r=cas(mode=C.ia.parametres['default_evaluation_mode'])
        f=FactureIA('appel',r.debut_effectif_ms,D('.06'),('LONDON_V3','EMA_V3'),'EVENEMENT',False)
        recherche=FactureIA('recherche',r.debut_effectif_ms,D('.02'),('LONDON_V3',),'RECHERCHE',False)
        r=replace(r,factures=(f,recherche))
        autre=replace(r,demande=replace(r.demande,identifiant='AUTRE'))
        x=produire_rapport((r,autre));b=x['criteres_apriori'][0]['bras']
        self.assertEqual(x['bilan_couts_projet']['cout_ia_total'],D('.08'))
        self.assertEqual(x['bilan_couts_projet']['depenses_recherche'],D('.02'))
        self.assertEqual(b['REFERENCE']['global_compte']['cout_ia'],D(0))
        self.assertEqual(b['IA']['global_compte']['cout_ia'],D('.08'))
        self.assertEqual(b['IA']['par_methode_symbole'][0]['mesures']['cout_ia'],None)

    def test_rapport_incomplet_conserve_pertes_et_arrets_des_six_voisins(self):
        d,source,c,s,_=experience_courte(perte=True)
        rs=executer_perturbations(C,d,source,c,fabriques=fabriques_horloge((s,)),
            fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        rapport=produire_rapport(rs);v=rapport['voisinage']
        self.assertTrue(v['complet']);self.assertFalse(v['selection_nouveau_reglage'])
        self.assertEqual(len(v['experiences']),6)
        self.assertTrue(all(x['pnl']<0 and x['pertes']==1 for x in v['experiences']))
        self.assertTrue(all('arrets_globaux' in x and 'arrets_quotidiens' in x for x in v['experiences']))
        self.assertEqual(rapport['statut'],'NON_VALIDE')

    def test_serialisation_exacte_stable_et_refus_non_finis(self):
        v={'z':D('0.00000000000000000000000001'),'a':date(2023,1,2)}
        self.assertEqual(serialiser_rapport(v),'\x7b"a":"2023-01-02","z":"1E-26"\x7d')
        for x in (float('nan'),float('inf'),D('-Infinity'),lambda:1):
            with self.assertRaises(ErreurRejeu):serialiser_rapport({'x':x})
        with self.assertRaises(ErreurRejeu):serialiser_rapport({1:'x'})
        rapport=produire_rapport((self.r,))
        self.assertEqual(json.loads(serialiser_rapport(rapport))['statut'],'NON_VALIDE')

    def test_a13_refuse_simulation_unique_et_aucune_perte_retiree(self):
        self.assertEqual(rapport_a13(self.r)['statut'],'NON_EVALUABLE')
        r=cas(mode=C.ia.parametres['default_evaluation_mode'])
        x=rapport_a13(r)
        self.assertEqual(x['reference_effectivement_affectee'],())
        self.assertEqual(x['statut'],'NON_VALIDE')
        self.assertEqual(x['reference']['pnl_courtier'],x['ia']['pnl_courtier'])
        self.assertEqual(next(c for c in x['criteres'] if c.nom=='permissions_externes_presentes').statut,'ECHEC')

    def test_a13_absence_facture_pas_consommation_reelle_nulle(self):
        r=cas(mode=C.ia.parametres['default_evaluation_mode'])
        p=PreuvesValidation(*('a'*64,)*4,verifier=lambda *_:True)
        criteres={c.nom:c for c in rapport_a13(r,preuves=p)['criteres']}
        self.assertEqual(criteres['couts_ia_reels_documentes'].statut,'ECHEC')
        f=FactureIA('gratuit_zero_explicitement_documente',r.debut_effectif_ms,D(0),('LONDON_V3',),'EVENEMENT',True)
        criteres={c.nom:c for c in rapport_a13(replace(r,factures=(f,)),preuves=p)['criteres']}
        self.assertEqual(criteres['couts_ia_reels_documentes'].statut,'SATISFAIT')
        p=replace(p,verifier=lambda nature,h:nature!='validation_c10')
        criteres={c.nom:c for c in rapport_a13(replace(r,factures=(f,)),preuves=p)['criteres']}
        self.assertEqual(criteres['maintien_c10_sous_gel_atteste'].statut,'ECHEC')

    def test_a13_cout_hors_periode_ou_recherche_pas_preuve_consommation(self):
        r=cas(mode=C.ia.parametres['default_evaluation_mode'])
        f=FactureIA('autre_periode',r.debut_effectif_ms-1,D(0),('LONDON_V3',),'EVENEMENT',True)
        for facture in (f,replace(f,instant_ms=r.debut_effectif_ms,nature='RECHERCHE')):
            x=rapport_a13(replace(r,factures=(facture,)))
            critere=next(c for c in x['criteres'] if c.nom=='couts_ia_reels_documentes')
            self.assertEqual(critere.statut,'ECHEC')

    def test_experiences_chevauchantes_pas_effectifs_additionnes(self):
        autre=replace(self.r,demande=replace(self.r.demande,identifiant='AUTRE'))
        rapport=produire_rapport((self.r,autre))
        self.assertTrue(all(c.observe is None for c in rapport['effectifs_globaux'][0]['criteres'] if c.nom.startswith('trades_')))
        with self.assertRaises(ErreurRejeu):produire_rapport((self.r,self.r))
        externe=replace(autre,regime_fondamental='PERMISSIONS_EXTERNES')
        effectifs=produire_rapport((self.r,externe))['effectifs_globaux']
        self.assertEqual(len(effectifs),2)
        self.assertEqual({e['regime_fondamental'] for e in effectifs},
            {'TECHNICAL_CONTROL_NEUTRAL','PERMISSIONS_EXTERNES'})
