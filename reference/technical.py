"""Reference indicators/detectors only: no orders, sizing engine or P&L backtest."""
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_BUNDLE = json.loads((ROOT / 'config/parametres_figes_v3.json').read_text(encoding='utf-8'))
COMMON, EMA, LONDON_CFG = _BUNDLE['common'], _BUNDLE['ema'], _BUNDLE['london']
LONDON = ZoneInfo('Europe/London')
NS = 1_000_000_000


def frozen_bundle():
    return {'common': COMMON, 'ema': EMA, 'london': LONDON_CFG}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def ema(values, n):
    values = np.asarray(values, dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) >= n:
        out[n-1] = np.mean(values[:n])
        for i in range(n, len(values)):
            out[i] = out[i-1] + 2/(n+1) * (values[i] - out[i-1])
    return out


def wilder(values, n=14):
    values = np.asarray(values, dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) >= n:
        out[n-1] = np.mean(values[:n])
        for i in range(n, len(values)):
            out[i] = ((n-1)*out[i-1] + values[i])/n
    return out


def rsi(values, n=14):
    values = np.asarray(values, dtype=float)
    change = np.diff(values)
    gain = wilder(np.maximum(change, 0), n)
    loss = wilder(np.maximum(-change, 0), n)
    out = np.full(len(values), np.nan)
    with np.errstate(divide='ignore', invalid='ignore'):
        v = 100 - 100/(1 + gain/loss)
    v[(gain == 0) & (loss == 0)] = 50
    v[(gain > 0) & (loss == 0)] = 100
    v[(gain == 0) & (loss > 0)] = 0
    out[1:] = v
    return out


def add_indicators(bars):
    b = bars.copy()
    c = b.C.to_numpy()
    prior = np.r_[c[0], c[:-1]]
    b['TR'] = np.maximum.reduce([b.H-b.L, np.abs(b.H-prior), np.abs(b.L-prior)])
    b['ATR'] = wilder(b.TR.to_numpy(), COMMON['atr_period'])
    b['A'] = b.ATR.shift(1)
    for n in EMA['ema_periods']:
        b[f'E{n}'] = ema(c, n)
    b['RSI'] = rsi(c, EMA['rsi_period'])
    return b


def local_decision_in_window(open_time, close_time, cfg):
    lo = open_time.tz_convert(LONDON)
    lc = close_time.tz_convert(LONDON)
    return (lo.date() == lc.date() and lc.weekday() in COMMON['active_weekdays_local']
            and lo.strftime('%H:%M:%S') >= cfg['session_start_local']
            and lc.strftime('%H:%M:%S') < cfg['entry_end_local_exclusive'])


def trend_side(row, previous_slow):
    if row.E15 > row.E25 > row.E50 and row.E50 > previous_slow:
        return 1
    if row.E15 < row.E25 < row.E50 and row.E50 < previous_slow:
        return -1
    return 0


def arm_context(row, side):
    return (side == 1 and row.C > row.E15 and row.RSI >= 50) or (
        side == -1 and row.C < row.E15 and row.RSI <= 50)


def pullback_valid(row, side):
    a = row.A
    return (row.C >= row.E50-0.25*a and row.RSI >= 40) if side == 1 else (
        row.C <= row.E50+0.25*a and row.RSI <= 60)


def ema_signal(row, side):
    span = row.H-row.L
    if span <= 0 or row.TR > 2.5*row.A:
        return False
    if side == 1:
        return (row.C > row.E15 and row.C > row.O and row.RSI >= 50
                and (row.C-row.L)/span >= 0.65)
    return (row.C < row.E15 and row.C < row.O and row.RSI <= 50
            and (row.H-row.C)/span >= 0.65)


def ema_setups(bars, tick_size):
    """Potential setups only: no owned-position status or daily fill counter."""
    setups = []
    side, pb_start, pb_low, pb_high, cooldown = 0, None, None, None, 0
    last_day = None
    for t in range(COMMON['warmup_closed_m15_bars']-1, len(bars)):
        stamp = bars.index[t]
        close_time = stamp + pd.Timedelta(seconds=900)
        row = bars.iloc[t]
        day = close_time.tz_convert(LONDON).date()
        if day != last_day:
            side, pb_start, cooldown = 0, None, 0
            last_day = day
        if not local_decision_in_window(stamp, close_time, EMA):
            side, pb_start, cooldown = 0, None, 0
            continue
        if not np.isfinite(row.A) or row.A <= 0:
            side, pb_start = 0, None
            continue
        if cooldown:
            cooldown -= 1
            continue
        trend = trend_side(row, bars.E50.iloc[t-4])
        if side == 0:
            if trend and arm_context(row, trend):
                side = trend
            continue
        if trend != side or not pullback_valid(row, side):
            side, pb_start = 0, None
            if trend and arm_context(row, trend):
                side = trend
            continue
        if pb_start is None:
            touched = row.L <= max(row.E15, row.E50) and row.H >= min(row.E15, row.E50)
            if not touched:
                continue
            pb_start, pb_low, pb_high = t, row.L, row.H
        else:
            if t-pb_start+1 > EMA['pullback_max_inclusive_bars']:
                side, pb_start = 0, None
                if trend and arm_context(row, trend):
                    side = trend
                continue
            pb_low, pb_high = min(pb_low, row.L), max(pb_high, row.H)
        if not ema_signal(row, side):
            continue
        buffer = max(tick_size, 0.10*row.A)
        stop_bid = min(pb_low-buffer, row.C-0.80*row.A) if side == 1 else max(
            pb_high+buffer, row.C+0.80*row.A)
        d = side*(row.C-stop_bid)
        if d <= 2.50*row.A:
            setups.append({'strategy': 'EMA_V3', 'decision_time': close_time,
                           'side': side, 'signal_close_bid': float(row.C),
                           'atr_reference': float(row.A), 'stop_chart_bid': float(stop_bid),
                           'pullback_bars': t-pb_start+1})
        # The first complete technical signal consumes the pullback, also if the stop is too wide.
        side, pb_start, cooldown = 0, None, 1
    return setups


def london_signal(row, prior_close, upper, lower, tick_size):
    a = row.A
    span = row.H-row.L
    if not np.isfinite(a) or a <= 0 or span <= 0 or row.TR > 2.50*a:
        return None
    if abs(row.C-row.O)/span < 0.40:
        return None
    b = max(tick_size, 0.05*a)
    cross_long = (prior_close <= upper+b) if LONDON_CFG['fresh_close_cross_required'] else True
    cross_short = (prior_close >= lower-b) if LONDON_CFG['fresh_close_cross_required'] else True
    if row.C > upper+b and cross_long and row.C > row.O and (row.C-row.L)/span >= 0.65:
        side = 1
    elif row.C < lower-b and cross_short and row.C < row.O and (row.H-row.C)/span >= 0.65:
        side = -1
    else:
        return None
    guard = max(tick_size, 0.10*a)
    stop_bid = min(row.L-guard, upper-0.25*a, row.C-0.80*a) if side == 1 else max(
        row.H+guard, lower+0.25*a, row.C+0.80*a)
    if side*(row.C-stop_bid) > 2.50*a:
        return None
    return side, stop_bid


def london_setups(bars, h1, tick_size):
    setups = []
    local_index = bars.index.tz_convert(LONDON)
    local_days = local_index.date
    h1_close_ns = h1.index.as_unit('ns').asi8 + 3600*NS
    for day in sorted(set(local_days)):
        midnight = pd.Timestamp(day).tz_localize(LONDON)
        if midnight.weekday() > 4:
            continue
        end_range = midnight + pd.Timedelta(hours=7)
        range_start = midnight + pd.Timedelta(hours=2)
        range_index = pd.date_range(range_start, end_range, freq='15min', inclusive='left').tz_convert('UTC')
        if len(range_index) != 20 or not range_index.isin(bars.index).all():
            continue
        freeze_ns = end_range.tz_convert('UTC').value
        hx = np.searchsorted(h1_close_ns, freeze_ns, side='right')-1
        if hx < COMMON['warmup_closed_h1_bars']-1 or freeze_ns-h1_close_ns[hx] > 3600*NS:
            continue
        ah = h1.ATR.iloc[hx]
        rg = bars.loc[range_index]
        upper, lower = float(rg.H.max()), float(rg.L.min())
        if not np.isfinite(ah) or ah <= 0 or not 0.50*ah <= upper-lower <= 4.00*ah:
            continue
        for t in np.flatnonzero(local_days == day):
            if t < COMMON['warmup_closed_m15_bars']-1:
                continue
            stamp = bars.index[t]
            close_time = stamp+pd.Timedelta(seconds=900)
            if not local_decision_in_window(stamp, close_time, LONDON_CFG):
                continue
            row = bars.iloc[t]
            hit = london_signal(row, bars.C.iloc[t-1], upper, lower, tick_size)
            if hit is not None:
                side, stop_bid = hit
                setups.append({'strategy': 'LONDON_V3', 'decision_time': close_time,
                               'side': side, 'signal_close_bid': float(row.C),
                               'atr_reference': float(row.A), 'stop_chart_bid': float(stop_bid),
                               'range_high': upper, 'range_low': lower, 'range_h1_atr': float(ah)})
    return sorted(setups, key=lambda x: x['decision_time'])


def rounded_levels(setup, bid, ask, tick):
    side, raw = setup['side'], setup['stop_chart_bid']
    spread = ask-bid
    stop = math.floor(raw/tick+1e-8)*tick if side == 1 else math.ceil((raw+spread)/tick-1e-8)*tick
    entry = ask if side == 1 else bid
    d = side*(entry-stop)
    rr = EMA['take_profit_gross_price_r'] if setup['strategy'] == 'EMA_V3' else LONDON_CFG['take_profit_gross_price_r']
    target_raw = entry+side*rr*d
    target = math.ceil(target_raw/tick-1e-8)*tick if side == 1 else math.floor(target_raw/tick+1e-8)*tick
    slip = max(tick, COMMON['slippage_budget_atr_per_leg']*setup['atr_reference'])
    return {'entry': entry, 'stop': stop, 'target': target, 'distance': d,
            'slippage_per_leg': slip, 'risk_distance_with_reserve': d+2*slip}


def replay_bar_data(minutes, rule, expected):
    """M1 diagnostic requires all constituent minutes: stronger than live tick-bar coverage."""
    data = minutes.resample(rule, closed='left', label='left').agg(
        O=('bid_open', 'first'), H=('bid_high', 'max'),
        L=('bid_low', 'min'), C=('bid_close', 'last'))
    counts = minutes.bid_open.resample(rule, closed='left', label='left').count()
    return data.loc[counts == expected]
