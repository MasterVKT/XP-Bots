"""Lecture gzip en flux ; empreintes des octets physiques et décompressés distinctes."""
from pathlib import Path
import gzip
import hashlib
import io


class LectureTicks:
    def __init__(self, chemin):
        self.chemin = Path(chemin)
        if not self.chemin.name.endswith('.csv.gz'):
            raise ValueError('fichier mensuel .csv.gz requis')
        self.sha256_fichier = None
        self.sha256_contenu = None
        self._fichier = None
        self._texte = None
        self._ouverte = False

    def lignes(self):
        if self._ouverte:
            raise ValueError('lecture déjà engagée')
        self._ouverte = True
        try:
            self._fichier = self.chemin.open('rb')
            physique = hashlib.sha256()
            while b := self._fichier.read(131072):
                physique.update(b)
            self._fichier.seek(0)
            self._texte = io.TextIOWrapper(gzip.GzipFile(fileobj=self._fichier, mode='rb'), encoding='utf-8', errors='strict', newline='')
            contenu = hashlib.sha256()
            for ligne in self._texte:
                contenu.update(ligne.encode('utf-8'))
                yield ligne
            # Une modification en place est détectée avant qualification du lot.
            self._fichier.seek(0)
            verification = hashlib.sha256()
            while b := self._fichier.read(131072):
                verification.update(b)
            if verification.digest() != physique.digest():
                raise OSError('fichier de ticks modifié pendant lecture')
            self.sha256_fichier = physique.hexdigest()
            self.sha256_contenu = contenu.hexdigest()
        finally:
            self.fermer()

    def fermer(self):
        if self._texte is not None:
            self._texte.close()
        if self._fichier is not None:
            self._fichier.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.fermer()
