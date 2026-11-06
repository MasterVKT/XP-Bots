"""Segments minimaux S1 (lecture des fichiers) et S6 (écriture du journal) du squelette.

Segments minimaux du squelette, remplacés en phase 11 par l'artefact `infrastructure` (lecteurs de fichiers et
journal JSON Lines quotidien). Contrat des coutures : mcl/squelette/COUTURES.md. Seul paquet du squelette qui
touche au système de fichiers.
"""
from __future__ import annotations

import os
from typing import Iterable, Iterator

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
    """Écrire les lignes du journal dans `<dossier>/decisions.jsonl` par fichier temporaire puis remplacement."""
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, NOM_JOURNAL_SQUELETTE)
    temporaire = chemin + '.tmp'
    try:
        with open(temporaire, 'w', encoding='utf-8', newline='\n') as fichier:
            for ligne in lignes:
                if '\n' in ligne or '\r' in ligne:
                    raise ValueError('une ligne de journal ne contient aucun saut de ligne')
                fichier.write(ligne + '\n')
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)
    except BaseException:
        if os.path.exists(temporaire):
            os.remove(temporaire)
        raise
    return chemin
