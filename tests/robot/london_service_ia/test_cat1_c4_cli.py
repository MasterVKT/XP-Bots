"""CLI hors ligne : profil non qualifié, état sans clé et refus statique."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xpbots.service_ia.c0_types import decoder
from xpbots.service_ia.c4_service import main,ServiceIA
from xpbots.service_ia.c4_service._cli import charger_profil
from .support import ROOT,ressources,Horloge


def sans_cle(nom,defaut=None):
    if nom in ('GROQ_API_KEY','GEMINI_API_KEY','OPENAI_API_KEY'):raise AssertionError('lecture clé inattendue')
    return defaut  # gettext/argparse peuvent consulter une préférence de langue publique.


class CLIService(unittest.TestCase):
    def test_route_payante_non_incluse_dans_audit_par_defaut_meme_projet_non_qualifie(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'profile.json';self.executer(['profil-exemple','--sortie',str(p)])
            with patch('os.environ.get',return_value='CLE_SYNTHETIQUE'):
                _,_,_,_,routes=charger_profil(ressources(),p,autoriser_cles=True)
            payantes={v['id'] for v in ressources().p['providers'] if 'input_usd_per_million_upper_bound' in v}
            self.assertFalse(payantes.intersection(routes))
    def test_route_payante_incluse_dans_audit_seulement_sur_autorisation_explicite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'profile.json';self.executer(['profil-exemple','--sortie',str(p)])
            with patch('os.environ.get',return_value='CLE_SYNTHETIQUE'):
                _,_,_,_,routes=charger_profil(ressources(),p,autoriser_cles=True,paiement_autorise=True)
            self.assertEqual(set(routes),{v['id'] for v in ressources().p['providers']})

    def executer(self,args):
        sortie=StringIO()
        with redirect_stdout(sortie):code=main(['--racine-depot',str(ROOT),*args])
        return code,decoder(sortie.getvalue().encode())
    def test_gabarit_public_sans_secret_sans_ecrasement(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'profile.json'
            with patch('os.environ.get',side_effect=sans_cle):
                code,v=self.executer(['profil-exemple','--sortie',str(p)])
            self.assertEqual(code,0);profil=decoder(p.read_bytes())
            self.assertTrue(all(not a['cle_disponible'] and a['verifie_ms'] is None for a in profil['providers']))
            self.assertEqual(len(profil['providers']),len(ressources().p['providers']))
            avant=p.read_bytes();code,v=self.executer(['profil-exemple','--sortie',str(p)])
            self.assertEqual(code,1);self.assertEqual(p.read_bytes(),avant)
    def test_etat_ne_lit_aucune_cle_et_ne_recree_pas_base_absente(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=p/'ia.db'
            code,v=self.executer(['--base',str(base),'etat']);self.assertEqual(code,1);self.assertFalse(base.exists())
            with ServiceIA(ressources(),base,p/'context.json',horloge=Horloge()) as s:s.heartbeat()
            with patch('os.environ.get',side_effect=sans_cle):
                code,v=self.executer(['--base',str(base),'etat'])
            self.assertEqual(code,0);self.assertEqual(v['sequence'],1);self.assertEqual(v['mode'],ressources().p['default_evaluation_mode'])
