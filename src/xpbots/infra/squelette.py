"""Compatibilité des fichiers synthétiques S1 et façade du writer physique S6.

Le direct de phase 11 passe par `infrastructure` (flux MT5 et journal quotidien durable).
La lecture simple reste réservée aux fixtures historiques ; S6 délègue au writer commun. Contrat des coutures : mcl/squelette/COUTURES.md. Seul paquet du squelette qui
touche au système de fichiers.
"""
from __future__ import annotations

import os
from typing import Iterable, Iterator
from xpbots.infra.c4_assemblage import ecrire_fichier

NOM_JOURNAL_SQUELETTE = 'decisions.jsonl'
CHEMINS_CONFIGURATION = ('config/parametres_figes_v3.json', 'config/parametres_IA_integration_v1.json',
                         'docs/validation/conservation_ressources.json')


def lire_octets(chemin: str) -> bytes:
    """Lire un fichier entier."""
    with open(chemin, 'rb') as fichier:
        return fichier.read()


def lire_configuration(racine_depot: str) -> tuple[bytes, bytes, bytes]:
    """Octets de l'export technique, de l'export IA et de la preuve de conservation du dépôt."""
    return tuple(lire_octets(os.path.join(racine_depot, *relatif.split('/'))) for relatif in CHEMINS_CONFIGURATION)


def lire_lignes(chemin: str) -> Iterator[str]:
    """Lire un fichier texte UTF-8 ligne par ligne, sans le caractère de fin de ligne."""
    with open(chemin, encoding='utf-8', newline='') as fichier:
        for ligne in fichier:
            yield ligne.rstrip('\r\n')


def ecrire_journal(dossier: str, lignes: Iterable[str]) -> str:
    """Façade de compatibilité S6 ; le writer atomique est celui de l'infrastructure."""
    chemin = os.path.join(dossier, NOM_JOURNAL_SQUELETTE)
    contenu = bytearray()
    for ligne in lignes:
        if '\n' in ligne or '\r' in ligne:
            raise ValueError('une ligne de journal ne contient aucun saut de ligne')
        contenu.extend((ligne+'\n').encode('utf-8'))
    ecrire_fichier(chemin, bytes(contenu), ecraser=True)
    return chemin
