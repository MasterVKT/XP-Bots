"""Messages et exports synthétiques au format de frontière exact, sans source externe."""
import json
from datetime import datetime, timedelta, timezone
from robot.outils.configuration import configuration_figee
from xpbots.noyau.c0a_temps import instant_depuis_iso, instant_vers_iso
from xpbots.fondamental.c0_types import millisecondes
from xpbots.fondamental.c0_types import TableImportance
from xpbots.noyau.c0a_temps import instant_depuis_datetime, instant_vers_datetime

T = instant_depuis_iso('2026-11-09T08:00:00.000Z')


def commun():
    return configuration_figee().technique.commun


def message(symbole='EURUSD', **changements):
    p = dict(schema='fundamental-permission-v1', canonical_symbol=symbole, sequence=1,
        issued_at_utc=instant_vers_iso(T), known_at_utc=instant_vers_iso(T + 100),
        valid_from_utc=instant_vers_iso(T),
        valid_until_utc=instant_vers_iso(T + millisecondes(commun().fundamental_max_validity_seconds)),
        direction='ANY', risk_state='ALLOW', model_version='MODELE_SYNTHETIQUE_V1', input_snapshot_id='SYNTHETIQUE_1')
    p.update(changements)
    return p


def octets(objet):
    return json.dumps(objet, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


class ConversionServeurScenario:
    """Frontière externe synthétique : décalage déclaré, sans déduction du document reçu."""
    def __init__(self, decalage_heures=2): self.decalage = timedelta(hours=decalage_heures)

    def __call__(self, texte):
        dt = datetime.strptime(texte, '%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc) - self.decalage
        return instant_depuis_datetime(dt)


def heure_native(instant_ms, decalage_heures=2):
    return (instant_vers_datetime(instant_ms) + timedelta(hours=decalage_heures)).strftime('%Y.%m.%d %H:%M:%S')


def table_importance():
    return TableImportance('MQL5_SYNTHETIQUE', 'TABLE_TEST_V1', ['CALENDAR_IMPORTANCE_HIGH'])


def evenement(instant_ms=T+1800000, **changements):
    e = dict(id_valeur=1, id_evenement=2, code='ANNONCE_TEST', nom='Annonce synthétique', devise='USD',
        importance='CALENDAR_IMPORTANCE_HIGH', type='EVENT', secteur='MONETARY',
        heure_serveur=heure_native(instant_ms), revision=0)
    e.update(changements)
    return e


def calendrier(version=1, export_ms=T, evenements=(), **changements):
    debut = instant_depuis_datetime(instant_vers_datetime(export_ms).replace(hour=0, minute=0, second=0,
        microsecond=0) - timedelta(days=1))
    fin = export_ms + millisecondes(commun().news_forward_coverage_seconds + commun().news_calendar_max_age_seconds) + 3600000
    p = dict(schema='xp-export-calendrier-v1', version=version, export_serveur=heure_native(export_ms),
        export_gmt=heure_native(export_ms, 0), fenetre_debut_serveur=heure_native(debut),
        fenetre_fin_serveur=heure_native(fin), evenements=list(evenements))
    p.update(changements)
    return p
