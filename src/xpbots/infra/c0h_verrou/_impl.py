"""Verrou physique non bloquant ; ne jamais supprimer son fichier support."""
from pathlib import Path
import os


class VerrouProcessus:
    def __init__(self,chemin):
        if not isinstance(chemin,(str,os.PathLike)) or not str(chemin):
            raise ValueError('VERROU_CHEMIN_INVALIDE')
        self.chemin=Path(chemin);self._fichier=None

    @property
    def acquis(self):return self._fichier is not None

    def acquerir(self):
        if self._fichier is not None:return self
        f=None
        try:
            self.chemin.parent.mkdir(parents=True,exist_ok=True)
            f=self.chemin.open('a+b')
            f.seek(0)
            if not f.read(1):
                f.write(b'\0');f.flush();os.fsync(f.fileno())
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            elif os.name=='posix':
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            else:raise ValueError('VERROU_PLATEFORME_NON_SUPPORTEE')
            self._fichier=f
            return self
        except (OSError,ValueError):
            if f is not None:f.close()
            raise ValueError('VERROU_PROCESSUS_INDISPONIBLE') from None

    def liberer(self):
        f=self._fichier
        if f is None:return
        self._fichier=None
        try:
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            elif os.name=='posix':
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)
        finally:f.close()

    def __enter__(self):return self.acquerir()
    def __exit__(self,*_):self.liberer()
