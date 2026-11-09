"""Snapshots synthétiques A10 au format exact, sans modèle ni service externe."""
import json
from robot.outils.configuration import configuration_figee
from xpbots.noyau.c0a_temps import instant_depuis_iso,instant_vers_iso
from xpbots.contexte_ia.c0_types import charger_parametres,empreinte

T=instant_depuis_iso('2026-11-09T08:00:00.000Z')


def parametres():return charger_parametres(configuration_figee())


def evenement(debut=T+60000,fin=T+900000,**changements):
    e=dict(event_id='evenement_1',reason_code='OFFICIAL_UNSCHEDULED_POLICY',canonical_symbols=['EURUSD'],
        valid_from_utc=instant_vers_iso(debut),valid_until_utc=instant_vers_iso(fin),item_id='document_1',
        provider_id=next(iter(sorted(parametres().fournisseurs))))
    e.update(changements);return e


def snapshot(sequence=1,genere=T+120000,evenements=None,**changements):
    p=dict(schema='xp-ai-context-v1',sequence=sequence,generated_at_utc=instant_vers_iso(genere),
        integration_digest=parametres().empreinte_integration,events=[evenement()] if evenements is None else evenements)
    p.update(changements)
    return dict(payload=p,sha256=empreinte(p))


def octets(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode('utf-8')
