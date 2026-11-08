"""Frontière C05 synthétique ; aucun lecteur de permission de phase 7."""
from xpbots.noyau.c1c_domaine import DecisionFondamentale


class PermissionSynthetique:
    def __init__(self, decision=None, symboles=()):
        self.decision = decision or DecisionFondamentale(True)
        self.symboles = symboles
        self.appels = []
        self.indisponible = False

    def evaluer(self, symbole, sens, instant_ms):
        self.appels.append((symbole, sens, instant_ms))
        if self.indisponible:
            raise OSError('frontière indisponible')
        return self.decision

    def clotures_obligatoires(self, instant_ms):
        if self.indisponible:
            raise OSError('frontière indisponible')
        return self.symboles
