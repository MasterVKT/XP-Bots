"""Fichiers et processus reels, sans simuler une primitive de verrou."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import inspect,subprocess,sys,time,unittest
from xpbots.infra.c0h_verrou import VerrouProcessus


class TestVerrouSysteme(unittest.TestCase):
    def test_exclusion_contexte_repetition_et_fichier_conserve(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'sous-dossier'/'coordinateur.lock'
            premier=VerrouProcessus(p);autre=VerrouProcessus(p)
            with premier:
                self.assertTrue(premier.acquis);self.assertIs(premier.acquerir(),premier)
                with self.assertRaisesRegex(ValueError,'^VERROU_PROCESSUS_INDISPONIBLE$'):autre.acquerir()
                self.assertFalse(autre.acquis)
            self.assertFalse(premier.acquis);self.assertTrue(p.is_file())
            premier.liberer()
            with autre:self.assertTrue(autre.acquis)

    def test_exception_de_contexte_libere_et_erreur_ouverture_ne_fuit_pas_chemin(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'coordinateur.lock'
            with self.assertRaises(RuntimeError):
                with VerrouProcessus(p):raise RuntimeError('incident synthetique')
            with VerrouProcessus(p):pass
            invalide=VerrouProcessus(Path(d))
            with self.assertRaisesRegex(ValueError,'^VERROU_PROCESSUS_INDISPONIBLE$'):invalide.acquerir()
            self.assertFalse(invalide.acquis)
        for v in (None,False,0,''):
            with self.assertRaises(ValueError):VerrouProcessus(v)

    def test_processus_concurrent_exclu_et_mort_libere_sans_supprimer_fichier(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'coordinateur.lock';marqueur=Path(d)/'acquis'
            code=('import sys;from pathlib import Path;from runpy import run_path;'
                'Verrou=run_path(sys.argv[1])["VerrouProcessus"];'
                'v=Verrou(sys.argv[2]);v.acquerir();Path(sys.argv[3]).write_bytes(b"OK");sys.stdin.read()')
            enfant=subprocess.Popen([sys.executable,'-B','-c',code,inspect.getfile(VerrouProcessus),str(p),str(marqueur)],
                stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                fin=time.monotonic()+5
                while not marqueur.exists() and time.monotonic()<fin and enfant.poll() is None:Event().wait(.01)
                self.assertTrue(marqueur.exists(),'le processus enfant doit avoir acquis le vrai verrou')
                with self.assertRaises(ValueError):VerrouProcessus(p).acquerir()
                enfant.terminate();enfant.wait(timeout=5)
                self.assertTrue(p.is_file())
                with VerrouProcessus(p):pass
            finally:
                if enfant.poll() is None:enfant.kill();enfant.wait(timeout=5)
                enfant.stdin.close();enfant.stderr.close()
