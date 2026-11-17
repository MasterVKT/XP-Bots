"""Codec fermé : aucune classe ni fonction n'est choisie par import du document."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
import json
import math
from zoneinfo import ZoneInfo

from xpbots.orchestration.c0_contrats import ErreurOrchestration
from xpbots.orchestration.c2_moteur import EtatMoteur, CheckpointMoteur, CheckpointJournalMoteur
from ._registre import TYPES_PUBLICS

_ZONES_SUPPORTEES = ('UTC', 'Europe/London')


def _refuser(detail):
    raise ErreurOrchestration('codec : '+detail)


def _json(valeur):
    return json.dumps(valeur, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':'))


def _registre(supplementaires):
    noms = dict(TYPES_PUBLICS)
    classes = {c: n for n, c in TYPES_PUBLICS}
    for paire in supplementaires:
        if not isinstance(paire, tuple) or len(paire) != 2:
            _refuser('registre supplémentaire invalide')
        n, c = paire
        if (type(n) is not str or not n or n.startswith('_') or n in noms
                or not isinstance(c, type) or c in classes
                or not (issubclass(c, Enum) or (is_dataclass(c) and c.__dataclass_params__.frozen))):
            _refuser('classe supplémentaire invalide ou en collision')
        noms[n] = c
        classes[c] = n
    return noms, classes


def _fuseau(v):
    tz = v.tzinfo
    if tz is None:
        return None
    if isinstance(tz, ZoneInfo):
        if tz.key not in _ZONES_SUPPORTEES:
            _refuser('zone non autorisée')
        return tz.key
    if isinstance(tz, timezone):
        return 'fixe'
    _refuser('fuseau non autorisé')


def _encoder(v, classes, profondeur=0):
    if profondeur > 128:
        _refuser('profondeur excessive')
    def enc(x):
        return _encoder(x, classes, profondeur+1)
    if isinstance(v, Enum):
        if type(v) not in classes:
            _refuser('enum inconnu')
        return {'t': 'enum', 'n': classes[type(v)], 'v': v.name}
    if v is None or type(v) in (str, bool, int):
        return v
    if type(v) is float:
        if not math.isfinite(v):
            _refuser('flottant non fini')
        return {'t': 'float', 'v': v.hex()}
    if type(v) is Decimal:
        if not v.is_finite():
            _refuser('Decimal non fini')
        return {'t': 'decimal', 'v': str(v)}
    if type(v) is bytes:
        return {'t': 'bytes', 'v': v.hex()}
    if type(v) in (datetime, time):
        return {'t': type(v).__name__, 'v': v.isoformat(), 'tz': _fuseau(v), 'fold': v.fold}
    if type(v) is date:
        return {'t': 'date', 'v': v.isoformat()}
    if type(v) in (tuple, list, set, frozenset):
        contenu = [enc(x) for x in v]
        if type(v) in (set, frozenset):
            contenu.sort(key=_json)
        return {'t': type(v).__name__, 'v': contenu}
    if isinstance(v, Mapping):
        contenu = [[enc(k), enc(x)] for k, x in v.items()]
        contenu.sort(key=lambda p: _json(p[0]))
        return {'t': 'mapping', 'v': contenu}
    if is_dataclass(v) and not isinstance(v, type) and type(v) in classes:
        return {'t': 'objet', 'n': classes[type(v)],
                'v': {f.name: enc(getattr(v, f.name)) for f in fields(v) if f.init and not f.name.startswith('_')}}
    _refuser('valeur non autorisée')


def _champs(v, attendus):
    if type(v) is not dict or set(v) != set(attendus):
        _refuser('champs du document invalides')


def _decoder(v, noms, profondeur=0):
    if profondeur > 128:
        _refuser('profondeur excessive')
    def dec(x):
        return _decoder(x, noms, profondeur+1)
    if v is None or type(v) in (str, bool, int):
        return v
    if type(v) is not dict or type(v.get('t')) is not str:
        _refuser('valeur non étiquetée')
    t = v['t']
    if t in ('objet', 'enum'):
        _champs(v, ('t', 'n', 'v'))
        if type(v['n']) is not str or v['n'] not in noms:
            _refuser('classe inconnue')
        c = noms[v['n']]
        if t == 'enum':
            if not issubclass(c, Enum) or type(v['v']) is not str or v['v'] not in c.__members__:
                _refuser('membre enum inconnu')
            return c[v['v']]
        if not is_dataclass(c):
            _refuser('classe sans champs')
        attendus = tuple(f.name for f in fields(c) if f.init and not f.name.startswith('_'))
        _champs(v['v'], attendus)
        resultat = c(**{k: dec(x) for k, x in v['v'].items()})
        if isinstance(resultat, (EtatMoteur, CheckpointMoteur, CheckpointJournalMoteur)):
            resultat.verifier()
        return resultat
    if t in ('datetime', 'time'):
        _champs(v, ('t', 'v', 'tz', 'fold'))
        if (type(v['v']) is not str or type(v['fold']) is not int or v['fold'] not in (0, 1)
                or v['tz'] not in (None, 'fixe')+_ZONES_SUPPORTEES):
            _refuser('date ou fuseau invalide')
        r = (datetime if t == 'datetime' else time).fromisoformat(v['v'])
        zone_sans_date = t == 'time' and v['tz'] in _ZONES_SUPPORTEES and r.tzinfo is None
        if not zone_sans_date and (r.tzinfo is None) != (v['tz'] is None):
            _refuser('fuseau incohérent')
        if v['tz'] in _ZONES_SUPPORTEES:
            initial = r.utcoffset()
            r = r.replace(tzinfo=ZoneInfo(v['tz']), fold=v['fold'])
            if not zone_sans_date and r.utcoffset() != initial:
                _refuser('décalage incompatible avec la zone')
        return r.replace(fold=v['fold'])
    _champs(v, ('t', 'v'))
    x = v['v']
    if t in ('float', 'decimal', 'bytes', 'date'):
        if type(x) is not str:
            _refuser('scalaire mal encodé')
        if t == 'float':
            r = float.fromhex(x)
            if not math.isfinite(r):
                _refuser('flottant non fini')
            return r
        if t == 'decimal':
            r = Decimal(x)
            if not r.is_finite():
                _refuser('Decimal non fini')
            return r
        if t == 'bytes':
            return bytes.fromhex(x)
        return date.fromisoformat(x)
    if t in ('tuple', 'list', 'set', 'frozenset', 'mapping'):
        if type(x) is not list:
            _refuser('conteneur mal encodé')
        if t == 'mapping':
            r = {}
            for p in x:
                if type(p) is not list or len(p) != 2:
                    _refuser('paire invalide')
                k = dec(p[0])
                if k in r:
                    _refuser('clé en double ou en collision')
                r[k] = dec(p[1])
            return r
        valeurs = [dec(e) for e in x]
        if t in ('set', 'frozenset') and len(set(valeurs)) != len(valeurs):
            _refuser('élément en double ou en collision')
        return {'tuple': tuple, 'list': list, 'set': set, 'frozenset': frozenset}[t](valeurs)
    _refuser('étiquette inconnue')


def _paires(paires):
    r = {}
    for k, v in paires:
        if k in r:
            _refuser('clé JSON en double')
        r[k] = v
    return r


def serialiser_valeur(valeur, *, types_supplementaires=()):
    """Retourne des octets JSON canoniques ; seuls les types déclarés sont admis."""
    try:
        _, classes = _registre(types_supplementaires)
        return _json({'schema': 'xp-valeur-persistante-v1', 'valeur': _encoder(valeur, classes)}).encode('utf-8')
    except ErreurOrchestration:
        raise
    except (ValueError, TypeError, KeyError, ArithmeticError, RecursionError) as e:
        raise ErreurOrchestration('codec : valeur invalide') from e


def deserialiser_valeur(octets, *, types_supplementaires=()):
    """Reconstruit par les constructeurs publics et vérifie les sceaux durables."""
    try:
        if type(octets) is not bytes:
            _refuser('octets requis')
        noms, _ = _registre(types_supplementaires)
        v = json.loads(octets.decode('utf-8'), object_pairs_hook=_paires,
                       parse_constant=lambda _: _refuser('nombre JSON non fini'))
        _champs(v, ('schema', 'valeur'))
        if v['schema'] != 'xp-valeur-persistante-v1':
            _refuser('version inconnue')
        return _decoder(v['valeur'], noms)
    except ErreurOrchestration:
        raise
    except (ValueError, TypeError, KeyError, ArithmeticError, RecursionError) as e:
        raise ErreurOrchestration('codec : document invalide') from e
