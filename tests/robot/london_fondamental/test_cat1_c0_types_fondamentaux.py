"""Catégorie 1, couche 0 : types, table C05 exacte et JSON strict des deux protocoles."""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
import unittest

from xpbots.fondamental.c0_types import (Annonce, DirectionFondamentale, ErreurFondamental, EtatRisque,
    MessagePermission, TableImportance, VersionCalendrier, decoder_json_strict, devises_pour,
    entier, millisecondes, texte)
from xpbots.noyau.c1b_instrument import Intervalle


def annonce(**changements):
    return replace(Annonce(1, 2, 'TEST', 'Annonce synthétique', 'USD', 'CALENDAR_IMPORTANCE_HIGH',
        'EVENT', 'MONETARY', '2026.11.09 10:00:00', 1000, 0, 500), **changements)


class TestTypesFondamentaux(unittest.TestCase):
    def test_table_devises_exactement_c05(self):
        # Spécification C05 : EUR+USD, GBP+USD, USD seulement pour l'or.
        self.assertEqual({s: devises_pour(s) for s in ('EURUSD', 'GBPUSD', 'XAUUSD')},
            {'EURUSD': ('EUR', 'USD'), 'GBPUSD': ('GBP', 'USD'), 'XAUUSD': ('USD',)})
        for s in ('EURUSDr', 'USDJPY', '', None, []):
            with self.subTest(s=s), self.assertRaises(ValueError): devises_pour(s)

    def test_enumerations_exactes(self):
        self.assertEqual({v.value for v in DirectionFondamentale}, {'ANY', 'LONG_ONLY', 'SHORT_ONLY'})
        self.assertEqual({v.value for v in EtatRisque}, {'ALLOW', 'NO_NEW', 'FLATTEN'})

    def test_json_strict_et_decimal_exact(self):
        self.assertEqual(decoder_json_strict('{"nom":"é","n":0.1}'.encode()), {'nom': 'é', 'n': Decimal('.1')})
        for b in (b'{"n":1,"n":2}', b'{"a":{"n":1,"n":2}}', b'{"n":NaN}', b'{"n":Infinity}',
                  b'[]', b'null', b'{} {}', b'\xff', b'\xef\xbb\xbf{}', '{}'):
            with self.subTest(b=b), self.assertRaises(ErreurFondamental): decoder_json_strict(b)

    def test_scalaires_et_conversion_sans_seuil(self):
        self.assertEqual(millisecondes(3), 3000)
        self.assertEqual(millisecondes(0), 0)
        for v in (True, -1, 1.0, '1'):
            with self.subTest(v=v), self.assertRaises(ErreurFondamental): entier(v)
        for v in ('', '  ', '\ud800', None):
            with self.subTest(v=repr(v)), self.assertRaises(ErreurFondamental): texte(v)

    def test_message_immuable_et_valide_structurellement(self):
        m = MessagePermission('EURUSD', 1, 100, 200, 100, 900, 'ANY', 'ALLOW', 'synthetique', 's1')
        self.assertIs(m.direction, DirectionFondamentale.ANY)
        self.assertIs(m.risk_state, EtatRisque.ALLOW)
        with self.assertRaises(FrozenInstanceError): m.sequence = 2
        for changements in ({'sequence': True}, {'direction': 'BOTH'}, {'risk_state': ''}, {'model_version': ''}):
            with self.subTest(c=changements), self.assertRaises(ValueError): replace(m, **changements)

    def test_table_importance_explicitement_versionnee(self):
        valeurs = ['HIGH']; t = TableImportance('MQL5_SYNTHETIQUE', 'v1', valeurs); valeurs.append('LOW')
        self.assertEqual(t.hautes, frozenset({'HIGH'}))
        for fournisseur, version, hautes in (('', 'v1', ['HIGH']), ('X', '', ['HIGH']), ('X', 'v1', []),
                                            ('X', 'v1', 'HIGH'), ('X', 'v1', [''])):
            with self.subTest(h=hautes), self.assertRaises(ErreurFondamental):
                TableImportance(fournisseur, version, hautes)

    def test_annonce_conserve_identite_native_et_connaissance(self):
        a = annonce()
        self.assertEqual((a.id_valeur, a.id_evenement, a.revision, a.known_at_ms), (1, 2, 0, 500))
        for changements in ({'id_valeur': 0}, {'revision': True}, {'devise': 'usd'}, {'secteur': ''}, {'instant_ms': -1}):
            with self.subTest(c=changements), self.assertRaises(ValueError): annonce(**changements)

    def test_version_immuable_coherente_et_sans_doublon(self):
        valeurs = [annonce()]
        v = VersionCalendrier(1, 500, 600, Intervalle(0, 2000), valeurs,
                              TableImportance('MQL5_SYNTHETIQUE', 'v1', ['HIGH']), 'a' * 64)
        valeurs.clear(); self.assertEqual(len(v.annonces), 1)
        for changements in ({'annonces': (annonce(), annonce())}, {'annonces': (annonce(known_at_ms=601),)},
                            {'export_ms': 601}, {'version': False}, {'empreinte': 'invalide'}):
            with self.subTest(c=changements), self.assertRaises(ValueError): replace(v, **changements)
