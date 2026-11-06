"""Implémentation de la couche 0b (nombres). Révisable à comportement constant sous harnais complet."""
from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, Context, Decimal, InvalidOperation, localcontext
from enum import Enum
import math

EPSILON_GRILLE = Decimal('1e-8')
_CONTEXTE = Context(prec=50)


class ErreurNombre(ValueError):
    """Nombre, pas ou arrondi refusés."""


class Arrondi(Enum):
    BAS = 'BAS'
    HAUT = 'HAUT'


def decimal_depuis(valeur: int | float | Decimal | str) -> Decimal:
    if isinstance(valeur, bool):
        raise ErreurNombre('booléen refusé')
    if isinstance(valeur, float):
        if not math.isfinite(valeur):
            raise ErreurNombre(f'flottant non fini refusé : {valeur!r}')
        resultat = Decimal(repr(valeur))
    elif isinstance(valeur, int):
        resultat = Decimal(valeur)
    elif isinstance(valeur, Decimal):
        resultat = valeur
    elif isinstance(valeur, str):
        try:
            resultat = Decimal(valeur.strip())
        except InvalidOperation as erreur:
            raise ErreurNombre(f'texte décimal illisible : {valeur!r}') from erreur
    else:
        raise ErreurNombre(f'type non pris en charge : {type(valeur).__name__}')
    if not resultat.is_finite():
        raise ErreurNombre(f'décimal non fini refusé : {valeur!r}')
    return resultat


def _pas(pas: int | float | Decimal | str) -> Decimal:
    resultat = decimal_depuis(pas)
    if resultat <= 0:
        raise ErreurNombre(f'pas de grille strictement positif exigé : {pas!r}')
    return resultat


def arrondir_sur_grille(valeur: int | float | Decimal | str, pas: int | float | Decimal | str,
                        sens: Arrondi) -> Decimal:
    if not isinstance(sens, Arrondi):
        raise ErreurNombre('sens d\'arrondi inconnu')
    nombre, grille = decimal_depuis(valeur), _pas(pas)
    with localcontext(_CONTEXTE):
        quotient = nombre / grille
        if sens is Arrondi.BAS:
            multiple = (quotient + EPSILON_GRILLE).to_integral_value(rounding=ROUND_FLOOR)
        else:
            multiple = (quotient - EPSILON_GRILLE).to_integral_value(rounding=ROUND_CEILING)
        return (multiple * grille).quantize(grille)


def est_sur_grille(valeur: int | float | Decimal | str, pas: int | float | Decimal | str) -> bool:
    nombre, grille = decimal_depuis(valeur), _pas(pas)
    with localcontext(_CONTEXTE):
        return nombre % grille == 0
