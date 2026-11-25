"""Calendrier D12 exact et mapping synthétiques, sans déduction du nom d'annonce."""
from robot.outils.fondamental import (ConversionServeurScenario, table_importance,
    calendrier, evenement, octets)
from xpbots.fondamental.c1b_annonces import GardeAnnonces
from xpbots.service_ia.c2a_veto import CorrespondanceCalendrier, TableAppariement, apparier_calendrier


def garde(r,d,*,annonces=(),export_ms=None,**kw):
    t=d.collecte_ms if export_ms is None else export_ms
    g=GardeAnnonces(r.configuration.technique.commun,ConversionServeurScenario())
    reception=g.recevoir(octets(calendrier(export_ms=t,evenements=annonces,**kw)),t,table_importance())
    if not reception.acceptee:raise AssertionError(reception.raison)
    return g


def mapping(d,*,correspondances=(),**kw):
    v=dict(fournisseur=table_importance().fournisseur,version='MAPPING_SYNTHETIQUE_V1',
        known_at_ms=d.collecte_ms,complete=True,correspondances=correspondances)
    v.update(kw);return TableAppariement(**v)


def appariement(r,d,*,annonces=(),correspondances=()):
    return apparier_calendrier(r,garde(r,d,annonces=annonces),mapping(d,correspondances=correspondances),
        d,d.collecte_ms,source_valide=True)
