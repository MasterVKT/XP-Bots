"""Pont de test vers `reference.technical` (numpy, pandas) : indicateurs et configurations potentielles S01."""
import importlib.util

REFERENCE_DISPONIBLE = all(importlib.util.find_spec(nom) for nom in ('numpy', 'pandas'))


def cadre_reference(bougies):
    """DataFrame indexé par l'ouverture UTC, enrichi par `reference.technical.add_indicators`."""
    import pandas as pd
    from reference import technical
    index = pd.to_datetime([b.ouverture_ms for b in bougies], unit='ms', utc=True)
    cadre = pd.DataFrame([(float(b.o), float(b.h), float(b.l), float(b.c)) for b in bougies],
                         columns=['O', 'H', 'L', 'C'], index=index)
    return technical.add_indicators(cadre)


def setups_reference(cadre, tick_size):
    from reference import technical
    return [{'cloture_ms': int(s['decision_time'].value // 1_000_000), 'sens': s['side'],
             'cloture_bid': s['signal_close_bid'], 'a_t': s['atr_reference'], 'b_sl': s['stop_chart_bid'],
             'age': s['pullback_bars']} for s in technical.ema_setups(cadre, float(tick_size))]
