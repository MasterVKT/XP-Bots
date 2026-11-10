"""Rapports descriptifs et critères a priori, sans décision de trading."""
from ._impl import (Critere,PreuvesValidation,QualificationSemantique,ObservationCoutDemo,
    produire_rapport,rapport_a11,rapport_a13,comparer_routes,comparer_couts_demo,rapporter_papier,serialiser_rapport)

__all__=('Critere','PreuvesValidation','QualificationSemantique','ObservationCoutDemo',
    'produire_rapport','rapport_a11','rapport_a13','comparer_routes','comparer_couts_demo','rapporter_papier','serialiser_rapport')
