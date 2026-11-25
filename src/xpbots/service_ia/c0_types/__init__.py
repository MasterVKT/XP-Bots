"""Couche 0 du service IA — types : valeurs pures et ports externes.

Interface publique figée ; contrat : mcl/london-service-ia/contrats/couche-0.md.
"""
from ._impl import (ErreurService, RessourcesIA, DocumentIA, RequeteHTTP,
    ReponseHTTP, JobIA, ResultatIA, DepotIA, HorlogeIA, canonique, decoder,
    empreinte, entier, instant, texte, montant, iso, utc, url_https, TABLES_IA)

__all__ = ('ErreurService', 'RessourcesIA', 'DocumentIA', 'RequeteHTTP',
    'ReponseHTTP', 'JobIA', 'ResultatIA', 'DepotIA', 'HorlogeIA', 'canonique',
    'decoder', 'empreinte', 'entier', 'instant', 'texte', 'montant', 'iso',
    'utc', 'url_https', 'TABLES_IA')
