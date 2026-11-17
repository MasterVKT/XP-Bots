"""Ressources reelles et seul SDK externe double ; aucune connexion native."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib,io,os,unittest,gzip,hashlib
from robot.outils.execution_partagee import configuration
from robot.outils.qualification_mt5 import T
from robot.outils.faux_mt5 import FauxMT5
from xpbots.infra.c0a_types import ErreurInfra
from xpbots.infra.c4_assemblage import InfrastructurePhysique,lire_configuration,ecrire_fichier,ouvrir_ticks


META=dict(deploiement='FIXTURE',mode='DEMO',empreintes={'technique':'a'*64,'ia':'b'*64},commit='c'*40)


class HarnaisInfrastructure:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.racine=Path(self.temp.name);self.commun=self.racine/'commun';self.temps=T
        p=patch('time.time_ns',side_effect=lambda:self.temps*1000000);p.start();self.addCleanup(p.stop)
        self.env=patch.dict(os.environ,{'XPBOTS_COMMON_FILES_DIR':''});self.env.start();self.addCleanup(self.env.stop)

    def nouveau(self,*,meta=None,sdk=None,racine=None,**options):
        sdk=sdk if sdk is not None else FauxMT5(self.commun,instant_ms=T)
        r=InfrastructurePhysique(configuration().commun,META if meta is None else meta,{'EURUSD':'EURUSD.micro'},
            racine=self.racine if racine is None else racine,max_octets_echange=131072,snapshot_max_octets=32768,
            sdk=sdk,common_files_attendu=str(self.commun/'Files'),**options)
        self.addCleanup(lambda:r.fermer(1000))
        return r,sdk


class TestAssemblagePhysique(HarnaisInfrastructure,unittest.TestCase):
    def test_import_inerte_et_resolution_sdk_uniquement_a_construction(self):
        import xpbots.infra.c4_assemblage as module
        with patch('importlib.import_module',side_effect=AssertionError('import natif interdit au chargement')):
            importlib.reload(module)
        sdk=FauxMT5(self.commun,instant_ms=T)
        with patch('importlib.import_module',return_value=sdk) as resolver:
            i=InfrastructurePhysique(configuration().commun,META,{'EURUSD':'EURUSD.micro'},racine=self.racine,
                max_octets_echange=131072,snapshot_max_octets=32768,common_files_attendu=str(self.commun/'Files'))
            self.addCleanup(lambda:i.fermer(1000));resolver.assert_called_once_with('MetaTrader5')
        self.assertFalse(any(a[0]=='order_send' for a in sdk.appels));self.assertTrue(i.fermer(0));self.assertFalse(sdk.attache)

    def test_deux_deploiements_exclus_et_echec_nettoie_session_sans_creer_base(self):
        premier,sdk=self.nouveau()
        with self.assertRaisesRegex(ErreurInfra,'COURTIER_NON_INITIALISE'):_=premier.courtier
        autre=FauxMT5(self.commun,instant_ms=T)
        with self.assertRaises(ErreurInfra):self.nouveau(meta=dict(META,deploiement='AUTRE'),sdk=autre)
        self.assertFalse(autre.attache);self.assertTrue(sdk.attache)
        self.assertFalse((self.racine/'runtime/AUTRE/etat.sqlite').exists())
        self.assertTrue(premier.fermer(0))
        suivant,_=self.nouveau();self.assertTrue(suivant.fermer(0))

    def test_lien_compte_refuse_changer_de_deploiement_et_etat_disparu(self):
        i,_=self.nouveau();i.fermer(0)
        with self.assertRaisesRegex(ErreurInfra,'PROPRIETE_COMPTE_INCOMPATIBLE'):
            self.nouveau(meta=dict(META,deploiement='AUTRE'))
        etat=self.racine/'runtime/FIXTURE/etat.sqlite'
        self.assertTrue(etat.read_bytes());etat.unlink()
        with self.assertRaisesRegex(ErreurInfra,'ETAT_COMPTE_PERSISTANT_ABSENT'):self.nouveau()

    def test_meta_etrangere_ou_session_incompatible_ne_reinitialise_pas(self):
        i,_=self.nouveau();i.depot.persister(1,T,b'{"etat":1}');i.fermer(0)
        with self.assertRaises(ErreurInfra):self.nouveau(meta=dict(META,commit='d'*40))
        i,_=self.nouveau();self.assertEqual(i.depot.charger(),b'{"etat":1}');i.fermer(0)
        mauvais=FauxMT5(self.commun,instant_ms=T);mauvais.__version__='incompatible'
        with self.assertRaises(ErreurInfra):self.nouveau(sdk=mauvais)
        self.assertFalse(mauvais.attache);self.assertFalse(any(a[0]=='initialize' for a in mauvais.appels))

    def test_lectures_connues_apres_fichier_et_snapshot_exact_a10(self):
        i,_=self.nouveau();base=self.commun/'Files/XPBots'
        (base/'fondamental/v1').mkdir(parents=True)
        (base/'fondamental/v1/permission_EURUSD.json').write_bytes(b'{"fixture":1}')
        (base/'ai/v1').mkdir(parents=True);(base/'ai/v1/context_latest.json').write_bytes(b'SNAPSHOT_FIXTURE')
        original=Path.open
        def ouvrir(p,*a,**kw):
            f=original(p,*a,**kw)
            if 'r' in (a[0] if a else kw.get('mode','r')):self.temps+=1
            return f
        with patch.object(Path,'open',autospec=True,side_effect=ouvrir):r=i.lire_controles();b,t,e=i.lire_snapshot()
        self.assertTrue(all(v.instant_ms>T for v in r));self.assertGreaterEqual(t,max(v.instant_ms for v in r))
        self.assertEqual((b,e),(b'SNAPSHOT_FIXTURE',None))
        permission=next(v for v in r if v.nature=='PERMISSION');self.assertEqual(permission.octets,b'{"fixture":1}')
        self.assertTrue(all(v.erreur=='FICHIER_ABSENT' for v in r if v.nature!='PERMISSION'))

    def test_variables_d_environnement_ne_changent_pas_le_dossier_natif(self):
        sdk=FauxMT5(self.commun,instant_ms=T)
        with patch.dict(os.environ,{'XPBOTS_COMMON_FILES_DIR':str(self.racine/'autre')}),patch('sys.stderr',new_callable=io.StringIO) as sortie:
            i=InfrastructurePhysique(configuration().commun,META,{'EURUSD':'EURUSD.micro'},racine=self.racine,
                max_octets_echange=131072,snapshot_max_octets=32768,sdk=sdk)
            self.addCleanup(lambda:i.fermer(1000))
        self.assertIn('COMMON_FILES_DIFFERENT',sortie.getvalue())
        self.assertEqual(Path(i.session.etat.common_files),self.commun/'Files')
        self.assertNotIn(str(self.racine),sortie.getvalue())

    def test_documents_env_bloques_avant_ouverture_et_ecriture_atomique_expresse(self):
        secret=self.racine/'.env';secret.write_text('SECRET_SYNTHETIQUE_NON_REEL',encoding='utf-8')
        with patch.object(Path,'open',side_effect=AssertionError('aucune ouverture env')):
            with self.assertRaisesRegex(ErreurInfra,'FICHIER_ENV_INTERDIT'):lire_configuration(secret,100)
            with self.assertRaisesRegex(ErreurInfra,'FICHIER_ENV_INTERDIT'):ecrire_fichier(secret,b'{}',ecraser=True)
            with self.assertRaisesRegex(ErreurInfra,'FICHIER_ENV_INTERDIT'):ouvrir_ticks(secret)
        p=self.racine/'registre.json';ecrire_fichier(p,b'{"fixture":1}')
        self.assertEqual(lire_configuration(p,100),{'fixture':1})
        with self.assertRaisesRegex(ErreurInfra,'FICHIER_EXISTANT'):ecrire_fichier(p,b'{}')
        ecrire_fichier(p,b'{"fixture":2}',ecraser=True)
        self.assertEqual(lire_configuration(p,100),{'fixture':2})
        with self.assertRaises(ErreurInfra):lire_configuration(p,1)
        with self.assertRaises(ErreurInfra):ouvrir_ticks(p)

    def test_lecture_ticks_physique_qualifie_octets_sans_attacher_sdk(self):
        contenu=b'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask\nEURUSD,EURUSD.micro,1794301200000,1,1.1003,1.1004\n'
        physique=gzip.compress(contenu,mtime=0);p=self.racine/'EURUSD_2026-11.csv.gz';p.write_bytes(physique)
        with patch('importlib.import_module',side_effect=AssertionError('rejeu sans SDK')):
            with ouvrir_ticks(p) as lecteur:
                self.assertEqual(''.join(lecteur.lignes()).encode(),contenu)
                self.assertEqual(lecteur.sha256_fichier,hashlib.sha256(physique).hexdigest())
                self.assertEqual(lecteur.sha256_contenu,hashlib.sha256(contenu).hexdigest())
