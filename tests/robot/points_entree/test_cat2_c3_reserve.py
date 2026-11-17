"""Vraies invocations de la copie du runtime ; gel et verrou survivent au processus."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip,json,os,shutil,subprocess,sys,unittest

from robot.outils.qualification_mt5 import T
from robot.points_entree.test_cat1_c0_configuration import registre
from robot.points_entree.test_cat1_c1c_rejeu import demande_fixture
from xpbots.app.c1c_cli_rejeu import encoder_rejeu
from xpbots.infra.c0h_verrou import VerrouProcessus

RACINE=Path(__file__).resolve().parents[3]


class TestReserveEntreProcessus(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        for nom in ('src/xpbots','mql5','config','schemas','prompts'):
            shutil.copytree(RACINE/nom,self.root/nom,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        conservation=self.root/'docs/validation/conservation_ressources.json'
        conservation.parent.mkdir(parents=True)
        conservation.write_bytes((RACINE/'docs/validation/conservation_ressources.json').read_bytes())
        garde=self.root/'garde';garde.mkdir()
        # Horloge externe déterministe et refus d'importer le SDK, même pour --help.
        (garde/'sitecustomize.py').write_text(
            'import sys,time,importlib.abc\n'
            f'time.time_ns=lambda: {T}*1000000\n'
            'class SansSDK(importlib.abc.MetaPathFinder):\n'
            ' def find_spec(self,fullname,path=None,target=None):\n'
            '  if fullname=="MetaTrader5" or fullname.startswith("MetaTrader5."):\n'
            '   raise RuntimeError("SDK_INTERDIT_DANS_CET_ESSAI")\n'
            'sys.meta_path.insert(0,SansSDK())\n',encoding='utf-8')
        self.env=os.environ.copy()
        self.env.update(PYTHONPATH=os.pathsep.join((str(garde),str(self.root/'src'))),
            PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
            XPBOTS_CONTRATS_MT5='0',XPBOTS_CONTRATS_API='0')
        self.registre=self.root/'registre.json'
        self.registre.write_text(json.dumps(registre()),encoding='utf-8')
        d,lignes=demande_fixture(jour=date(2025,1,2))
        self.demande=self.root/'demande.json';self.demande.write_bytes(encoder_rejeu(d))
        self.ticks=self.root/'ticks.csv.gz'
        self.ticks.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0))
        self.gel=self.root/'gel.json'
        self.etat=self.root/'.local/validation/registre_reserve.json'

    def cli(self,*args,code=0):
        r=subprocess.run([sys.executable,'-B','-m','xpbots.app','--racine-depot',str(self.root),
                          *map(str,args)],cwd=self.root,env=self.env,capture_output=True,text=True,
                         encoding='utf-8',timeout=60)
        self.assertEqual(r.returncode,code,(r.stdout,r.stderr))
        return r.stdout

    def geler(self,fichier=None):
        return self.cli('geler-code','--registre',self.registre,'--sortie',fichier or self.gel)

    def rejouer(self,gel=None,code=0):
        return self.cli('rejeu','--registre',self.registre,'--demande',self.demande,'--ticks',self.ticks,
            '--archive',self.root/'archive.json','--rapport',self.root/'rapport.json',
            '--ouvrir-reserve','--gel',gel or self.gel,'--ecraser',code=code)

    def test_aide_sans_sdk_premier_gel_conserve_et_changement_refuse_avant_prix(self):
        self.assertIn('geler-code',self.cli('--help'));self.assertFalse(self.etat.exists())
        self.geler();gel1=json.loads(self.gel.read_bytes())
        self.assertTrue(any(n=='src/xpbots/app/c3_principal/_impl.py' for n,_ in gel1['inventaire']['fichiers']))
        self.assertEqual(json.loads(self.rejouer())['statut'],'NON_VALIDE')
        premier=json.loads(self.etat.read_bytes())
        self.assertEqual(premier['empreinte_robot'],gel1['inventaire']['sha256'])
        self.assertEqual(premier['historique'][0]['action'],'OUVERTURE_RESERVE')
        self.rejouer();second=json.loads(self.etat.read_bytes())
        self.assertEqual(second['empreinte_robot'],premier['empreinte_robot'])
        self.assertGreater(len(second['historique']),len(premier['historique']))
        self.assertEqual(sum(e['action']=='OUVERTURE_RESERVE' for e in second['historique']),1)
        self.assertEqual(second['historique'][-1]['action'],'CONSULTATION_RESERVE')
        # La modification est exécutée dans la copie ; le dépôt et son gel restent intacts.
        (self.root/'src/xpbots/preuve_changement.py').write_text('PREUVE = 1\n',encoding='utf-8')
        self.assertEqual(json.loads(self.rejouer(code=2))['code'],'GEL_ROBOT_DIFFERENT')
        gel2=self.root/'nouveau_gel.json';self.geler(gel2)
        self.assertNotEqual(json.loads(gel2.read_bytes())['inventaire']['sha256'],premier['empreinte_robot'])
        self.ticks.unlink()
        self.assertEqual(json.loads(self.rejouer(gel2,code=2))['code'],'GEL_RESERVE_DIFFERENT')
        refuse=json.loads(self.etat.read_bytes())
        self.assertEqual(refuse['empreinte_robot'],premier['empreinte_robot'])
        self.assertEqual(refuse['historique'][-1]['action'],'REFUS_RESERVE')
        self.assertEqual(refuse['historique'][0],premier['historique'][0])

    def test_verrou_exclusif_et_registre_corrompu_ne_sont_pas_reinitialises(self):
        self.geler();self.rejouer();avant=self.etat.read_bytes()
        with VerrouProcessus(self.etat.with_suffix('.lock')):
            r=json.loads(self.rejouer(code=2))
            self.assertEqual(r['code'],'VERROU_PROCESSUS_INDISPONIBLE')
        self.assertEqual(self.etat.read_bytes(),avant)
        self.etat.write_bytes(b'{"schema":"CORROMPU"}\n');corrompu=self.etat.read_bytes()
        self.ticks.unlink()
        self.assertEqual(json.loads(self.rejouer(code=2))['code'],'ATTESTATION_RESERVE_INDISPONIBLE')
        self.assertEqual(self.etat.read_bytes(),corrompu)
