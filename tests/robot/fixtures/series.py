"""Séries synthétiques déterministes en mémoire pour les tests de `donnees-temps` ; aucun prix réel."""
from __future__ import annotations

import random
from decimal import Decimal

from xpbots.noyau.marche import Bougie, Tick
from xpbots.noyau.temps import Instant

M15 = 900_000
QUANTUM = Decimal('0.00001')
DEBUT_LUNDI = 1793664000000  # lundi 2026-11-02 00:00:00.000 UTC


def ticks_bougies(symbole: str, debut_ms: int, nb_bougies: int, graine: int = 7, ticks_par_bougie: int = 3,
                  prix: Decimal = Decimal('1.10000'), periode_ms: int = M15, sequence_depart: int = 1,
                  spread: Decimal = Decimal('0.00008')) -> list[Tick]:
    """Ticks strictement à l'intérieur de chaque intervalle [T, T+période), marche aléatoire au quantum."""
    alea = random.Random(graine)
    ticks, sequence = [], sequence_depart
    for i in range(nb_bougies):
        base = debut_ms + i * periode_ms
        for decalage in sorted(alea.sample(range(1, periode_ms), ticks_par_bougie)):
            prix = max(QUANTUM, prix + QUANTUM * alea.randint(-4, 4))
            ticks.append(Tick(symbole, symbole + 'synth', Instant(base + decalage, sequence), prix, prix + spread))
            sequence += 1
    return ticks


def bougies_directes(symbole: str, debut_ms: int, nb: int, graine: int = 3) -> list[Bougie]:
    """Bougies valides consécutives construites directement (sans couche 1b)."""
    alea = random.Random(graine)
    c, bougies = Decimal('1.10000'), []
    for i in range(nb):
        o = c
        c = max(QUANTUM, o + QUANTUM * alea.randint(-30, 30))
        h = max(o, c) + QUANTUM * alea.randint(0, 10)
        l = min(o, c) - QUANTUM * alea.randint(0, 10)  # noqa: E741
        bougies.append(Bougie(symbole, M15 // 1000, debut_ms + i * M15, o, h, l, c, 3, True))
    return bougies


def bougies_tendances(symbole: str, debut_ms: int, nb: int, graine: int = 1) -> list[Bougie]:
    """Bougies valides consécutives à régimes de tendance (dérive haussière, baissière ou nulle), au quantum.

    Série synthétique pour exercer la méthode S01 (armements, replis, reprises) ; aucun prix réel.
    """
    alea = random.Random(graine)
    c, bougies, derive, reste = Decimal('1.10000'), [], 0, 0
    for i in range(nb):
        if reste == 0:
            derive, reste = alea.choice((-6, 0, 6)), alea.randint(60, 400)
        reste -= 1
        o = c
        c = o + QUANTUM * (derive + alea.randint(-40, 40))
        h = max(o, c) + QUANTUM * alea.randint(0, 25)
        l = min(o, c) - QUANTUM * alea.randint(0, 25)  # noqa: E741
        bougies.append(Bougie(symbole, M15 // 1000, debut_ms + i * M15, o, h, l, c, 4, True))
    return bougies


def ticks_depuis_bougies(bougies: list[Bougie], spread: Decimal = Decimal('0.00008'),
                         sequence_depart: int = 1) -> list[Tick]:
    """Quatre ticks par bougie (O, extrême, autre extrême, C) strictement dans [T, T+900 s) : OHLC Bid reproduits."""
    ticks, sequence = [], sequence_depart
    for i, b in enumerate(bougies):
        extremes = (b.l, b.h) if i % 2 else (b.h, b.l)
        for decalage, bid in zip((1_000, 200_000, 400_000, 800_000), (b.o, *extremes, b.c)):
            ticks.append(Tick(b.symbole, b.symbole + 'synth', Instant(b.ouverture_ms + decalage, sequence), bid,
                              bid + spread))
            sequence += 1
    return ticks
