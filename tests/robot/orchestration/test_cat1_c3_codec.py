"""Catégorie 1 : codec fermé, précision et refus de documents hostiles."""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal, getcontext
import json
import math
import unittest
from zoneinfo import ZoneInfo

from xpbots.orchestration.c0_contrats import ErreurOrchestration, FabriqueStrategie
from xpbots.orchestration.c3_codec import serialiser_valeur, deserialiser_valeur
from xpbots.noyau.c1c_domaine import Sens


@dataclass(frozen=True)
class ValeurLocale:
    contenu: tuple


class TestCodecValeurs(unittest.TestCase):
    def tour(self, v, **kw):
        b = serialiser_valeur(v, **kw)
        r = deserialiser_valeur(b, **kw)
        self.assertEqual(r, v)
        self.assertEqual(serialiser_valeur(r, **kw), b)
        return r

    def document(self, v):
        return json.dumps({'schema': 'xp-valeur-persistante-v1', 'valeur': v}).encode()

    def test_primitifs_et_conteneurs_restent_distincts(self):
        v = (None, True, False, 1, -2, 'é', b'\x00\xff', [], (), {1, 2}, frozenset({3}))
        r = self.tour(v)
        self.assertEqual(tuple(map(type, r)), tuple(map(type, v)))
        self.assertEqual(type(self.tour(Sens.ACHAT)), Sens)

    def test_precision_decimal_float_et_zero_negatif(self):
        avant = getcontext().copy()
        v = (Decimal('-0.000'), Decimal('123456789.123456789000'), -0.0, 1.0000000000000002)
        r = self.tour(v)
        self.assertEqual(r[0].as_tuple(), v[0].as_tuple())
        self.assertEqual(math.copysign(1, r[2]), -1)
        self.assertEqual(getcontext().prec, avant.prec)
        self.assertEqual(r[1].as_tuple(), v[1].as_tuple())

    def test_dates_et_heures_du_changement_britannique(self):
        london = ZoneInfo('Europe/London')
        for fold in (0, 1):
            v = datetime(2026, 10, 25, 1, 30, tzinfo=london, fold=fold)
            r = self.tour(v)
            self.assertEqual(r.tzinfo.key, 'Europe/London')
            self.assertEqual(r.fold, fold)
            self.assertEqual(r.timestamp(), v.timestamp())
        for v in (date(2026, 11, 10), time(12, 31, 4, 123456, fold=1),
                  datetime(2026, 1, 1, tzinfo=timezone.utc),
                  time(2, tzinfo=timezone(timedelta(hours=3))), time(1, tzinfo=london, fold=1)):
            self.tour(v)

    def test_mapping_cles_typees_et_canonicalite(self):
        v = {1: 'entier', '1': 'texte', (2, 3): Decimal('1.0')}
        self.tour(v)
        self.assertEqual(serialiser_valeur(v), serialiser_valeur(dict(reversed(tuple(v.items())))))
        self.assertEqual(serialiser_valeur({1, 2}), serialiser_valeur({2, 1}))

    def test_registre_fourni_par_le_consommateur_uniquement(self):
        extra = (('consommateur.ValeurLocale', ValeurLocale),)
        b = serialiser_valeur(ValeurLocale((Decimal('2.00'),)), types_supplementaires=extra)
        with self.assertRaises(ErreurOrchestration): deserialiser_valeur(b)
        self.tour(ValeurLocale((Decimal('2.00'),)), types_supplementaires=extra)
        for mauvais in ((('x', ValeurLocale), ('x', ValeurLocale)),
                        (('xpbots.noyau.c1c_domaine.Sens', ValeurLocale),),
                        (('x', dict),), (('x', Sens),)):
            with self.assertRaises(ErreurOrchestration): serialiser_valeur(None, types_supplementaires=mauvais)

    def test_aucune_fonction_fabrique_ou_classe_arbitraire(self):
        for v in (lambda: None, object(), FabriqueStrategie('X', lambda *a: None)):
            with self.assertRaises(ErreurOrchestration): serialiser_valeur(v)
        for n in ('os.system', 'builtins.eval', 'xpbots.orchestration.c0_contrats.FabriqueStrategie'):
            with self.assertRaises(ErreurOrchestration):
                deserialiser_valeur(self.document({'t': 'objet', 'n': n, 'v': {}}))

    def test_versions_champs_et_etiquettes_inconnus(self):
        for b in (b'{}', b'[]', b'{"schema":"v2","valeur":null}',
                  b'{"schema":"xp-valeur-persistante-v1","valeur":null,"extra":1}',
                  self.document({'t': 'pickle', 'v': ''}), self.document([]), self.document(1.2)):
            with self.assertRaises(ErreurOrchestration): deserialiser_valeur(b)

    def test_json_utf8_strict_et_doublons_a_tout_niveau(self):
        for b in (b'\xff', b'{"schema":"xp-valeur-persistante-v1","valeur":0,"valeur":1}',
                  b'{"schema":"xp-valeur-persistante-v1","valeur":{"t":"bytes","v":"00","v":"ff"}}'):
            with self.assertRaises(ErreurOrchestration): deserialiser_valeur(b)
        with self.assertRaises(ErreurOrchestration): deserialiser_valeur('pas des octets')

    def test_nombres_non_finis_refuses_dans_toutes_les_formes(self):
        for v in (float('nan'), float('inf'), Decimal('NaN'), Decimal('-Infinity')):
            with self.assertRaises(ErreurOrchestration): serialiser_valeur(v)
        for v in ({'t': 'float', 'v': 'inf'}, {'t': 'decimal', 'v': 'NaN'}):
            with self.assertRaises(ErreurOrchestration): deserialiser_valeur(self.document(v))
        with self.assertRaises(ErreurOrchestration):
            deserialiser_valeur(b'{"schema":"xp-valeur-persistante-v1","valeur":NaN}')

    def test_doublons_et_collisions_dans_collections(self):
        for v in ({'t': 'mapping', 'v': [[True, 0], [1, 1]]},
                  {'t': 'mapping', 'v': [['x', 0], ['x', 1]]},
                  {'t': 'set', 'v': [True, 1]},
                  {'t': 'mapping', 'v': [[{'t': 'list', 'v': []}, 1]]}):
            with self.assertRaises(ErreurOrchestration): deserialiser_valeur(self.document(v))

    def test_constructeurs_reels_et_champs_exacts(self):
        n = 'xpbots.noyau.c1b_instrument.Intervalle'
        for v in ({'debut_ms': 2, 'fin_ms': 1}, {'debut_ms': 1},
                  {'debut_ms': 1, 'fin_ms': 2, '_effectives': []}):
            with self.assertRaises(ErreurOrchestration):
                deserialiser_valeur(self.document({'t': 'objet', 'n': n, 'v': v}))
        with self.assertRaises(ErreurOrchestration):
            deserialiser_valeur(self.document({'t': 'enum', 'n': 'xpbots.noyau.c1c_domaine.Sens', 'v': 'NOUVEAU'}))

    def test_fuseaux_incoherents_et_profondeur_refuses(self):
        for tz, fold, iso in (('os/secret', 0, '2026-01-01T00:00:00+00:00'),
                              ('UTC', True, '2026-01-01T00:00:00+00:00'),
                              ('Europe/London', 0, '2026-07-01T00:00:00+00:00')):
            with self.assertRaises(ErreurOrchestration):
                deserialiser_valeur(self.document({'t': 'datetime', 'v': iso, 'tz': tz, 'fold': fold}))
        v = None
        for _ in range(130): v = (v,)
        with self.assertRaises(ErreurOrchestration): serialiser_valeur(v)
