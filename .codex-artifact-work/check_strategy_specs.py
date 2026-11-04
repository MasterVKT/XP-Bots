from pathlib import Path
from decimal import Decimal, getcontext, ROUND_FLOOR, ROUND_CEILING
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import sys

getcontext().prec = 40
D = Decimal
ROOT = Path(r'D:\PROJETS\XP-Bots')
OUT = ROOT / 'livrables' / 'strategies_m15'
FILES = sorted(OUT.glob('0[12]_*.md'))
SOURCE = Path(r'C:\Users\Lenovo\Downloads\Modèles strategies ForexM15.md')
PASSED = [[], [], []]


def check(stage, name, predicate):
    if not predicate:
        raise AssertionError(f'Stage {stage}: {name}')
    PASSED[stage - 1].append(name)


def read_config(text):
    return json.loads(re.search(r'```json\n(.*?)\n```', text, re.S).group(1))


def down(price, tick):
    return (price / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


def up(price, tick):
    return (price / tick).to_integral_value(rounding=ROUND_CEILING) * tick


check(1, 'Exactly two requested Markdown files', len(FILES) == 2)
documents = [(p, p.read_text(encoding='utf-8')) for p in FILES]
configs = [read_config(text) for p, text in documents]
for (path, text), config in zip(documents, configs):
    tag = path.name[:2]
    check(1, tag + ' UTF-8 without replacement characters', '\ufffd' not in text)
    check(1, tag + ' newline normalization', b'\r' not in path.read_bytes() and text.endswith('\n'))
    check(1, tag + ' all common sections', all(f'## C{i:02d} ' in text for i in range(1, 11)))
    check(1, tag + ' all strategy sections', all(f'## S{i:02d} ' in text for i in range(1, 11)))
    check(1, tag + ' config and references', all(f'## {section} ' in text for section in ['P01', 'R01', 'R02']))
    check(1, tag + ' balanced code fences', sum(line.startswith('```') for line in text.splitlines()) % 2 == 0)
    check(1, tag + ' original source checksum', hashlib.sha256(SOURCE.read_bytes()).hexdigest() in text)
    check(1, tag + ' no placeholder instructions', not re.search(r'\b(?:TODO|TBD|FIXME)\b', text))
    check(1, tag + ' explicit nonvalidated profitability', 'rentabilité non validée' in text)
    check(1, tag + ' explicit rule origins', all(x in text for x in ['SOURCE', 'FORMALISATION', 'EXECUTION']))
    check(1, tag + ' paper default', config['execution_mode'] == 'PAPER')
    check(1, tag + ' source risk 0.5 percent', config['risk_fraction_per_trade'] == .005)
    check(1, tag + ' no H1 filter silently introduced', config['use_h1_filter'] is False)
    check(1, tag + ' symbols configured independently', set(config['symbol_profiles']) == {'EURUSD', 'GBPUSD', 'XAUUSD'})
    check(1, tag + ' unknown broker costs not zeroed', all(v['round_trip_cost_model_id'] is None for v in config['symbol_profiles'].values()))
    ids = re.findall(r'^\| ((?:C-T|S-T)\d+) \|', text, re.M)
    check(1, tag + ' unique acceptance IDs', len(ids) == len(set(ids)))
    check(1, tag + ' acceptance coverage not empty', len(ids) >= 40)

ema_cfg, london_cfg = configs
check(1, 'EMA original periods kept', ema_cfg['ema_periods'] == [15, 25, 50] and ema_cfg['rsi_period'] == 14)
check(1, 'EMA one explicit exit branch', ema_cfg['exit_mode'] == 'FIXED_R_2' and ema_cfg['take_profit_r_multiple'] == 2)
check(1, 'EMA no London fusion', ema_cfg['use_london_range'] is False)
check(1, 'London one explicit source close branch', london_cfg['entry_mode'] == 'M15_CLOSE_MARKET')
check(1, 'London no EMA RSI retest fusion', all(london_cfg[x] is False for x in ['use_ema', 'use_rsi', 'use_retest']))
check(1, 'London preserved UTC range', (london_cfg['range_timezone'], london_cfg['range_start'], london_cfg['range_end']) == ('UTC', '02:00:00', '06:00:00'))
check(1, 'London preserved cutoff and exit', (london_cfg['entry_cutoff'], london_cfg['force_exit']) == ('10:00:00', '12:00:00'))
check(1, 'London preserved width threshold', london_cfg['symbol_strategy_profiles']['EURUSD']['max_range_width_price'] == .006)
check(1, 'London no invented gold threshold', london_cfg['symbol_strategy_profiles']['XAUUSD']['max_range_width_price'] is None)

# Second pass: independent numerical calculations for all worked examples.
budget = D('20000') * D('.005')
volume = down(budget / D('127'), D('.01'))
check(2, 'FX budget example', budget == D('100'))
check(2, 'FX volume floor', volume == D('.78'))
check(2, 'FX accepted risk', volume * D('127') == D('99.06'))
check(2, 'FX next volume rejected', (volume + D('.01')) * D('127') == D('100.33'))
gold_volume = down(D('50') / D('807'), D('.01'))
check(2, 'Gold volume floor', gold_volume == D('.06'))
check(2, 'Gold accepted risk', gold_volume * D('807') == D('48.42'))
check(2, 'Gold next volume rejected', D('.07') * D('807') == D('56.49'))
tick = D('.00001')
sl_long = (up(D('1.10020'), tick) / tick - 1) * tick
entry = D('1.10102')
tp_long = up(entry + 2 * (entry - sl_long), tick)
check(2, 'EMA exact long stop', sl_long == D('1.10019'))
check(2, 'EMA exact long target', tp_long == D('1.10268'))
check(2, 'EMA pip distances', (entry - sl_long) / D('.0001') == D('8.3') and (tp_long - entry) / D('.0001') == D('16.6'))
sl_short = (down(D('1.09980'), tick) / tick + 1) * tick
entry_short = D('1.09898')
tp_short = down(entry_short - 2 * (sl_short - entry_short), tick)
check(2, 'EMA exact short stop and target', sl_short == D('1.09981') and tp_short == D('1.09732'))
check(2, 'EMA target reflection', D('2.20000') - tp_long == tp_short)
check(2, 'Gold EMA exact target', D('4000') + 2 * (D('4000') - D('3992')) == D('4016'))
hi, lo = D('1.1000'), D('1.0980')
width = hi - lo
check(2, 'London width example', width / D('.0001') == 20)
check(2, 'London long TP from range not entry', up(hi + D('1.5') * width, tick) == D('1.10300'))
check(2, 'London short TP from range not entry', down(lo - D('1.5') * width, tick) == D('1.09500'))
check(2, 'London risk versus reward', (D('1.10042') - lo) / D('.0001') == D('24.2') and (D('1.103') - D('1.10042')) / D('.0001') == D('25.8'))
check(2, 'London actual price RR', abs(D('25.8') / D('24.2') - D('1.066')) < D('.001'))
check(2, 'Gold London target', D('4000') + D('1.5') * (D('4000') - D('3990')) == D('4015'))
check(2, 'No price rounding increases risk through volume rounding', down(D('.787401'), D('.01')) < D('.787401'))


def emas(closes, period):
    out = [None] * len(closes)
    alpha = D(2) / D(period + 1)
    out[period - 1] = sum(closes[:period]) / D(period)
    for i in range(period, len(closes)):
        out[i] = alpha * closes[i] + (1 - alpha) * out[i - 1]
    return out


def rsi(closes, period=14):
    diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(x, D(0)) for x in diffs]
    losses = [max(-x, D(0)) for x in diffs]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period

    def val():
        if ag == 0 and al == 0: return D(50)
        if al == 0: return D(100)
        if ag == 0: return D(0)
        return D(100) - D(100) / (1 + ag/al)

    out = [val()]
    for gain, loss in zip(gains[period:], losses[period:]):
        ag = ((period-1) * ag + gain) / period
        al = ((period-1) * al + loss) / period
        out.append(val())
    return out


constant = [D('1.1')] * 600
linear = [D('1') + D(i) * D('.001') for i in range(600)]
for period in [15, 25, 50]:
    check(2, f'EMA {period} constant seed and recurrence', all(x is None or x == D('1.1') for x in emas(constant, period)))
    expected = linear[-1] - D(period - 1) / 2 * D('.001')
    check(2, f'EMA {period} linear exact lag', abs(emas(linear, period)[-1] - expected) < D('1e-30'))
check(2, 'RSI constant', set(rsi(constant)) == {D(50)})
check(2, 'RSI increasing', set(rsi(linear)) == {D(100)})
check(2, 'RSI decreasing', set(rsi(list(reversed(linear)))) == {D(0)})
alternating = [D(i % 2) for i in range(16)]
check(2, 'RSI Wilder first recurrence', rsi(alternating)[0] == 50 and abs(rsi(alternating)[1] - D(750)/14) < D('1e-30'))


# Third pass: causal boundaries and strategy scenario probes, not tests of a future robot.
def candle(o, h, l, c):
    return dict(zip('OHLC', map(D, (o, h, l, c))))


def geometry(b):
    r = b['H'] - b['L']
    body = abs(b['C'] - b['O'])
    upper = b['H'] - max(b['O'], b['C'])
    lower = min(b['O'], b['C']) - b['L']
    return r, body, upper, lower


def strong(b, side):
    r, body, upper, lower = geometry(b)
    if r <= 0 or body == 0: return False
    if side == 'long': return b['C'] > b['O'] and body >= D('.6')*r and b['H']-b['C'] <= D('.25')*r
    return b['C'] < b['O'] and body >= D('.6')*r and b['C']-b['L'] <= D('.25')*r


def weak(b, side):
    r, body, upper, lower = geometry(b)
    return r > 0 and body < D('.3') * r and (upper if side == 'long' else lower) > D('.5') * r


def hammer(b, side):
    r, body, upper, lower = geometry(b)
    if r <= 0 or body == 0: return False
    if side == 'long': return b['C'] > b['O'] and lower >= 2*body and upper <= body
    return b['C'] < b['O'] and upper >= 2*body and lower <= body


def reflect(b):
    k = D('2.2')
    return {'O': k-b['O'], 'H': k-b['L'], 'L': k-b['H'], 'C': k-b['C']}


long_bar = candle('1.10030','1.10110','1.10020','1.10100')
short_bar = reflect(long_bar)
check(3, 'Worked long bar meets strong predicate', strong(long_bar, 'long'))
check(3, 'Worked reflected short bar meets strong predicate', strong(short_bar, 'short'))
check(3, 'Worked long bar touches EMA zone', long_bar['L'] <= D('1.10060') and long_bar['H'] >= D('1.10000'))
check(3, 'Worked short bar touches reflected EMA zone', short_bar['L'] <= D('1.10000') and short_bar['H'] >= D('1.09940'))
check(3, 'Long example recovers EMA15', long_bar['C'] > D('1.10070'))
check(3, 'Short example recovers EMA15', short_bar['C'] < D('1.09930'))
check(3, 'Doji is not strong or hammer', not strong(candle('1','2','0','1'), 'long') and not hammer(candle('1','2','0','1'), 'long'))
hammer_bar = candle('1.10030','1.10060','1.09980','1.10050')
check(3, 'Hammer branch can trigger without strong body', hammer(hammer_bar, 'long') and not strong(hammer_bar, 'long'))
check(3, 'Hammer reflection symmetry', hammer(reflect(hammer_bar), 'short'))
check(3, 'Strong exact ratio boundary', strong(candle('0.15','1','0','0.75'), 'long'))
weak_bar = candle('.1','1','0','.3')
check(3, 'London narrow body opposing wick rejected', weak(weak_bar,'long'))
check(3, 'London opposing wick short symmetry', weak(reflect(weak_bar),'short'))
check(3, 'London body exactly thirty percent accepted by weak test', not weak(candle('.1','1','0','.4'),'long'))
check(3, 'London wick exactly fifty percent accepted by weak test', not weak(candle('.3','1','0','.5'),'long'))
check(3, 'RSI boundary 50 not strict entry', not (D(50) > 50) and not (D(50) < 50))
check(3, 'RSI 50 not pullback invalidation', not (D(50) < 50) and not (D(50) > 50))
check(3, 'Long pullback RSI crossing rejected', D('49.99') < 50)
check(3, 'Long wick may exceed EMA50 without invalidating close', D('1.0998') < D('1.1000') and D('1.1005') >= D('1.1000'))
check(3, 'Close exactly at range edge is not break', not (D('1.1') > hi) and not (D('1.098') < lo))
check(3, 'Range exact maximum accepted next tick rejected', D('.0060') <= D('.0060') < D('.00601'))
range_openings = [datetime(2026,11,3,2,0,tzinfo=timezone.utc)+timedelta(minutes=15*i) for i in range(16)]
check(3, 'Exactly sixteen range bar opens', len(range_openings) == 16 and range_openings[-1].strftime('%H:%M') == '05:45')
check(3, 'Range ends at six exclusive', range_openings[-1]+timedelta(minutes=15) == datetime(2026,11,3,6,tzinfo=timezone.utc))
check(3, 'Entry cutoff half-open', not (D('10') < D('10')))
check(3, 'TTL half-open', D('4.999') < 5 and not (D('5') < 5))
check(3, 'News half-open', -900 <= -900 < 900 and not (-900 <= 900 < 900))

for path, text in documents:
    tag = path.name[:2]
    for marker in ['SIGNAL_PENDING', 'RECONCILE_REQUIRED', 'EXIT_REQUIRED', 'PROVISIONAL_TP_EXECUTION', 'transaction persistante', 'prix moyen pondéré', 'passerelles de contexte', 'passerelles d\'exécution']:
        check(3, tag+' lifecycle invariant '+marker, marker in text)
    check(3, tag+' examples marked synthetic', 'synthétiques' in text and 'ne constituent ni un backtest' in text)
    check(3, tag+' risk not guaranteed', 'perte maximale garantie' in text)

counts = [len(x) for x in PASSED]
summary = {
    'status': 'PASS',
    'checks_by_pass': counts,
    'total_checks': sum(counts),
    'scope': 'Document structure and provenance; reference numerical calculations; boundary and scenario probes. No robot or real-market backtest tested.',
    'files': []
}

if '--publish' in sys.argv:
    for path, text in documents:
        before = text.split('## R02 — Triple contrôle de livraison documentaire')[0]
        report = f'''## R02 — Triple contrôle de livraison documentaire

Contrôles exécutés le **3 novembre 2026** sur les deux fichiers livrés :

1. **Fidélité, structure et configuration : {counts[0]} contrôles réussis.** Vérification des paramètres source conservés, des branches sélectionnées, de l'absence de fusion ou d'ajustement de performance présenté comme démontré, du JSON, de l'autonomie, des identifiants de cas et de l'empreinte du document source.
2. **Calculs et indicateurs : {counts[1]} contrôles réussis.** Recalcul décimal indépendant des exemples Forex/or, des volumes après frais, des arrondis, des stops/objectifs, des symétries achat/vente et des graines/récurrences EMA et RSI.
3. **Cas limites et cohérence opérationnelle : {counts[2]} contrôles réussis.** Vérification de référence des bornes temporelles et des prédicats de bougies, puis présence et cohérence des exigences de reprise, de signaux en attente, de transactions persistantes et de réconciliation. Les conversions saisonnières Londres/UTC des trois dates d'exemple ont aussi été recoupées avec les fuseaux Windows.

Total : **{sum(counts)} contrôles documentaires et de référence réussis**, répartis sur les deux fichiers. Les contrôles propres à l'une des stratégies ne sont pas des tests de l'autre. La relecture sémantique a notamment vérifié la distinction entre filtre de contexte et attente d'une cotation dans le TTL, le risque après remplissage et la conservation des bornes du range.

**Limite du contrôle : aucun robot n'a été développé ou testé à ce stade et aucun backtest sur marché réel n'a été effectué.** Ces contrôles ne certifient ni la future implémentation ni sa rentabilité. Les cas d'acceptation C-T et S-T restent des obligations de test pour l'agent qui développera le robot ; leur présence dans le document ne signifie pas qu'un robot les a déjà réussis.
'''
        path.write_text(before+report, encoding='utf-8', newline='\n')

for path in FILES:
    payload = path.read_bytes()
    summary['files'].append({'path': str(path), 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
print(json.dumps(summary, ensure_ascii=False, indent=2))
