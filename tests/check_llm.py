"""Triple check of the documentation and deterministic contracts, without any API call."""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import re
import os
from copy import deepcopy
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESOURCES = {'01_Triple_EMA_RSI_Repli_M15_V3_IA.md': 'livrables/strategies_m15/01_Triple_EMA_RSI_Repli_M15_Specification_IA.md', '02_London_Breakout_M15_V3_IA.md': 'livrables/strategies_m15/02_London_Breakout_M15_Specification_IA.md', '00_Decision_Conception_et_Faisabilite_V3.md': 'docs/decisions/00_Decision_Conception_et_Faisabilite_V3.md', '03_Donnees_Historiques_Requises_et_Validation.md': 'docs/data/03_Donnees_Historiques_Requises_et_Validation.md', '04_Integration_LLM_API_Choix_Couts_Validation.md': 'docs/architecture/04_Integration_LLM_API_Choix_Couts_Validation.md', 'parametres_figes_v3.json': 'config/parametres_figes_v3.json', 'parametres_IA_integration_v1.json': 'config/parametres_IA_integration_v1.json', 'schema_extraction_LLM_v1.json': 'schemas/schema_extraction_LLM_v1.json', 'schema_notes_IA_v1.json': 'schemas/schema_notes_IA_v1.json', 'prompts_IA_v1.json': 'prompts/prompts_IA_v1.json', 'diagnostic_faisabilite_v3.json': 'docs/validation/diagnostic_faisabilite_v3.json', 'snapshot_public_Deriv_2026-11-04.json': 'docs/validation/snapshot_public_Deriv_2026-11-04.json', 'provenance_diagnostic_v3.json': 'docs/validation/provenance_diagnostic_v3.json', 'provenance_IA_v1.json': 'docs/validation/provenance_IA_v1.json'}


def resource(name):
    return ROOT / RESOURCES[name]


PROOF = json.loads((ROOT / 'docs/validation/conservation_ressources.json').read_text(encoding='utf-8'))
REPORTS = ROOT / '.local/reports'
REPORTS.mkdir(parents=True, exist_ok=True)

from reference.llm_contracts import *

checks=[]


def check(group,name,ok):
    checks.append({'pass':group,'name':name,'ok':bool(ok)})
    if not ok:raise AssertionError(name)


def raises(call):
    try:call()
    except (ValueError,TypeError,KeyError):return True
    return False


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


meta=PROOF
technical=json.loads(resource('parametres_figes_v3.json').read_text(encoding='utf-8'))
check(1,'User reference document unchanged',
      sha(ROOT/'docs/references/IA_Generative_Forex_Scalping_M15_v2.md')==meta['source_reference_sha256'])
check(1,'Frozen technical parameter file unchanged',
      sha(resource('parametres_figes_v3.json'))==meta['frozen_technical_file_sha256'])
check(1,'Cloud configuration export exact',
      json.loads(resource('parametres_IA_integration_v1.json').read_text(encoding='utf-8'))==AI_CONFIG)
check(1,'Model output schema export exact',
      json.loads(resource('schema_extraction_LLM_v1.json').read_text(encoding='utf-8'))==SCHEMA)
check(1,'Informative briefing and journal schema export exact',
      json.loads(resource('schema_notes_IA_v1.json').read_text(encoding='utf-8'))==ADVISORY_SCHEMA)
check(1,'Local inference excluded explicitly',AI_CONFIG['local_inference_allowed'] is False)
check(1,'No local provider in route',
      all(p['endpoint'].startswith('https://') for p in AI_CONFIG['providers'])
      and [p['id'] for p in AI_CONFIG['providers']]==['GROQ_FREE','GEMINI_FREE','OPENAI_PAID_OPTIONAL'])
check(1,'Free default and total budget',
      AI_CONFIG['paid_fallback_enabled_by_default'] is False
      and Decimal(AI_CONFIG['monthly_total_budget_usd'])==15
      and Decimal(AI_CONFIG['monthly_paid_api_subcap_usd'])==3)
check(1,'No synchronous LLM allowed on entry',AI_CONFIG['synchronous_llm_on_entry_allowed'] is False)
for name,method in [('01_Triple_EMA_RSI_Repli_M15_V3_IA.md','ema'),
                    ('02_London_Breakout_M15_V3_IA.md','london')]:
    text=resource(name).read_text(encoding='utf-8')
    own=json.loads(re.search(r'~~~json\n(.*?)\n~~~',text,re.S).group(1))
    check(1,f'{method}: technical common JSON preserved',own['common']==technical['common'])
    check(1,f'{method}: method JSON preserved',own['strategy']==technical[method])
    check(1,f'{method}: full cloud configuration embedded',own['ai_integration']==AI_CONFIG)
    check(1,f'{method}: all fifteen AI sections embedded',
          all(f'## A{i:02d} ' in text for i in range(1,16)))
    check(1,f'{method}: no unresolved generator marker','{{' not in text and '§' not in text)
    check(1,f'{method}: mandatory fundamental contract preserved',
          'EXTERNAL_REQUIRED' in text and 'NEUTRAL signifie **aucun veto supplémentaire**' in text)
    check(1,f'{method}: core five second execution TTL preserved',own['common']['entry_signal_ttl_seconds']==5)
    start='## S01 ' if method=='ema' else '## S02 '
    new_core=text[text.index(start):text.index('## A01 ')].strip()
    check(1,f'{method}: strategy section text unchanged',hashlib.sha256(new_core.encode('utf-8')).hexdigest()==PROOF['preserved_sections'][method]['method_sha256'])
    check(1,f'{method}: provider examples and actual schema included',
          all(s in text for s in ['max_completion_tokens','responseJsonSchema','max_output_tokens','provided_text']))
    check(1,f'{method}: model and financial validation distinguished',
          '200 textes' in text and '200 trades clos' in text and 'NON_QUALIFIE' in text)
    check(1,f'{method}: API failure not a fundamental permission',
          'une permission fondamentale manquante en autorisation' in text)
    check(1,f'{method}: snapshot expiry does not extend event life',
          'ne renouvelle pas la vie des événements' in text and 'cache persistant' in text)
    check(1,f'{method}: no reduction of lots by LLM','ni REDUCE/lot' in text)
    check(1,f'{method}: no false claim of successful API or profit test',
          'Ils ne certifient pas un appel réussi aux API' in text)
    check(1,f'{method}: documentary version upgraded', 'version documentaire 3.1.0' in text)
    check(1,f'{method}: method-specific refusal semantics',
          ('repli consommé' in text) if method=='ema' else ('Aucun sens n\'est marqué' in text))

# Deterministic tests with clearly synthetic public text, not assertions about actual policy.
provided='The Federal Reserve announces a reduction in the target policy rate, effective immediately.'
item={'item_id':'SYNTHETIC-01','issuer':'FED','text':provided+' Unsent historical appendix.',
      'provided_text':provided,'published_at_utc':'2026-11-05T08:01:00Z',
      'first_seen_utc':'2026-11-05T08:01:05Z',
      'scheduled_high_impact_match':False,'trusted_official_origin':True}
valid={'schema_version':'fx-text-extraction-v1','item_id':item['item_id'],
       'event_class':'MONETARY_DECISION','temporal_status':'ANNOUNCED_NOW',
       'policy_actor':'FED','stance':'EASING','evidence_quote':provided}
raw=canonical(valid)
parsed=parse_model_output(raw,item)
check(2,'Synthetic well formed extraction accepted',parsed==valid)
check(2,'Required fields equal schema properties',set(SCHEMA['required'])==set(SCHEMA['properties']))
check(2,'Output cannot contain trading action','decision' not in SCHEMA['properties'] and 'price' not in SCHEMA['properties'])
for field,value in [('decision','BUY'),('size_multiplier',2),('confidence',0.99)]:
    bad={**valid,field:value}
    check(2,f'Extra model control field {field} rejected',
          raises(lambda bad=bad:parse_model_output(canonical(bad),item)))
for key in valid:
    bad=valid.copy();bad.pop(key)
    check(2,f'Missing model field {key} rejected',raises(lambda bad=bad:parse_model_output(canonical(bad),item)))
for key in ENUMS:
    bad={**valid,key:'BUY_NOW'}
    check(2,f'Unknown {key} enum rejected',raises(lambda bad=bad:parse_model_output(canonical(bad),item)))
check(2,'Duplicate JSON key rejected',
      raises(lambda:parse_model_output(raw[:-1]+',"stance":"TIGHTENING"}',item)))
check(2,'Invalid JSON rejected',raises(lambda:parse_model_output('not json',item)))
check(2,'Nonfinite JSON rejected',raises(lambda:parse_model_output(raw.replace('"EASING"','NaN'),item)))
check(2,'Numeric model output rejected',
      raises(lambda:parse_model_output(canonical({**valid,'item_id':123}),item)))
check(2,'Foreign source item rejected',
      raises(lambda:parse_model_output(canonical({**valid,'item_id':'OTHER'}),item)))
check(2,'Invented quotation rejected',
      raises(lambda:parse_model_output(canonical({**valid,'evidence_quote':'Invented policy statement'}),item)))
check(2,'Quotation absent from actual submitted excerpt rejected',
      raises(lambda:parse_model_output(canonical({**valid,'evidence_quote':'Unsent historical appendix.'}),item)))
check(2,'Quotation over160 chars rejected',
      raises(lambda:parse_model_output(canonical({**valid,'evidence_quote':'x'*161}),{**item,'provided_text':'x'*200})))
check(2,'Response byte cap enforced',
      raises(lambda:parse_model_output(' '*16385,item)))
event=build_policy_event(parsed,item,'2026-11-05T08:02:00Z','GROQ_FREE',True)
check(2,'Synthetic unscheduled policy creates possible veto',event is not None)
check(2,'Veto valid from actual receipt not publication',utc(event['valid_from_utc'])==utc('2026-11-05T08:02:00Z'))
check(2,'Veto ends publication plus15 minutes',utc(event['valid_until_utc'])==utc('2026-11-05T08:16:00Z'))
check(2,'USD maps to all three canonical instruments',event['canonical_symbols']==['EURUSD','GBPUSD','XAUUSD'])
for key,value in [('event_class','CENTRAL_BANK_SPEECH'),('event_class','ECONOMIC_DATA'),
                  ('temporal_status','HISTORICAL'),('temporal_status','CONDITIONAL'),
                  ('temporal_status','UNCLEAR'),('policy_actor','ECB'),('stance','UNCLEAR'),
                  ('evidence_quote','short')]:
    changed={**valid,key:value}
    check(2,f'Nonqualifying event {key}/{value} creates no veto',
          build_policy_event(changed,item,'2026-11-05T08:02:00Z','GROQ_FREE',True) is None)
for issuer,symbols in [('ECB',['EURUSD']),('BOE',['GBPUSD'])]:
    changed={**valid,'policy_actor':issuer}
    ev=build_policy_event(changed,{**item,'issuer':issuer},'2026-11-05T08:02:00Z','GEMINI_FREE',True)
    check(2,f'{issuer} currency mapping exact',ev['canonical_symbols']==symbols)
check(2,'Scheduled announcement does not add duplicate AI veto',
      build_policy_event(parsed,{**item,'scheduled_high_impact_match':True},'2026-11-05T08:02:00Z','GROQ_FREE',True) is None)
check(2,'Invalid mandatory calendar cannot be bypassed',
      build_policy_event(parsed,item,'2026-11-05T08:02:00Z','GROQ_FREE',False) is None)
check(2,'Unofficial source cannot produce veto',
      build_policy_event(parsed,{**item,'trusted_official_origin':False},'2026-11-05T08:02:00Z','GROQ_FREE',True) is None)
check(2,'Unknown provider rejected',raises(lambda:build_policy_event(parsed,item,'2026-11-05T08:02:00Z','UNKNOWN',True)))
check(2,'Future publication rejected',raises(lambda:build_policy_event(parsed,{**item,'published_at_utc':'2026-11-05T09:00:00Z'},'2026-11-05T08:02:00Z','GROQ_FREE',True)))
check(2,'Future reception rejected',raises(lambda:build_policy_event(parsed,item,'2026-11-05T08:01:00Z','GROQ_FREE',True)))
check(2,'Boolean source fields are strict',raises(lambda:build_policy_event(parsed,{**item,'trusted_official_origin':'false'},'2026-11-05T08:02:00Z','GROQ_FREE',True)))
check(2,'NonUTC timestamps rejected',raises(lambda:utc('2026-11-05T09:02:00+01:00')))
check(2,'Response at expiry is unusable',
      build_policy_event(parsed,item,'2026-11-05T08:16:00Z','GROQ_FREE',True) is None)

snap=make_snapshot(10,'2026-11-05T08:02:00Z',[event])
check(2,'Paper veto active at inclusive start',overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD')=='BLOCK')
check(2,'Snapshot cannot act before publication of result',overlay_decision(snap,'2026-11-05T08:01:59Z','EURUSD')=='NEUTRAL')
check(2,'Snapshot90seconds inclusive',overlay_decision(snap,'2026-11-05T08:03:30Z','EURUSD')=='BLOCK')
check(2,'Snapshot older than90s adds no new events',overlay_decision(snap,'2026-11-05T08:03:31Z','EURUSD')=='NEUTRAL')
check(2,'Known prior veto survives stale heartbeat until own expiry',
      overlay_decision(snap,'2026-11-05T08:10:00Z','EURUSD',cached_events=[event])=='BLOCK')
check(2,'Cached veto expires at exact event end',
      overlay_decision(snap,'2026-11-05T08:16:00Z','EURUSD',cached_events=[event])=='NEUTRAL')
check(2,'New heartbeat cannot renew veto',
      overlay_decision(make_snapshot(11,'2026-11-05T08:16:00Z',[event]),'2026-11-05T08:16:00Z','EURUSD')=='NEUTRAL')
check(2,'Unknown snapshot is neutral on cold start',overlay_decision({},'2026-11-05T08:02:00Z','EURUSD')=='NEUTRAL')
check(2,'Corruption cannot revoke already verified active event',
      overlay_decision({},'2026-11-05T08:03:00Z','EURUSD',cached_events=[event])=='BLOCK')
broken=deepcopy(snap);broken['sha256']='wrong'
check(2,'Corrupt snapshot cannot add event',overlay_decision(broken,'2026-11-05T08:02:00Z','EURUSD')=='NEUTRAL')
check(2,'Sequence rollback rejected',overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD',last_sequence=11)=='NEUTRAL')
check(2,'Same fresh sequence can be read repeatedly',overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD',last_sequence=10)=='BLOCK')
check(2,'Unvalidated real-account AI veto disabled',overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD',live=True)=='NEUTRAL')
check(2,'Live gate must be a Boolean',overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD',live=True,financial_gate_passed='false')=='NEUTRAL')
check(2,'Validated gate enables same veto mechanically',
      overlay_decision(snap,'2026-11-05T08:02:00Z','EURUSD',live=True,financial_gate_passed=True)=='BLOCK')
for baseline in [False,None,1]:
    check(2,f'Optional context never replaces mandatory control {baseline!r}',
          combined_entry_allowed(baseline,'NEUTRAL') is False)
check(2,'Neutral overlay preserves mandatory allowed baseline',combined_entry_allowed(True,'NEUTRAL'))
check(2,'Veto cannot create a trade',combined_entry_allowed(True,'BLOCK') is False)

note={'schema_version':'fx-advisory-v1','kind':'BRIEFING',
      'observations':[{'text':'Synthetic official source received.','evidence_ids':['SOURCE-1']}],
      'uncertainties':['No complete geopolitical coverage.'],'hypotheses':[]}
check(2,'Informative briefing validates only provided evidence',
      parse_advisory_output(canonical(note),'BRIEFING',{'SOURCE-1'})==note)
check(2,'Informative output cannot contain executable action',
      raises(lambda:parse_advisory_output(canonical({**note,'decision':'BUY'}),'BRIEFING',{'SOURCE-1'})))
check(2,'Advisory invented evidence ID rejected',
      raises(lambda:parse_advisory_output(canonical(note),'BRIEFING',{'OTHER'})))
check(2,'Advisory expected kind is enforced',
      raises(lambda:parse_advisory_output(canonical(note),'JOURNAL',{'SOURCE-1'})))
check(2,'Unknown advisory task rejected',
      raises(lambda:parse_advisory_output(canonical({**note,'kind':'TRADE'}),'TRADE',{'SOURCE-1'})))
check(2,'Briefing cannot mutate research agenda',
      raises(lambda:parse_advisory_output(canonical({**note,'hypotheses':[{'statement':'Change live RSI.','validation_plan':'None'}]}),'BRIEFING',{'SOURCE-1'})))
check(2,'Advisory output lists bounded',
      raises(lambda:parse_advisory_output(canonical({**note,'uncertainties':['x']*4}),'BRIEFING',{'SOURCE-1'})))
check(2,'Advisory text bounded',
      raises(lambda:parse_advisory_output(canonical({**note,'uncertainties':['x'*401]}),'BRIEFING',{'SOURCE-1'})))

check(3,'Paid maximal per-request bound exact',reserve_cost_usd()==Decimal('0.0014336'))
check(3,'22-day maximum cost exact',reserve_cost_usd()*24*22==Decimal('0.7569408'))
check(3,'31-day maximum cost exact',reserve_cost_usd()*24*31==Decimal('1.0665984'))
check(3,'Daily worst reserved tokens within cap',(4096+2048)*24==147456<150000)
check(3,'One maximum request fits eighty percent of public TPM',6144<=8000*0.8)
check(3,'Input byte fallback includes envelope',token_input_upper_bound('abc')==515)
check(3,'NonASCII UTF8 included in bound',token_input_upper_bound('é')==514)
check(3,'Token envelope cannot silently increase',raises(lambda:reserve_cost_usd(4097,2048)))
check(3,'Negative token reservation refused',raises(lambda:reserve_cost_usd(-1,2048)))
check(3,'Paid budget near limit still admits fitting request',
      budget_admits('2.9985','0',reserve_cost_usd()))
check(3,'Paid budget cannot overspend three dollars',
      not budget_admits('2.999','0',reserve_cost_usd()))
check(3,'Reserved requests counted before second admission',
      not budget_admits('2.9985',reserve_cost_usd(),reserve_cost_usd()))
check(3,'Global gross budget includes fees and other AI costs',
      not budget_admits('2','0','.001','12','1'))
check(3,'Exact global fifteen boundary admitted',budget_admits('2','0','0','12','1'))
check(3,'Negative ledger rejected',raises(lambda:budget_admits('-1','0','.001')))
report=resource('04_Integration_LLM_API_Choix_Couts_Validation.md').read_text(encoding='utf-8')
provenance=json.loads(resource('provenance_IA_v1.json').read_text(encoding='utf-8'))
check(3,'No invented model tests or financial gains',
      provenance['inference_calls_performed']==0 and not provenance['model_quality_test_performed']
      and not provenance['financial_gain_validated'])
check(3,'Failed BoE feed not claimed operational','HTTP 403' in report)
check(3,'Source daily-before-cost evidence limitations disclosed','quotidien' in report and 'avant frais' in report)
check(3,'Prior reference negative-base generalization corrected','Faux comme énoncé mathématique général' in report)
check(3,'Source preservation documented','conservée sans modification' in report)
check(3,'Updated data collection includes causal LLM traces',
      'réponses originales' in resource('03_Donnees_Historiques_Requises_et_Validation.md').read_text(encoding='utf-8'))
check(3,'Core diagnostic is not relabeled AI result',
      'sans LLM' in resource('00_Decision_Conception_et_Faisabilite_V3.md').read_text(encoding='utf-8'))
result={'status':'PASS','integration_digest':digest(AI_CONFIG),'checks_total':len(checks),
        'passes':{str(group):sum(c['pass']==group for c in checks) for group in [1,2,3]},
        'scope':'Documents and deterministic reference contracts only; no model inference, broker order, compiled EA, semantic accuracy or financial validation.',
        'network_inference_calls':0,'checks':checks}
(REPORTS/'check_llm.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False,indent=2))
