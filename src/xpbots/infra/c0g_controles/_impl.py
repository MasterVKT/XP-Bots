"""Fichiers D11/D12 en lecture seule, datés par la coquille."""
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


@dataclass(frozen=True)
class ReceptionFichier:
    nature: str
    symbole: str | None
    octets: bytes | None
    instant_ms: int
    erreur: str | None


def _nom(v):
    if (type(v) is not str or not v or v in ('.', '..') or v[-1] in ('.', ' ')
            or any(c in v for c in '/\\:\x00<>|?*"')):
        raise ValueError('nom de fichier sûr requis')
    return v


class SourcesControles:
    def __init__(self, dossier_commun, liaisons, max_octets):
        if type(max_octets) is not int or max_octets <= 0 or not liaisons:
            raise ValueError('liaisons et plafond explicites requis')
        self.dossier = Path(dossier_commun)
        self.liaisons = MappingProxyType({_nom(k): _nom(v) for k, v in liaisons.items()})
        if len(set(self.liaisons.values())) != len(self.liaisons):
            raise ValueError('liaison d’un même symbole courtier en double')
        self.max_octets = max_octets

    def lire(self, instant_ms):
        if type(instant_ms) is not int or instant_ms < 0:
            raise ValueError('instant de lecture requis')
        base = self.dossier/'XPBots'
        fichiers = [('PERMISSION', s, base/'fondamental'/'v1'/('permission_'+s+'.json')) for s in self.liaisons]
        fichiers += [('CALENDRIER', None, base/'export'/'v1'/'calendrier.json'),
                     ('FERMETURES', None, base/'export'/'v1'/'fermetures_exceptionnelles.json')]
        fichiers += [('SEANCES', s, base/'export'/'v1'/('seances_'+b+'.json')) for s, b in self.liaisons.items()]
        resultat = []
        for nature, symbole, chemin in fichiers:
            b, erreur = None, None
            try:
                with chemin.open('rb') as f:
                    b = f.read(self.max_octets+1)
                if len(b) > self.max_octets:
                    b, erreur = None, 'FICHIER_TROP_GRAND'
            except FileNotFoundError:
                erreur = 'FICHIER_ABSENT'
            except OSError:
                erreur = 'LECTURE_IMPOSSIBLE'
            resultat.append(ReceptionFichier(nature, symbole, b, instant_ms, erreur))
        return tuple(resultat)
