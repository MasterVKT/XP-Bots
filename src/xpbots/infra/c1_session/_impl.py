"""Attachement au terminal et statut natif, sans accès aux identifiants."""
from dataclasses import dataclass
from pathlib import Path
import os
from xpbots.infra.c0a_types import ProtocoleMT5, ErreurInfra, ErreurNative, entier_natif, champ_natif

_MODES = frozenset(('PAPER', 'PAPER_AB', 'DEMO', 'REEL'))
_FONCTIONS = frozenset(('initialize', 'shutdown', 'version', 'account_info', 'terminal_info',
    'symbols_get', 'symbol_select', 'symbol_info', 'symbol_info_tick', 'copy_ticks_from', 'copy_ticks_range',
    'order_calc_profit', 'order_calc_margin', 'order_check', 'order_send', 'positions_get', 'orders_get',
    'history_orders_get', 'history_deals_get'))


@dataclass(frozen=True)
class EtatSession:
    version_paquet: str
    version_terminal: tuple
    build: int
    connecte: bool
    droits: bool
    common_files: str
    alertes: tuple


def _booleen(objet, nom):
    v = champ_natif(objet, nom)
    if type(v) is not bool:
        raise ErreurInfra('champ natif booléen requis : '+nom)
    return v


class SessionMT5:
    def __init__(self, sdk: ProtocoleMT5, mode, *, chemin_terminal=None, common_files_attendu=None):
        if type(mode) is not str or mode not in _MODES:
            raise ErreurInfra('mode de session invalide')
        self.sdk = sdk
        self.mode = mode
        self.chemin_terminal = chemin_terminal
        self.common_files_attendu = common_files_attendu
        self.etat = None
        self.attachee = False

    def _erreur(self, nom):
        try:
            resultat = self.sdk.last_error()
            code = entier_natif(resultat[0])
        except Exception:
            code = self.sdk.RES_E_FAIL
        return ErreurNative(nom, code)

    def appeler(self, nom, *args, **kw):
        if nom not in _FONCTIONS:
            raise ErreurInfra('fonction native non autorisée')
        if nom == 'shutdown':
            self.fermer()
            return None
        if nom == 'initialize' and (len(args) > 1 or kw or args and type(args[0]) is not str):
            raise ErreurInfra('attachement sans identifiants uniquement')
        if nom == 'order_send' and self.mode not in ('DEMO', 'REEL'):
            raise ErreurInfra('envoi natif interdit en papier')
        if nom not in ('initialize', 'shutdown') and not self.attachee:
            raise ErreurInfra('session non attachée')
        try:
            resultat = getattr(self.sdk, nom)(*args, **kw)
        except Exception:
            raise self._erreur(nom) from None
        if resultat is None:
            raise self._erreur(nom) from None
        return resultat

    def attacher(self):
        if self.attachee:
            raise ErreurInfra('session déjà attachée')
        if getattr(self.sdk, '__version__', None) != '5.0.6231':
            raise ErreurInfra('version du paquet MT5 incompatible')
        args = () if self.chemin_terminal is None else (str(self.chemin_terminal),)
        if self.appeler('initialize', *args) is not True:
            raise self._erreur('initialize') from None
        self.attachee = True
        try:
            etat = self.actualiser()
            if not etat.connecte or self.mode in ('DEMO', 'REEL') and not etat.droits:
                raise ErreurInfra('ENVIRONMENT_NOT_READY connexion ou droits natifs')
            return etat
        except BaseException:
            self.fermer()
            raise

    def actualiser(self):
        terminal = self.appeler('terminal_info')
        compte = self.appeler('account_info')
        version = self.appeler('version')
        if (not isinstance(version, (tuple, list)) or len(version) != 3
                or type(version[-1]) is not str):
            raise ErreurInfra('version du terminal incomplète')
        version = (entier_natif(version[0]), entier_natif(version[1]), version[-1])
        if version[0] <= 0 or version[1] <= 0:
            raise ErreurInfra('version du terminal invalide')
        mode = entier_natif(champ_natif(compte, 'trade_mode'))
        if (self.mode == 'DEMO' and mode != self.sdk.ACCOUNT_TRADE_MODE_DEMO
                or self.mode == 'REEL' and mode != self.sdk.ACCOUNT_TRADE_MODE_REAL):
            raise ErreurInfra('ENVIRONMENT_NOT_READY type de compte incompatible')
        root = champ_natif(terminal, 'commondata_path')
        if type(root) is not str or not root or not Path(root).is_absolute():
            raise ErreurInfra('dossier commun natif absent')
        common = (Path(root)/'Files').resolve()
        alertes = ()
        if self.common_files_attendu is not None and os.path.normcase(str(Path(self.common_files_attendu).resolve())) != os.path.normcase(str(common)):
            alertes = ('COMMON_FILES_DIFFERENT',)
        droits = (_booleen(terminal, 'trade_allowed'), not _booleen(terminal, 'tradeapi_disabled'),
                  _booleen(compte, 'trade_allowed'), _booleen(compte, 'trade_expert'))
        etat = EtatSession(self.sdk.__version__, version, entier_natif(champ_natif(terminal, 'build')),
            _booleen(terminal, 'connected'), all(droits),
            str(common), alertes)
        self.etat = etat
        return etat

    def fermer(self):
        if self.attachee:
            self.attachee = False
            try:
                self.sdk.shutdown()
            except Exception:
                raise self._erreur('shutdown') from None
