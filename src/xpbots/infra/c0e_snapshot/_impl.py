"""Lecture binaire bornée et immédiatement fermée du seul snapshot A10."""
from pathlib import Path


class LecteurSnapshot:
    def __init__(self, chemin, max_octets):
        if type(max_octets) is not int or max_octets <= 0:
            raise ValueError('plafond snapshot requis')
        self.chemin = Path(chemin)
        self.max_octets = max_octets

    def lire(self, instant_ms):
        if type(instant_ms) is not int or instant_ms < 0:
            raise ValueError('instant de lecture requis')
        try:
            with self.chemin.open('rb') as f:
                b = f.read(self.max_octets+1)
            if len(b) > self.max_octets:
                return None, instant_ms, 'SNAPSHOT_TROP_GRAND'
            return b, instant_ms, None
        except FileNotFoundError:
            return None, instant_ms, 'SNAPSHOT_ABSENT'
        except OSError:
            return None, instant_ms, 'SNAPSHOT_LECTURE_IMPOSSIBLE'
