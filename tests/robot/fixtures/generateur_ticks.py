"""Générateur déterministe de ticks synthétiques au format du cahier de données (§2) ; aucun prix réel.

Régénérer les fixtures versionnées : `python tests/robot/fixtures/generateur_ticks.py --ecrire tests/robot/fixtures`.
Un test vérifie que la régénération reproduit les octets versionnés.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

ENTETE = ('canonical_symbol', 'broker_symbol', 'time_utc_ms', 'sequence', 'bid', 'ask')
QUANTUM = Decimal('0.00001')
NOM_TICKS = 'squelette_ticks.csv'
NOM_MANIFESTE = 'squelette_manifeste.json'


@dataclass(frozen=True)
class ProfilSynthetique:
    symbole: str
    symbole_courtier: str
    prix_initial: Decimal
    spread: Decimal
    couverture: tuple[tuple[int, int], ...]
    seances: tuple[tuple[int, int], ...]


# Mercredi 4 novembre 2026, 08:00–10:00 UTC, marché ouvert ; GBPUSD a une interruption déclarée de 08:40 à 08:50.
DEBUT_MS = 1793779200000
FIN_MS = DEBUT_MS + 2 * 3_600_000
PROFILS = (
    ProfilSynthetique('EURUSD', 'EURUSDsynth', Decimal('1.10000'), Decimal('0.00008'), ((DEBUT_MS, FIN_MS),),
                      ((DEBUT_MS, FIN_MS),)),
    ProfilSynthetique('GBPUSD', 'GBPUSDsynth', Decimal('1.30000'), Decimal('0.00012'),
                      ((DEBUT_MS, DEBUT_MS + 2_400_000), (DEBUT_MS + 3_000_000, FIN_MS)), ((DEBUT_MS, FIN_MS),)),
)
# Tick EURUSD exactement à une frontière M15 (08:15:00.000) et égalité de milliseconde entre symboles.
INSTANTS_IMPOSES = {'EURUSD': (DEBUT_MS + 900_000, DEBUT_MS + 1_234_567), 'GBPUSD': (DEBUT_MS + 1_234_567,)}


def _instants(profil: ProfilSynthetique, alea: random.Random, ecart_max_ms: int) -> list[int]:
    instants = set(INSTANTS_IMPOSES.get(profil.symbole, ()))
    for debut, fin in profil.couverture:
        t = debut + alea.randint(1, ecart_max_ms)
        while t < fin:
            instants.add(t)
            t += alea.randint(1, ecart_max_ms)
    return sorted(t for t in instants if any(a <= t < b for a, b in profil.couverture))


def generer(graine: int = 20261104, ecart_max_ms: int = 30_000) -> tuple[str, str]:
    """Texte CSV (LF) et manifeste JSON (LF) déterministes pour la graine donnée."""
    alea = random.Random(graine)
    evenements = []
    for rang, profil in enumerate(PROFILS):
        prix = profil.prix_initial
        for t in _instants(profil, alea, ecart_max_ms):
            prix = max(QUANTUM, prix + QUANTUM * alea.randint(-3, 3))
            evenements.append((t, rang, profil, prix))
    evenements.sort(key=lambda e: (e[0], e[1]))
    lignes = [','.join(ENTETE)]
    for sequence, (t, _, profil, bid) in enumerate(evenements, start=1):
        bid = bid.quantize(QUANTUM)
        lignes.append(f'{profil.symbole},{profil.symbole_courtier},{t},{sequence},{bid},{(bid + profil.spread).quantize(QUANTUM)}')
    manifeste = {
        'schema': 'xp-fixture-manifeste-v2', 'origine': 'synthetique', 'fuseau': 'UTC',
        'description': 'Ticks synthétiques déterministes du squelette (graine %d) ; aucun prix réel.' % graine,
        'fin_donnees_ms': FIN_MS,
        'symboles': {p.symbole: {'symbole_courtier': p.symbole_courtier, 'couverture': [list(c) for c in p.couverture],
                                 'seances': [list(s) for s in p.seances]} for p in PROFILS},
    }
    return '\n'.join(lignes) + '\n', json.dumps(manifeste, ensure_ascii=False, indent=2) + '\n'


def ecrire(dossier: Path, graine: int = 20261104) -> tuple[Path, Path]:
    texte_ticks, texte_manifeste = generer(graine)
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_ticks, chemin_manifeste = dossier / NOM_TICKS, dossier / NOM_MANIFESTE
    chemin_ticks.write_bytes(texte_ticks.encode('utf-8'))
    chemin_manifeste.write_bytes(texte_manifeste.encode('utf-8'))
    return chemin_ticks, chemin_manifeste


if __name__ == '__main__':
    parseur = argparse.ArgumentParser(description='Régénère les fixtures synthétiques du squelette.')
    parseur.add_argument('--ecrire', type=Path, required=True, help='dossier de destination')
    print(*ecrire(parseur.parse_args().ecrire), sep='\n')
