"""Rapports issus du London et du veto archives, sans backends physiques."""
from dataclasses import replace
from datetime import date,time,timedelta
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C,experience_london,experience_courte,fabriques_horloge
from robot.squelette.test_contexte_ia import paquet
from xpbots.rejeu.squelette import SourceSnapshotScenario
from xpbots.rejeu.c2_executeur import ControlesRejeu,executer_experience
from xpbots.rejeu.c3_rapports import rapport_a11,rapport_a13,produire_rapport,serialiser_rapport


class TestJonctionRapports(unittest.TestCase):
    def test_effet_c05_total_distinct_du_calendrier_et_du_llm(self):
        from robot.squelette.test_fondamental import export,permission
        from robot.outils.fondamental import ConversionServeurScenario
        from xpbots.donnees.c0b_sessions import CalendrierLondres
        from xpbots.fondamental.c3_permissions import PermissionsFondamentales
        from xpbots.rejeu.squelette import SourceFondamentaleScenario
        jour=date(2026,7,15);d,source,c,_=experience_london(jour)
        neutre=executer_experience(C,d,source,c,fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        self.assertTrue(neutre.bras['REFERENCE'].trades)
        s=CalendrierLondres.depuis_parametres(C.technique.commun).instant_local(jour,time(8,15))
        def controles(_):
            f=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario())
            return ControlesRejeu(fondamental=f,
                source_fondamentale=SourceFondamentaleScenario(f,(export(s-60000),permission(s-1000,risk_state='NO_NEW'))))
        externe=executer_experience(C,replace(d,identifiant='C05_COMPLET'),source,c,fabrique_controles=controles)
        self.assertFalse(externe.bras['REFERENCE'].trades)
        ligne=produire_rapport((neutre,externe))['effet_fondamental'][0]
        self.assertEqual(ligne['statut_c05_total'],'COMPARABLE')
        self.assertEqual(ligne['difference_pnl_c05_total'],-sum((t.net for t in neutre.bras['REFERENCE'].trades),D(0)))
        self.assertEqual(ligne['perimetre_c05_total'],'PERMISSIONS_ET_ANNONCES')
        self.assertIsNone(ligne['difference_pnl'])
        self.assertEqual(ligne['raison'],'CALENDRIERS_DIFFERENTS_OU_NON_TRACES')
        self.assertEqual(ligne['configurations_brutes_reference'],ligne['configurations_brutes_candidat'])

    def test_vrai_london_axes_et_stop_contraignant(self):
        d,source,c,_=experience_london(date(2026,7,15))
        r=executer_experience(C,d,source,c,fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        self.assertTrue(r.bras['REFERENCE'].trades)
        a=rapport_a11(r)['REFERENCE'];axes={x['axe'] for x in a['ventilations']}
        self.assertEqual(axes,{'W_ATR_H1','premiere_cassure','sens','stop_local','jour_semaine','symbole','scenario_couts'})
        self.assertTrue(any(x['valeur'] for x in a['ventilations'] if x['axe']=='stop_local'))
        self.assertGreater(a['ratio_remplissage'],D(0))
        self.assertIn('NON_VALIDE',serialiser_rapport(produire_rapport((r,))))

    def test_veto_archive_compare_deux_portefeuilles_et_gagnant_bloque(self):
        d,source,c,s,_=experience_courte(mode=C.ia.parametres['default_evaluation_mode'])
        def controle(_):
            n=ControlesRejeu.technique_neutre(C)
            return replace(n,source_ia=SourceSnapshotScenario(n.lecteur_ia,(paquet(s-1000,s+60000),)))
        r=executer_experience(C,d,source,c,fabriques=fabriques_horloge((s,)),fabrique_controles=controle)
        a=rapport_a11(r)['IA'];fin=rapport_a13(r)
        self.assertEqual((a['gagnants_bloques'],a['perdants_bloques']),(1,0))
        self.assertGreater(a['pnl_reference_bloque'],0)
        self.assertEqual(len(fin['reference_effectivement_affectee']),1)
        self.assertEqual(fin['ia']['positions_closes'],0)
        self.assertEqual(fin['statut'],'NON_VALIDE')
        reference=executer_experience(C,replace(d,mode='REJEU'),source,c,
            fabriques=fabriques_horloge((s,)),fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        tableau=produire_rapport((r,),{r.demande.identifiant:reference})['criteres_apriori'][0]
        self.assertEqual(tableau['reference_v1'],'COMPARABLE')

    def test_bootstrap_reel_zero_jours_gardes_sans_v1_inventee(self):
        d,source,c,_=experience_london(date(2026,7,15))
        # La mesure couvre le prechargement connu ; aucun prix supplementaire n'est cree.
        from xpbots.noyau.c0a_temps import instant_vers_datetime
        debut=instant_vers_datetime(source.manifeste.intervalle.debut_ms).date()+timedelta(days=1)
        d=replace(d,bloc=replace(d.bloc,debut=debut))
        r=executer_experience(C,d,source,c,fabrique_controles=lambda _:ControlesRejeu.technique_neutre(C))
        x=produire_rapport((r,))['criteres_apriori'][0]['bras']['REFERENCE']
        self.assertGreaterEqual(x['global_compte']['jours_zero'],5)
        b=x['bootstrap'];self.assertEqual(b['statut'],'CALCULE')
        self.assertEqual(len(b['empreinte_indices']),64)
        self.assertIsNone(b['difference_esperance']);self.assertIsNone(b['gain_incremental'])
