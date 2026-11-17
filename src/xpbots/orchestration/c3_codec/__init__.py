"""Représentation durable, typée et pure des valeurs publiques du moteur."""
from ._impl import serialiser_valeur, deserialiser_valeur

__all__ = ('serialiser_valeur', 'deserialiser_valeur')
