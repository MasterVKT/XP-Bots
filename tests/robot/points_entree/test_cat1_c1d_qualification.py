"""Lectures C04 réelles contre le seul faux terminal externe."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest

from robot.outils.orchestration import C
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.qualification_mt5 import T
from robot.outils.assemblage_mt5 import parametres,installer_controles
from robot.points_entree.test_cat1_c0_configuration import registre
from xpbots.app.c0_configuration import analyser_registre
from xpbots.app.c1d_cli_qualification import qualifier
from xpbots.infra.c4_assemblage import InfrastructurePhysique
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2c_calculs import CalculsMT5


class HarnaisQualification:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        p=patch('time.time_ns',return_value=T*1000000);p.start();self.addCleanup(p.stop)
        self.sdk=FauxMT5(self.root,instant_ms=T)
        d=registre('DEMO');d['chemins']['racine']=str(self.root)
        self.app=analyser_registre(d,C,T,qualification=True)
        self.infra=InfrastructurePhysique(C.technique.commun,self.app.meta,self.app.liaisons,
            racine=self.root,max_octets_echange=self.app.ingenierie['max_octets_echange'],
            snapshot_max_octets=C.ia.parametres['snapshot_max_bytes'],sdk=self.sdk)
        self.addCleanup(lambda:self.infra.fermer(0))
        self.table,self.q,_=parametres(self.sdk)


class TestQualificationApplication(HarnaisQualification,unittest.TestCase):
    def test_lectures_c04_completes_sans_champ_sensible_ni_ordre(self):
        installer_controles(self.infra.session.etat.common_files)
        r=qualifier(self.app,self.infra,self.table,self.q)
        self.assertEqual(r['conclusion'],'LECTURES_C04_COMPLETES')
        self.assertEqual(r['type_compte_natif'],'DEMO')
        self.assertEqual(r['compte']['devise'],C.technique.commun.account_currency)
        self.assertEqual(r['instruments']['EURUSD']['profil']['devise_marge'],'EUR')
        self.assertFalse(r['autorisation_execution']);self.assertEqual(r['validation_financiere'],'NON_EVALUEE')
        texte=json.dumps(r)
        for champ in ('login','password','solde','balance','common_files'):
            self.assertNotIn('"'+champ+'"',texte)
        self.assertNotIn(str(self.root),texte)
        self.assertEqual(self.infra.depot.dernier_numero,0)
        self.assertFalse(any(n in ('order_send','order_check') for n,*_ in self.sdk.appels))

    def test_exports_absents_et_preuve_expiree_refuses_sans_frais_inventes(self):
        r=qualifier(self.app,self.infra,self.table,self.q)
        self.assertEqual(r['conclusion'],'ENVIRONMENT_NOT_READY')
        self.assertIn('EXPORTS_D12_NON_PRETS',r['environnement_non_pret'])
        self.assertIsNone(r['instruments']['EURUSD']['profil'])
        self.assertEqual(r['faisabilite_volume_minimal']['statut'],'NON_EVALUABLE_SANS_SIGNAL_C06')

    def test_sondes_non_executees_ne_deviennent_pas_des_preuves(self):
        installer_controles(self.infra.session.etat.common_files)
        r=qualifier(self.app,self.infra,self.table,self.q)
        self.assertEqual(r['sondes']['S01']['statut'],'TABLE_EXTERNE_DECLAREE')
        self.assertEqual(r['sondes']['S08']['statut'],'PREUVE_EXTERNE_DECLAREE')
        self.assertEqual(r['sondes']['S07']['statut'],'NON_EXECUTEE_SANS_SCENARIO_DATE')
        self.assertTrue(all(r['sondes'][n]['statut']=='A_CONFRONTER_13_1' for n in ('S02','S03','S04','S05','S06')))

    def test_qualification_expiree_ne_valide_pas_s08(self):
        q=deepcopy(self.q);q['valid_until_utc_ms']=T
        r=qualifier(self.app,self.infra,self.table,q)
        self.assertEqual(r['conclusion'],'ENVIRONMENT_NOT_READY')
        self.assertEqual(r['sondes']['S08']['statut'],'PREUVE_ABSENTE_OU_INVALIDE')
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_message_natif_prive_non_restitue_apres_erreur_de_lecture(self):
        installer_controles(self.infra.session.etat.common_files)
        self.sdk.scenarios['account_info'].append(None)
        self.sdk.erreur=(self.sdk.RES_E_FAIL,'TEXTE_PRIVE_DU_SDK_INTERDIT_DANS_LE_RAPPORT')
        r=qualifier(self.app,self.infra,self.table,self.q)
        self.assertIn('ETAT_SESSION_ILLISIBLE',r['environnement_non_pret'])
        self.assertNotIn('TEXTE_PRIVE_DU_SDK',json.dumps(r))
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
