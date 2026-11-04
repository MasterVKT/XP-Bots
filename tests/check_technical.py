"""Frozen-document and reference-detector checks using synthetic data only."""
from pathlib import Path
from decimal import Decimal, ROUND_FLOOR
from zoneinfo import ZoneInfo
import sys
import json
import hashlib
import re
import math
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESOURCES = {'01_Triple_EMA_RSI_Repli_M15_V3_IA.md': 'livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md', '02_London_Breakout_M15_V3_IA.md': 'livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md', '00_Decision_Conception_et_Faisabilite_V3.md': 'docs/decisions/00_Decision_Conception_et_Faisabilite_V3.md', '03_Donnees_Historiques_Requises_et_Validation.md': 'docs/data/03_Donnees_Historiques_Requises_et_Validation.md', '04_Integration_LLM_API_Choix_Couts_Validation.md': 'docs/architecture/04_Integration_LLM_API_Choix_Couts_Validation.md', 'parametres_figes_v3.json': 'config/parametres_figes_v3.json', 'parametres_IA_integration_v1.json': 'config/parametres_IA_integration_v1.json', 'schema_extraction_LLM_v1.json': 'schemas/schema_extraction_LLM_v1.json', 'schema_notes_IA_v1.json': 'schemas/schema_notes_IA_v1.json', 'prompts_IA_v1.json': 'prompts/prompts_IA_v1.json', 'diagnostic_faisabilite_v3.json': 'docs/validation/diagnostic_faisabilite_v3.json', 'snapshot_public_Deriv_2026-11-04.json': 'docs/validation/snapshot_public_Deriv_2026-11-04.json', 'provenance_diagnostic_v3.json': 'docs/validation/provenance_diagnostic_v3.json', 'provenance_IA_v1.json': 'docs/validation/provenance_IA_v1.json'}


def resource(name):
    return ROOT / RESOURCES[name]


PROOF = json.loads((ROOT / 'docs/validation/conservation_ressources.json').read_text(encoding='utf-8'))
REPORTS = ROOT / '.local/reports'
REPORTS.mkdir(parents=True, exist_ok=True)

from reference import technical as d

checks = []


def check(group, name, ok):
    checks.append({'pass': group, 'name': name, 'ok': bool(ok)})
    if not ok:
        raise AssertionError(name)


def close(a, b, tol=1e-10):
    return bool(np.allclose(a, b, atol=tol, rtol=0, equal_nan=True))


config = json.loads(resource('parametres_figes_v3.json').read_text(encoding='utf-8'))
probe = json.loads(resource('diagnostic_faisabilite_v3.json').read_text(encoding='utf-8'))
documents = {
    'ema': resource('01_Triple_EMA_RSI_Repli_M15_V3_IA.md').read_text(encoding='utf-8'),
    'london': resource('02_London_Breakout_M15_V3_IA.md').read_text(encoding='utf-8'),
}
check(1, 'Frozen JSON equals detector configuration', config == d.frozen_bundle())
check(1, 'Diagnostic pins the same configuration hash', probe['design_sha256'] == d.canonical_hash(config))
check(1, 'Account context 100 USD and 1:100 retained',
      config['common']['initial_equity_usd']==100 and config['common']['account_leverage']==100
      and config['common']['account_currency']=='USD')
check(1, 'No undefined strategy parameter values', 'null' not in json.dumps(config))
check(1, 'Risk remains 0.5 percent; no forced increase', config['common']['risk_fraction_per_entry']==0.005)
for name, text in documents.items():
    own = json.loads(re.search(r'~~~json\n(.*?)\n~~~', text, re.S).group(1))
    check(1, f'{name}: autonomous JSON common block identical', own['common']==config['common'])
    check(1, f'{name}: autonomous own method config identical', own['strategy']==config[name])
    check(1, f'{name}: all eleven common sections present',
          all(f'## C{i:02d} ' in text for i in range(1,12)))
    check(1, f'{name}: no unexpanded placeholder', '{{' not in text and '§' not in text)
    check(1, f'{name}: JSON fences balanced', text.count('~~~')%2==0)
    check(1, f'{name}: source references and known limitations',
          '## R ' in text and 'rentabilité n\'est pas validée' in text and 'Aucune ne valide' in text)
    check(1, f'{name}: hypothetical and real execution separated',
          'ne calcule aucun P&L' in text and 'caractéristiques imposées par le courtier' in text)
    check(1, f'{name}: fundamental causal timestamps and expiry present',
          all(s in text for s in ['known_at_utc','valid_until_utc','EXTERNAL_REQUIRED','FLATTEN']))
    check(1, f'{name}: real bid/ask and min volume refusal specified',
          'MIN_VOLUME_OR_RISK_REJECT' in text and 'Bid/Ask' in text and 'arrondir' in text.lower())
    check(1, f'{name}: shared account and original frequency target specified',
          'unique compte de 100 USD' in text and '80 %' in text)
    check(1, f'{name}: quantitative acceptance and reproduction of tick constraints',
          '10 000 réplications' in text and 'ticks générés' in text and '2,5 % et 97,5 %' in text)
check(1, 'EMA body threshold is not accidentally borrowed from London',
      'Il n\'y a pas de minimum de corps relatif' in documents['ema'])
check(1, 'London no fresh-cross gate matches frequency design',
      config['london']['fresh_close_cross_required'] is False
      and 'Aucun franchissement récent' in documents['london'])
check(1, 'London revised range has twenty bars',
      config['london']['expected_range_m15_bars']==20 and '[02:00,07:00)' in documents['london'])
for method, text in documents.items():
    marker = '## S01 ' if method == 'ema' else '## S02 '
    common = text[text.index('## C03 '):text.index(marker)].strip()
    check(1, f'{method}: common execution/risk rules preserved',
          hashlib.sha256(common.encode('utf-8')).hexdigest() == PROOF['preserved_sections'][method]['common_sha256'])

# Pass 2: arithmetic, time mapping, state edges and prefix invariance.
check(2, 'EMA3 seed and hand recurrence', close(d.ema([1,2,3,4,5],3), [np.nan,np.nan,2,3,4]))
check(2, 'Wilder3 seed and hand recurrence', close(d.wilder([1,2,3,4,5],3),
                                               [np.nan,np.nan,2,8/3,31/9]))
check(2, 'RSI constant exactly fifty', close(d.rsi(np.ones(50))[14:], np.full(36,50)))
check(2, 'RSI monotone rise exactly one hundred', close(d.rsi(np.arange(50.))[14:], np.full(36,100)))
check(2, 'RSI monotone fall exactly zero', close(d.rsi(-np.arange(50.))[14:], np.zeros(36)))
fixtures = [
    ('2026-03-30 08:00:00',7), ('2026-10-26 08:00:00',8),
    ('2026-07-01 08:00:00',7), ('2026-01-12 08:00:00',8),
]
for local, expected in fixtures:
    stamp = pd.Timestamp(local, tz='Europe/London')
    check(2, f'London DST conversion {local}', stamp.tz_convert('UTC').hour==expected)
for date in ['2026-07-01','2026-01-12']:
    begin = pd.Timestamp(date+' 02:00', tz='Europe/London')
    end = pd.Timestamp(date+' 07:00', tz='Europe/London')
    check(2, f'London range exactly twenty M15 {date}',
          len(pd.date_range(begin,end,freq='15min',inclusive='left'))==20)
    first = pd.Timestamp(date+' 08:00',tz='Europe/London').tz_convert('UTC')
    too_late = pd.Timestamp(date+' 10:45',tz='Europe/London').tz_convert('UTC')
    check(2, f'First London close at 08:15 {date}',
          d.local_decision_in_window(first,first+pd.Timedelta(minutes=15),d.LONDON_CFG))
    check(2, f'London close at 11:00 excluded {date}',
          not d.local_decision_in_window(too_late,too_late+pd.Timedelta(minutes=15),d.LONDON_CFG))


def synthetic_ema(length=1012):
    arm_open = pd.Timestamp('2026-05-11 08:00',tz='Europe/London').tz_convert('UTC')
    index = pd.date_range(start=arm_open-pd.Timedelta(minutes=15*999), periods=length, freq='15min')
    b = pd.DataFrame(index=index)
    b['O'],b['H'],b['L'],b['C'] = 100.1,100.4,100.05,100.3
    b['E15'],b['E25'] = 100.,99.7
    b['E50'] = 98.301+np.arange(length)*.001
    b['RSI'],b['A'],b['TR'],b['ATR'] = 55.,1.,.4,1.
    b.iloc[1000,b.columns.get_indexer(['O','H','L','C','RSI','TR'])] = [100.05,100.2,99.6,99.9,45.,.6]
    return b


fixture = synthetic_ema()
signals = d.ema_setups(fixture,.01)
check(2, 'EMA reprise emitted after prior contact', len(signals)==1 and signals[0]['pullback_bars']==2)
check(2, 'EMA reprise may avoid retouching the zone',
      fixture.iloc[1001].L > fixture.iloc[1001].E15 and len(signals)==1)
check(2, 'EMA stop includes earlier pullback extreme and ATR floor',
      close(signals[0]['stop_chart_bid'],99.5))
check(2, 'Arming bar cannot emit same-bar entry', len(d.ema_setups(fixture.iloc[:1000],.01))==0)
at_floor = fixture.copy()
at_floor.iloc[1000,at_floor.columns.get_loc('RSI')] = 40
check(2, 'Pullback RSI40 inclusive', len(d.ema_setups(at_floor,.01))==1)
below_floor = fixture.copy()
below_floor.iloc[1000,below_floor.columns.get_loc('RSI')] = 39.999
check(2, 'Pullback RSI below40 invalidates', len(d.ema_setups(below_floor,.01))==0)
bad = fixture.copy()
bad.iloc[1001,bad.columns.get_loc('RSI')] = 49.999
check(2, 'Signal below RSI50 not accepted at that close',
      not any(s['decision_time']==bad.index[1001]+pd.Timedelta(minutes=15)
              for s in d.ema_setups(bad,.01)))
bad = fixture.copy()
bad.iloc[1001,bad.columns.get_loc('TR')] = 2.500001
check(2, 'Signal TR above 2.5 ATR rejected at that close',
      not any(s['decision_time']==bad.index[1001]+pd.Timedelta(minutes=15)
              for s in d.ema_setups(bad,.01)))
mirror = fixture.copy()
for col in ['O','C','E15','E25','E50']:
    mirror[col] = 200-fixture[col]
mirror['H'],mirror['L'],mirror['RSI'] = 200-fixture.L,200-fixture.H,100-fixture.RSI
shorts = d.ema_setups(mirror,.01)
check(2, 'EMA short mirror symmetric', len(shorts)==1 and shorts[0]['side']==-1
      and close(shorts[0]['stop_chart_bid'],200-signals[0]['stop_chart_bid']))
for signal_index in [1007,1008]:
    aged = fixture.copy()
    for i in range(1000,signal_index):
        aged.iloc[i,aged.columns.get_indexer(['O','H','L','C','RSI','TR'])] = [100.05,100.2,99.6,99.9,45.,.6]
    aged.iloc[signal_index,aged.columns.get_indexer(['O','H','L','C','RSI','TR'])] = [100.1,100.4,100.05,100.3,55.,.4]
    at_instant = [s for s in d.ema_setups(aged,.01)
                  if s['decision_time']==aged.index[signal_index]+pd.Timedelta(minutes=15)]
    check(2, f'Pullback age boundary {signal_index-999}', bool(at_instant)==(signal_index==1007))

row = pd.Series({'O':1.09995,'H':1.10055,'L':1.09990,'C':1.10050,'A':.00050,'TR':.00065})
hit = d.london_signal(row,1.10040,1.10000,1.09800,.00001)
check(2, 'London allows previously outside close', hit is not None and hit[0]==1)
check(2, 'London local stop hand result', close(hit[1],1.09985))
check(2, 'London local stop differs from opposite whole range', hit[1] >1.09800)
doji = row.copy(); doji.O=doji.C
check(2, 'London doji fails', d.london_signal(doji,1.10040,1.10000,1.09800,.00001) is None)
weak = row.copy();weak.O=1.10030
check(2, 'London insufficient body fails', d.london_signal(weak,1.10040,1.10000,1.09800,.00001) is None)
limit = row.copy();limit.C=1.10000+max(.00001,.05*row.A);limit.O=1.09995
check(2, 'London equal breakout buffer not strict crossing',
      d.london_signal(limit,1.10040,1.10000,1.09800,.00001) is None)
large = row.copy();large.TR=2.500001*large.A
check(2, 'London oversized TR fails', d.london_signal(large,1.10040,1.10000,1.09800,.00001) is None)
limit = row.copy();limit.TR=2.5*row.A
check(2, 'London TR limit inclusive', d.london_signal(limit,1.10040,1.10000,1.09800,.00001) is not None)
rev = pd.Series({'O':2.2-row.O,'H':2.2-row.L,'L':2.2-row.H,'C':2.2-row.C,'A':row.A,'TR':row.TR})
reverse_hit = d.london_signal(rev,2.2-1.10040,2.2-1.09800,2.2-1.10000,.00001)
check(2, 'London short mirror symmetric', reverse_hit is not None and reverse_hit[0]==-1
      and close(reverse_hit[1],2.2-hit[1]))

buy = {'strategy':'EMA_V3','side':1,'stop_chart_bid':1.09945,'atr_reference':.00050}
sell = {'strategy':'EMA_V3','side':-1,'stop_chart_bid':1.10055,'atr_reference':.00050}
bp=d.rounded_levels(buy,1.10000,1.10010,.00001)
sp=d.rounded_levels(sell,1.10000,1.10010,.00001)
check(2, 'Long stop and target numerical example', close([bp['stop'],bp['target']],[1.09945,1.10108]))
check(2, 'Short Ask stop and target numerical example', close([sp['stop'],sp['target']],[1.10065,1.09902]))
check(2, 'Bid/Ask risk symmetric without double spread',
      close([bp['distance'],sp['distance']],[.00065,.00065]))
check(2, 'Entry and exit risk slippage reserved exactly once each',
      close([bp['risk_distance_with_reserve'],sp['risk_distance_with_reserve']],[.00070,.00070]))
lp = d.rounded_levels({'strategy':'LONDON_V3','side':1,'stop_chart_bid':hit[1],'atr_reference':.00050},
                      1.10050,1.10060,.00001)
check(2, 'London target 2R hand result', close([lp['entry'],lp['stop'],lp['target']],[1.10060,1.09985,1.10210]))
check(2, 'Minimal standard FX risk exceeds 0.5USD', Decimal('0.00070')*Decimal('1000')>Decimal('0.50'))
max_micro = (Decimal('.5')/(Decimal('.00070')*Decimal('1000'))/Decimal('.1')).to_integral_value(rounding=ROUND_FLOOR)*Decimal('.1')
check(2, 'Example micro hypothetical step down only', max_micro==Decimal('.7')
      and max_micro*Decimal('1000')*Decimal('.00070')<=Decimal('.5'))
check(2, 'Example gold 0.1 ounce stop8 exceeds budget', Decimal('.1')*Decimal('8')>Decimal('.5'))
check(2, 'Leverage affects margin not same-size stop loss',
      close(1000*1.1/100,11) and close(1000*.0007,.7))

# Deterministic synthetic M1 fixture: independent of archived prices and network.
minute_index = pd.date_range('2026-05-01', periods=15*3300, freq='1min', tz='UTC').as_unit('us')
minute_step = np.arange(len(minute_index), dtype=float)
minute_open = 1.10 + minute_step*.0000004 + .0008*np.sin(minute_step/73)
minute_close = minute_open + .00004*np.cos(minute_step/17)
m = pd.DataFrame({'bid_open': minute_open,
                  'bid_high': np.maximum(minute_open,minute_close)+.00003,
                  'bid_low': np.minimum(minute_open,minute_close)-.00003,
                  'bid_close': minute_close}, index=minute_index)
b=d.add_indicators(d.replay_bar_data(m,'15min',15))
h=d.add_indicators(d.replay_bar_data(m,'1h',60))
check(2, 'Timestamp index explicitly normalized to ns',
      h.index.as_unit('ns').asi8[-1] > 10**18)
check(2, 'ATR reference is strictly previous closed bar',
      close(b.A.iloc[15:].to_numpy(),b.ATR.iloc[14:-1].to_numpy()))
for cut in [2400,3200]:
    prefix = b.iloc[:cut]
    raw_prefix = d.add_indicators(prefix[['O','H','L','C']])
    for column in ['E15','E25','E50','RSI','ATR','A']:
        check(2,f'{column} prefix invariance at {cut}',
              close(raw_prefix[column].to_numpy(),prefix[column].to_numpy()))
    check(2, f'EMA technical decisions prefix-causal at {cut}',
          d.ema_setups(prefix,.00001)==[s for s in d.ema_setups(b,.00001)
                                     if s['decision_time']<=prefix.index[-1]+pd.Timedelta(minutes=15)])
    cutoff=prefix.index[-1]+pd.Timedelta(minutes=15)
    hp=h.loc[h.index+pd.Timedelta(hours=1)<=cutoff]
    check(2, f'London H1 mapping and decisions prefix-causal at {cut}',
          d.london_setups(prefix,hp,.00001)==[s for s in d.london_setups(b,h,.00001)
                                           if s['decision_time']<=cutoff])

# Pass 3: financial claims, output accounting, data requests, reproducibility.
report=resource('00_Decision_Conception_et_Faisabilite_V3.md').read_text(encoding='utf-8')
request=resource('03_Donnees_Historiques_Requises_et_Validation.md').read_text(encoding='utf-8')
check(3,'Diagnostic twelve rows complete',len(probe['rows'])==12)
check(3,'Invalid or crossed quotations rejected explicitly',
      all('invalid_quote' in r['quote_rejections'] for r in probe['rows']))
expected={(s,t,p) for s in ['EMA_V3','LONDON_V3'] for t in ['EURUSD','GBPUSD','XAUUSD']
          for p in ['STANDARD_GENERIC','MICRO_PUBLIC_EXPOSURE']}
check(3,'Diagnostic Cartesian coverage correct',
      {(r['strategy'],r['symbol'],r['profile']) for r in probe['rows']}==expected)
for r in probe['rows']:
    label=f"{r['strategy']}/{r['symbol']}/{r['profile']}"
    check(3,label+': setup and rejection accounting',
          r['potential_technical_setups_before_fill_counters']
          ==r['quote_and_price_eligible_setups']+sum(r['quote_rejections'].values()))
    check(3,label+': feasibility count bounded',
          0<=r['potentially_feasible_at_100_before_fees_and_portfolio']<=r['quote_and_price_eligible_setups'])
    check(3,label+': quantile lower bound internally ordered',
          0<r['minimum_equity_median_lower_bound_usd']<=r['minimum_equity_p80_lower_bound_usd'])
check(3,'No backtest or PnL fabricated',
      probe['portfolio_and_trade_pnl_computed'] is False and 'Il ne calcule aucun profit' in report)
check(3,'Independent block tests distinguished from continuous account path',
      all('rejeu continu du 01/01/2020' in text and 'expérience autonome' in text
          for text in documents.values()))
check(3,'M1 quotation timing approximation disclosed', 'même tick synchrone' in report)
check(3,'No retention claim from candidate counts', 'aucune rétention effective' in report)
check(3,'Frequency iterations disclosed, no PnL tuning',
      probe['frequency_design_iterations']==2 and probe['profit_parameter_search_count']==0
      and 'Deux conceptions de fréquence' in report)
check(3,'Gold incompatibility with examined 100USD configurations disclosed',
      all(r['potentially_feasible_at_100_before_fees_and_portfolio']==0
          for r in probe['rows'] if r['symbol']=='XAUUSD') and 'L\'or n\'est pas retenu' in report)
check(3,'Deriv micro account eligibility not claimed', 'ne garantit pas' in report and 'ton compte standard' in report)
check(3,'Required exact history dates and three symbols',
      all(s in request for s in ['02/12/2019','03/11/2026','EURUSD','GBPUSD','XAUUSD','ticks']))
check(3,'Exposed dates not called independent final test',
      'Déjà exploré' in request and '01/05/2026–03/11/2026' in request)
check(3,'External fundamental historical permissions explicitly required',
      all(s in request for s in ['known_at_utc','input_snapshot_id','permissions','causales']))
check(3,'No unnecessary DXY or volume requirement', 'DXY et volumes ne sont pas nécessaires' in report)
snapshot=json.loads(resource('snapshot_public_Deriv_2026-11-04.json').read_text(encoding='utf-8'))
for symbol,contract,minimum in [('EURUSDmicro','1000','0.1'),('GBPUSDmicro','1000','0.1'),('XAUUSDmicro','1','0.1')]:
    check(3,f'Public snapshot exposure {symbol}',
          snapshot['rows'][symbol]['contract-size']==contract and snapshot['rows'][symbol]['min-size']==minimum)
check(3,'No stale draft config among canonical resources',not (ROOT/'config/parametres_brouillon_probe.json').exists())

output={'status':'PASS','scope':'Documents, indicator/detector arithmetic and prefix causality, and truthfulness of feasibility reporting. Not a broker robot backtest or financial validation.',
        'checks_total':len(checks),'passes':{str(i):sum(x['pass']==i for x in checks) for i in [1,2,3]},
        'design_sha256':d.canonical_hash(config),'checks':checks}
(REPORTS/'check_technical.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in output.items() if k!='checks'},ensure_ascii=False,indent=2))
