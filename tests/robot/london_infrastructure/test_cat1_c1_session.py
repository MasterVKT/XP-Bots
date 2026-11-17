"""Catégorie 1, couche 1 : attachement, gardes et erreurs natives assainies."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.faux_mt5 import FauxMT5
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c0a_types import ErreurInfra, ErreurNative


class TestSessionNative(unittest.TestCase):
    def test_attachement_sans_identifiants_racine_files_et_fermeture(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); s = SessionMT5(sdk, 'DEMO', chemin_terminal=Path(d)/'terminal64.exe')
            etat = s.attacher()
            self.assertEqual(etat.common_files, str((Path(d)/'Files').resolve()))
            self.assertTrue(etat.connecte); self.assertTrue(etat.droits)
            init = next(c for c in sdk.appels if c[0] == 'initialize')
            self.assertEqual(init[1], (str(Path(d)/'terminal64.exe'),)); self.assertEqual(init[2], {})
            self.assertNotIn(str(sdk.compte.login), repr(etat))
            s.fermer(); s.fermer(); self.assertFalse(s.attachee)
            self.assertEqual(sum(c[0] == 'shutdown' for c in sdk.appels), 1)

    def test_modes_demo_reel_et_type_compte_incompatible(self):
        with TemporaryDirectory() as d:
            for mode, trade in (('DEMO', FauxMT5.ACCOUNT_TRADE_MODE_REAL), ('REEL', FauxMT5.ACCOUNT_TRADE_MODE_DEMO)):
                sdk = FauxMT5(d); sdk.compte = sdk.compte._replace(trade_mode=trade); s = SessionMT5(sdk, mode)
                with self.assertRaises(ErreurInfra): s.attacher()
                self.assertFalse(s.attachee); self.assertFalse(sdk.attache)
            for mode in ('PAPER', 'PAPER_AB'):
                sdk = FauxMT5(d); sdk.compte = sdk.compte._replace(trade_mode=sdk.ACCOUNT_TRADE_MODE_REAL)
                s = SessionMT5(sdk, mode); s.attacher()
                with self.assertRaises(ErreurInfra): s.appeler('order_send', {})
                self.assertFalse(any(c[0] == 'order_send' for c in sdk.appels)); s.fermer()

    def test_droits_et_connexion_degrades_sans_faux_etat_pret(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); sdk.terminal = sdk.terminal._replace(trade_allowed=False)
            with self.assertRaises(ErreurInfra): SessionMT5(sdk, 'DEMO').attacher()
            sdk.terminal = sdk.terminal._replace(trade_allowed=True)
            s = SessionMT5(sdk, 'DEMO'); s.attacher()
            sdk.terminal = sdk.terminal._replace(connected=False, tradeapi_disabled=True)
            etat = s.actualiser(); self.assertFalse(etat.connecte); self.assertFalse(etat.droits); s.fermer()

    def test_none_consomme_un_seul_last_error_sans_chaine_sensible(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); s = SessionMT5(sdk, 'DEMO'); s.attacher()
            sdk.erreur = (sdk.RES_E_AUTH_FAILED, 'NUMERO_COMPTE_SECRET_FIXTURE')
            sdk.scenarios['account_info'].append(None)
            with self.assertRaises(ErreurNative) as c: s.appeler('account_info')
            self.assertEqual(c.exception.code, sdk.RES_E_AUTH_FAILED)
            self.assertNotIn('SECRET', str(c.exception))
            self.assertEqual(sum(c[0] == 'last_error' for c in sdk.appels), 1); s.fermer()

    def test_zero_et_tableau_vide_ne_sont_pas_none(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); s = SessionMT5(sdk, 'DEMO'); s.attacher()
            sdk.scenarios['order_calc_profit'].append(0.0)
            self.assertEqual(s.appeler('order_calc_profit', 0, 'EURUSD.micro', 1., 1., 1.), 0.)
            self.assertEqual(s.appeler('positions_get'), ())
            self.assertFalse(any(c[0] == 'last_error' for c in sdk.appels)); s.fermer()

    def test_versions_mode_et_fonctions_interdites(self):
        for mode in (None, [], 'LIVE'):
            with self.assertRaises(ErreurInfra): SessionMT5(FauxMT5(), mode)
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); sdk.__version__ = '0'
            with self.assertRaises(ErreurInfra): SessionMT5(sdk, 'DEMO').attacher()
            sdk.__version__ = '5.0.6231'; s = SessionMT5(sdk, 'DEMO'); s.attacher()
            for nom in ('login', 'Buy', 'Sell', 'Close', 'copy_rates_from', 'copy_rates_range'):
                with self.assertRaises(ErreurInfra): s.appeler(nom)
            with self.assertRaises(ErreurInfra): s.appeler('initialize', login=123)
            with self.assertRaises(ErreurInfra): s.appeler('initialize', 'terminal', 123, 'password')
            s.fermer()

    def test_ecart_de_dossier_attendu_signale_et_chemin_relatif_refuse(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); s = SessionMT5(sdk, 'DEMO', common_files_attendu=Path(d)/'autre')
            self.assertEqual(s.attacher().alertes, ('COMMON_FILES_DIFFERENT',)); s.fermer()
        with self.assertRaises(ErreurInfra): SessionMT5(FauxMT5('chemin_relatif'), 'DEMO').attacher()

    def test_exception_native_et_init_refuse_ne_fuient_pas_le_message(self):
        with TemporaryDirectory() as d:
            sdk = FauxMT5(d); sdk.scenarios['initialize'].append(False)
            with self.assertRaises(ErreurNative): SessionMT5(sdk, 'DEMO').attacher()
            sdk.scenarios['terminal_info'].append(RuntimeError('SECRET_FIXTURE'))
            with self.assertRaises(ErreurNative) as c: SessionMT5(sdk, 'DEMO').attacher()
            self.assertNotIn('SECRET', str(c.exception)); self.assertFalse(sdk.attache)
