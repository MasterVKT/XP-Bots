"""Couche 0 — `parametres_ema` : clés exactes du bloc `ema`, variantes implémentées, seuils `common` de S01."""
import copy
import unittest

from xpbots.donnees_temps.c0_parametres_seances import FonctionNonImplementee
from xpbots.moteur_ema.c0_parametres import (CLES_COMMON, SCHEMA_EMA, VARIANTES_IMPLEMENTEES, ParametresEMA,
                                             charger_parametres_ema)
from xpbots.noyau.config import ConfigurationInvalide, charger_bundle_technique

BUNDLE = charger_bundle_technique()
EMA = dict(BUNDLE.donnees['ema'])
COMMON = dict(BUNDLE.donnees['common'])


def parametres(**changements):
    bloc = copy.deepcopy(EMA)
    for cle, valeur in changements.items():
        if valeur is KeyError:
            del bloc[cle]
        else:
            bloc[cle] = valeur
    return ParametresEMA(bloc, COMMON, BUNDLE.empreinte)


class TestSchema(unittest.TestCase):
    def test_vingt_trois_cles_exactes(self):
        self.assertEqual(set(SCHEMA_EMA), set(EMA))
        self.assertEqual(len(SCHEMA_EMA), 23)

    def test_valeurs_lues_dans_config(self):
        p = charger_parametres_ema(BUNDLE)
        self.assertEqual(p.strategie_id, EMA['strategy_id'])
        self.assertEqual(p.periodes_ema, tuple(EMA['ema_periods']))
        self.assertEqual((p.rsi_repli_long_min, p.rsi_repli_court_max, p.rsi_signal_long_min, p.rsi_signal_court_max),
                         (EMA['long_pullback_rsi_min'], EMA['short_pullback_rsi_max'], EMA['long_signal_rsi_min'],
                          EMA['short_signal_rsi_max']))
        self.assertEqual((p.decalage_pente, p.age_max_repli, p.clotures_cooldown, p.entrees_max_jour),
                         (EMA['slow_ema_slope_lookback_bars'], EMA['pullback_max_inclusive_bars'],
                          EMA['cooldown_closed_bars_after_signal_or_owned_exit'],
                          EMA['max_filled_entries_per_symbol_local_day']))
        self.assertEqual((p.depassement_ema_lente_atr, p.position_cloture_min, p.multiple_objectif),
                         (EMA['maximum_close_beyond_ema50_atr'], EMA['signal_close_location_min'],
                          EMA['take_profit_gross_price_r']))
        self.assertEqual((p.tampon_structurel_atr, p.stop_min_atr, p.stop_max_atr, p.tr_max_atr),
                         tuple(COMMON[c] for c in CLES_COMMON))
        self.assertEqual([h.isoformat() for h in p.heures],
                         [EMA['session_start_local'], EMA['entry_end_local_exclusive'], EMA['force_exit_local']])
        self.assertEqual(p.empreinte, BUNDLE.empreinte)
        self.assertIs(type(p.multiple_objectif), float)

    def test_cle_manquante_en_trop_ou_mal_typee(self):
        for changements in ({'rsi_period': KeyError}, {'cle_inconnue': 1}, {'rsi_period': 14.0},
                            {'long_pullback_rsi_min': '40'}, {'session_start_local': '8:00'},
                            {'require_signal_touch': 0}, {'ema_periods': []}, {'ema_periods': [15, 25.0, 50]},
                            {'pullback_max_inclusive_bars': 0}, {'take_profit_gross_price_r': float('nan')}):
            with self.subTest(changements=changements), self.assertRaises(ConfigurationInvalide):
                parametres(**changements)

    def test_lecture_seule_et_cle_absente(self):
        p = charger_parametres_ema(BUNDLE)
        with self.assertRaises(ConfigurationInvalide):
            p.valeur('inexistante')
        with self.assertRaises(AttributeError):
            p.strategie_id = 'X'
        self.assertEqual(p.valeur('ema_seed'), EMA['ema_seed'])


class TestVariantes(unittest.TestCase):
    def test_variante_non_implementee_refusee(self):
        autres = {'ema_seed': 'FIRST_VALUE', 'rsi_method': 'SMA', 'pullback_touch_zone': 'EMA15_ONLY',
                  'require_directional_body': False, 'require_signal_touch': True,
                  'h1_directional_filter_enabled': True}
        self.assertEqual(set(autres), set(VARIANTES_IMPLEMENTEES))
        for cle, valeur in autres.items():
            with self.subTest(cle=cle), self.assertRaises(FonctionNonImplementee):
                parametres(**{cle: valeur})

    def test_periodes_coherentes(self):
        for periodes in ([15, 25], [15, 25, 50, 100], [25, 15, 50], [15, 15, 50]):
            with self.subTest(periodes=periodes), self.assertRaises(ConfigurationInvalide):
                parametres(ema_periods=periodes)

    def test_fenetre_et_fraction(self):
        for changements in ({'session_start_local': EMA['entry_end_local_exclusive']},
                            {'signal_close_location_min': 1.5}):
            with self.subTest(changements=changements), self.assertRaises(ConfigurationInvalide):
                parametres(**changements)

    def test_seuils_common_obligatoires(self):
        for cle in CLES_COMMON:
            common = {k: v for k, v in COMMON.items() if k != cle}
            with self.subTest(cle=cle), self.assertRaises(ConfigurationInvalide):
                ParametresEMA(EMA, common, BUNDLE.empreinte)


if __name__ == '__main__':
    unittest.main()
