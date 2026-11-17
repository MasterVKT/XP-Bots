"""Activation explicite des contrats physiques en 13.1, jamais par la suite ordinaire."""
from contextlib import contextmanager
import importlib
import json
import os
from pathlib import Path

MT5_ACTIF = os.name == 'nt' and os.environ.get('XPBOTS_CONTRATS_MT5') == '1'
RAISON = '13.1 : Windows, terminal démo et XPBOTS_CONTRATS_MT5=1 requis'


def registre_contrat():
    chemin = os.environ.get('XPBOTS_CONTRATS_REGISTRE')
    if not chemin:
        raise AssertionError('13.1 : XPBOTS_CONTRATS_REGISTRE doit désigner le registre qualifié')
    r = json.loads(Path(chemin).read_text(encoding='utf-8'))
    if r.get('mode') != 'DEMO' or not r.get('liaisons'):
        raise AssertionError('registre de démonstration qualifié requis')
    return r


@contextmanager
def sdk_contrat():
    if not MT5_ACTIF:
        raise AssertionError('contrat physique non activé')
    sdk = importlib.import_module('MetaTrader5')
    if sdk.__version__ != '5.0.6231' or not sdk.initialize():
        raise AssertionError('SDK épinglé et terminal connecté requis')
    try:
        compte = sdk.account_info()
        if compte is None or compte.trade_mode != sdk.ACCOUNT_TRADE_MODE_DEMO:
            raise AssertionError('contrats physiques limités au compte démo')
        yield sdk
    finally:
        sdk.shutdown()
