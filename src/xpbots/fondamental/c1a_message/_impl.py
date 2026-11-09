"""Validation pure du format D-11 et des conditions temporelles C05."""
import re

from xpbots.fondamental.c0_types import (ErreurFondamental, MessagePermission, decoder_json_strict,
    devises_pour, instant, millisecondes)
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c0c_configuration import ParametresCommuns

_CLES = frozenset({'schema', 'canonical_symbol', 'sequence', 'issued_at_utc', 'known_at_utc',
    'valid_from_utc', 'valid_until_utc', 'direction', 'risk_state', 'model_version', 'input_snapshot_id'})
_UTC = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z')


class ErreurPermission(ErreurFondamental):
    def __init__(self, detail='INVALIDE'):
        if detail not in ('INVALIDE', 'PERIMEE'):
            raise ErreurFondamental('détail de permission inconnu')
        self.detail = detail
        super().__init__('permission ' + detail)


def _utc(valeur):
    if type(valeur) is not str or _UTC.fullmatch(valeur) is None:
        raise ErreurPermission()
    return instant_depuis_iso(valeur)


def valider_message(message, reception_ms, instant_ms, commun):
    if not isinstance(commun, ParametresCommuns):
        raise ErreurFondamental('paramètres communs réels requis')
    try:
        instant(reception_ms)
        instant(instant_ms)
        if not isinstance(message, MessagePermission) or message.symbole not in commun.universe_priority:
            raise ErreurPermission()
        m = message
        duree = m.valid_until_ms - m.issued_at_ms
        tolerance = millisecondes(commun.fundamental_timestamp_future_tolerance_seconds)
        if (not 0 < duree <= millisecondes(commun.fundamental_max_validity_seconds)
                or m.issued_at_ms > m.known_at_ms or m.issued_at_ms > m.valid_from_ms
                or m.known_at_ms > reception_ms or reception_ms > instant_ms
                or max(m.issued_at_ms, m.known_at_ms, m.valid_from_ms) > instant_ms + tolerance
                or m.valid_from_ms > instant_ms):
            raise ErreurPermission()
        if instant_ms >= m.valid_until_ms:
            raise ErreurPermission('PERIMEE')
        return m
    except ErreurPermission:
        raise
    except (ValueError, TypeError) as erreur:
        raise ErreurPermission() from erreur


def decoder_message(octets, symbole_attendu, reception_ms, instant_ms, commun):
    try:
        devises_pour(symbole_attendu)
        p = decoder_json_strict(octets)
        if set(p) != _CLES or p['schema'] != 'fundamental-permission-v1' or p['canonical_symbol'] != symbole_attendu:
            raise ErreurPermission()
        m = MessagePermission(p['canonical_symbol'], p['sequence'],
            *(_utc(p[n]) for n in ('issued_at_utc', 'known_at_utc', 'valid_from_utc', 'valid_until_utc')),
            p['direction'], p['risk_state'], p['model_version'], p['input_snapshot_id'])
        return valider_message(m, reception_ms, instant_ms, commun)
    except ErreurPermission:
        raise
    except (ValueError, TypeError, KeyError) as erreur:
        raise ErreurPermission() from erreur
