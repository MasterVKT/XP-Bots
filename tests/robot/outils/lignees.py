"""Registre de propriété des fichiers de `src/xpbots/` entre les deux lignées de construction (robot 1 EMA_V3, robot London).

Les deux lignées partagent le paquet `xpbots` et certains noms de sous-paquets (`noyau`, `app`, `execution`) : chaque garde
transverse d'une lignée doit ignorer les fichiers de l'autre. Les motifs sont des `fnmatch` sur le chemin relatif à la racine
du dépôt (même format que `exclure` dans `carte.json`). Un fichier absent des deux registres (par exemple un `__init__.py`
partagé ou un fichier neuf) est contrôlé par les deux gardes : l'ajout d'un fichier dans un paquet partagé force ainsi à
déclarer son propriétaire ici, et dans `exclure` des deux cartes composites (`mcl/robot-ema-v3/` et `mcl/robot-london-v3/`).
Voir docs/architecture/COEXISTENCE_ROBOT1_LONDON.md.
"""
from fnmatch import fnmatch

ROBOT1 = (
    'src/xpbots/noyau/config.py', 'src/xpbots/noyau/decisions.py', 'src/xpbots/noyau/journal_schema.py',
    'src/xpbots/noyau/json_canonique.py', 'src/xpbots/noyau/marche.py', 'src/xpbots/noyau/ports.py',
    'src/xpbots/noyau/temps.py', 'src/xpbots/donnees_temps/*', 'src/xpbots/moteur_ema/*',
    'src/xpbots/app/rejeu.py', 'src/xpbots/app/segments_minimaux.py',
)
LONDON = (
    'src/xpbots/noyau/c[0-9]*', 'src/xpbots/donnees/*', 'src/xpbots/london/*', 'src/xpbots/orchestration/*',
    'src/xpbots/rejeu/*', 'src/xpbots/infra/*', 'src/xpbots/execution/squelette.py', 'src/xpbots/app/rejeu_squelette.py',
)


def appartient(chemin_relatif_au_depot: str, registre: tuple[str, ...]) -> bool:
    """Vrai si le chemin (séparateur `/`) correspond à un motif du registre."""
    return any(fnmatch(chemin_relatif_au_depot, motif) for motif in registre)
