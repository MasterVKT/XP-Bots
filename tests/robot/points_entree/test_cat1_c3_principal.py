"""Interface opérateur réelle, fichiers temporaires et erreurs sans données privées."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from unittest.mock import patch
from xpbots.app.c3_principal import main
from robot.outils.orchestration import C
from robot.points_entree.test_cat1_c0_configuration import registre
from robot.outils.qualification_mt5 import iso,T

RACINE=Path(__file__).resolve().parents[3]


def appeler(arguments,*,sdk=None,racine=RACINE):
    sortie=StringIO();erreur=StringIO()
    with redirect_stdout(sortie),redirect_stderr(erreur):
        code=main(['--racine-depot',str(racine),*map(str,arguments)],sdk=sdk)
    return code,sortie.getvalue(),erreur.getvalue()


class TestPrincipal(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_aide_et_arguments_inconnus_ne_chargent_pas_sdk_ni_valeur_privee(self):
        with patch('importlib.import_module',side_effect=AssertionError('IMPORT_EXTERNE_INTERDIT')):
            code,s,_=appeler(['--help']);self.assertEqual(code,0)
            for nom in ('gabarits','parametres-export','qualifier','direct','rejeu','rapports','incident','geler-code'):
                self.assertIn(nom,s)
            code,s,e=appeler(['gabarits','--password','VALEUR_PRIVEE_FIXTURE'])
            self.assertEqual(code,2);self.assertNotIn('VALEUR_PRIVEE_FIXTURE',s+e)

    def test_gabarits_reels_refus_d_ecrasement_et_option_explicite(self):
        r=self.root/'registre.json';f=self.root/'fermetures.json'
        args=['gabarits','--sortie-registre',r,'--sortie-fermetures',f]
        self.assertEqual(appeler(args)[0],0)
        d=json.loads(r.read_bytes());self.assertEqual(d['mode'],C.ia.parametres['default_evaluation_mode'])
        self.assertEqual(d['empreintes']['technique'],C.technique.empreinte_octets)
        avant=r.read_bytes();self.assertEqual(appeler(args)[0],2);self.assertEqual(r.read_bytes(),avant)
        self.assertEqual(appeler([*args,'--ecraser'])[0],0)
        self.assertEqual(json.loads(f.read_bytes())['schema'],'xp-fermetures-v1')

    def test_env_refuse_et_plafond_technique_invalide(self):
        r=self.root/'r.json';f=self.root/'f.json'
        code,s,_=appeler(['--max-octets-document','0','gabarits','--sortie-registre',r,'--sortie-fermetures',f])
        self.assertEqual(code,2);self.assertEqual(json.loads(s)['code'],'PLAFOND_DOCUMENT_INVALIDE')
        code,s,_=appeler(['gabarits','--sortie-registre',self.root/'.env','--sortie-fermetures',f])
        self.assertEqual(code,2);self.assertEqual(json.loads(s)['code'],'FICHIER_ENV_INTERDIT')
        self.assertFalse((self.root/'.env').exists())

    def test_un_autre_arbre_ne_prouve_pas_le_gel_du_principal_charge(self):
        for nom in ('config','docs/validation','src/xpbots','mql5','schemas','prompts'):(self.root/nom).mkdir(parents=True)
        for nom in ('config/parametres_figes_v3.json','config/parametres_IA_integration_v1.json','docs/validation/conservation_ressources.json'):
            (self.root/nom).write_bytes((RACINE/nom).read_bytes())
        r=self.root/'registre.json';r.write_text(json.dumps(registre()),encoding='utf-8')
        code,s,_=appeler(['geler-code','--registre',r,'--sortie',self.root/'gel.json'],racine=self.root)
        self.assertEqual(code,2);self.assertEqual(json.loads(s)['code'],'CHEMIN_HORS_RACINE')
        self.assertFalse((self.root/'gel.json').exists())
