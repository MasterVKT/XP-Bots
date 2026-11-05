"""Doublure de la frontière « stockage d'état » : dictionnaire en mémoire, même contrat que le port `Stockage`."""


class StockageMemoire:
    def __init__(self):
        self._donnees: dict[str, bytes] = {}
        self.ecritures = 0

    def lire(self, cle: str) -> bytes | None:
        if type(cle) is not str or not cle:
            raise ValueError('clé de stockage invalide')
        return self._donnees.get(cle)

    def ecrire(self, cle: str, valeur: bytes) -> None:
        if type(cle) is not str or not cle or type(valeur) is not bytes:
            raise ValueError('clé ou valeur de stockage invalide')
        self._donnees[cle] = valeur
        self.ecritures += 1
