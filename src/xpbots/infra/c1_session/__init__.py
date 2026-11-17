"""Session native injectée, sans identifiants ni import du paquet SDK."""
from ._impl import SessionMT5, EtatSession

__all__ = ('SessionMT5', 'EtatSession')
