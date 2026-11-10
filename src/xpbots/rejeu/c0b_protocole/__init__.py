"""Couche 0b — protocole C10 fixé avant les données. Contrat : couche-0b.md du dossier actif."""
from ._impl import (ErreurProtocole,BlocC10,ScenarioExecution,ParametresBootstrap,SeuilsC10,
    ProtocoleC10,charger_protocole)

__all__=('ErreurProtocole','BlocC10','ScenarioExecution','ParametresBootstrap','SeuilsC10',
    'ProtocoleC10','charger_protocole')
