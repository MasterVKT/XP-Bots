"""Fabrique de ticks synthétiques (document 03, §4), première version du squelette.

À partir de bougies voulues, elle produit des ticks Bid/Ask reproductibles, sans hasard : quatre ticks par
bougie à des décalages fixes (ouverture, puis bas et haut dans l'ordre réaliste, puis clôture), un spread
constant, des numéros de séquence croissants. Le tick d'ouverture tombe exactement sur le début de la bougie :
c'est le tick de frontière qui clôt la bougie précédente (C03.2). Les prix sont des textes décimaux à cinq
décimales, écrits tels quels dans le fichier CSV canonique (document 08, §6.1), jamais des prix réels.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

LONDRES = ZoneInfo('Europe/London')
COLONNES = ('canonical_symbol', 'broker_symbol', 'time_utc_ms', 'sequence', 'bid', 'ask')
DECALAGES_MS = (0, 300_000, 600_000, 899_000)
PAS = Decimal('0.00001')


@dataclass(frozen=True)
class BougieVoulue:
    """Bougie Bid à reproduire ; prix en texte décimal."""

    debut_ms: int
    ouverture: str
    haut: str
    bas: str
    cloture: str


@dataclass(frozen=True)
class TickFabrique:
    symbole: str
    symbole_courtier: str
    instant_ms: int
    sequence: int
    bid: str
    ask: str


def _texte(prix: Decimal) -> str:
    return str(prix.quantize(PAS))


def ticks_de_bougies(symbole: str, bougies: list[BougieVoulue], *, spread: str = '0.00010',
                     symbole_courtier: str | None = None, sequence_initiale: int = 1) -> list[TickFabrique]:
    """Quatre ticks par bougie, aux décalages `DECALAGES_MS` depuis son début ; Ask = Bid + spread."""
    ecart = Decimal(spread)
    courtier = symbole_courtier or symbole
    ticks: list[TickFabrique] = []
    sequence = sequence_initiale
    for bougie in bougies:
        o, h, l, c = (Decimal(v) for v in (bougie.ouverture, bougie.haut, bougie.bas, bougie.cloture))
        if not (l <= min(o, c) and max(o, c) <= h):
            raise ValueError(f'bougie incohérente à {bougie.debut_ms}')
        milieu = (l, h) if c >= o else (h, l)
        for decalage, bid in zip(DECALAGES_MS, (o, *milieu, c)):
            ticks.append(TickFabrique(symbole, courtier, bougie.debut_ms + decalage, sequence, _texte(bid),
                                      _texte(bid + ecart)))
            sequence += 1
    return ticks


ORIGINE = datetime(1970, 1, 1, tzinfo=timezone.utc)


def instant_ms(moment: datetime) -> int:
    """Instant UTC en millisecondes d'un datetime conscient de son fuseau (arithmétique entière exacte)."""
    return (moment - ORIGINE) // timedelta(milliseconds=1)


def bornes_journee_londres(jour: date) -> tuple[int, int]:
    """Début et fin UTC, en millisecondes, du jour civil de Londres (23, 24 ou 25 heures)."""
    debut = datetime.combine(jour, time(0), tzinfo=LONDRES)
    fin = datetime.combine(jour + timedelta(days=1), time(0), tzinfo=LONDRES)
    return instant_ms(debut), instant_ms(fin)


def journee_londres(jour: date, *, symbole: str = 'EURUSD', duree_ms: int,
                    prix_base: str = '1.10000') -> tuple[list[BougieVoulue], list[TickFabrique]]:
    """Bougies régulières couvrant tout le jour de Londres, puis un tick de frontière à minuit suivant.

    Le dernier tick, exactement à la fin du jour, clôt la dernière bougie du jour et ouvre une bougie du
    lendemain qui reste ouverte. Motif de prix déterministe : une vague de dix bougies.
    """
    debut, fin = bornes_journee_londres(jour)
    if (fin - debut) % duree_ms:
        raise ValueError('la durée de bougie ne divise pas la journée')
    base = Decimal(prix_base)
    bougies = []
    for indice in range((fin - debut) // duree_ms):
        ouverture = base + PAS * (5 * (indice % 10))
        cloture = ouverture + PAS * (3 if indice % 2 == 0 else -2)
        haut = max(ouverture, cloture) + PAS * 4
        bas = min(ouverture, cloture) - PAS * 4
        bougies.append(BougieVoulue(debut + indice * duree_ms, _texte(ouverture), _texte(haut), _texte(bas),
                                    _texte(cloture)))
    ticks = ticks_de_bougies(symbole, bougies)
    dernier = bougies[-1]
    ticks.append(TickFabrique(symbole, symbole, fin, ticks[-1].sequence + 1, dernier.cloture,
                              _texte(Decimal(dernier.cloture) + Decimal('0.00010'))))
    return bougies, ticks


def lignes_csv(ticks: list[TickFabrique]) -> list[str]:
    """Lignes du format canonique, en-tête compris."""
    return [','.join(COLONNES)] + [
        f'{t.symbole},{t.symbole_courtier},{t.instant_ms},{t.sequence},{t.bid},{t.ask}' for t in ticks]


def ecrire_csv(chemin: Path, ticks: list[TickFabrique]) -> Path:
    """Écrire le fichier CSV canonique (UTF-8, fins de ligne LF) dans un dossier temporaire du test."""
    chemin.write_text('\n'.join(lignes_csv(ticks)) + '\n', encoding='utf-8', newline='\n')
    return chemin
