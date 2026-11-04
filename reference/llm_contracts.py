"""Pure reference contracts, with no HTTP client, model inference or broker order."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
AI_CONFIG = json.loads((ROOT / 'config/parametres_IA_integration_v1.json').read_text(encoding='utf-8'))
SCHEMA = json.loads((ROOT / 'schemas/schema_extraction_LLM_v1.json').read_text(encoding='utf-8'))
ADVISORY_SCHEMA = json.loads((ROOT / 'schemas/schema_notes_IA_v1.json').read_text(encoding='utf-8'))
_PROMPTS = json.loads((ROOT / 'prompts/prompts_IA_v1.json').read_text(encoding='utf-8'))
ENUMS = {key: SCHEMA['properties'][key]['enum'] for key in
         ['event_class', 'temporal_status', 'policy_actor', 'stance']}
EXTRACTION_PROMPT = _PROMPTS['extraction']
BRIEF_PROMPT = _PROMPTS['briefing']
JOURNAL_PROMPT = _PROMPTS['journal']


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def utc(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):
        raise ValueError('UTC offset required')
    return dt.astimezone(timezone.utc)


def no_duplicate_keys(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def parse_model_output(text, item):
    if len(text.encode('utf-8'))>AI_CONFIG['max_response_bytes']:
        raise ValueError('Response too large')
    value=json.loads(text,object_pairs_hook=no_duplicate_keys,
                     parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    if not isinstance(value,dict) or set(value)!=set(SCHEMA['required']):
        raise ValueError('Unexpected or missing fields')
    if any(not isinstance(v,str) for v in value.values()):
        raise ValueError('String-only output')
    if value['schema_version']!='fx-text-extraction-v1' or value['item_id']!=item['item_id']:
        raise ValueError('Schema or item mismatch')
    for key,allowed in ENUMS.items():
        if value[key] not in allowed: raise ValueError('Unknown enum')
    quote=value['evidence_quote']
    if len(quote)>AI_CONFIG['evidence_quote_max_characters'] or (quote and quote not in item['provided_text']):
        raise ValueError('Evidence not verbatim in provided document')
    return value


def parse_advisory_output(text,expected_kind,known_evidence_ids):
    if expected_kind not in ['BRIEFING','JOURNAL','WEEKLY_REVIEW']:raise ValueError('Unknown task kind')
    if len(text.encode('utf-8'))>AI_CONFIG['max_response_bytes']:raise ValueError('Too large')
    value=json.loads(text,object_pairs_hook=no_duplicate_keys)
    if not isinstance(value,dict) or set(value)!=set(ADVISORY_SCHEMA['required']):
        raise ValueError('Unexpected advisory fields')
    if value['schema_version']!='fx-advisory-v1' or value['kind']!=expected_kind:
        raise ValueError('Advisory kind mismatch')
    for key in ['observations','uncertainties','hypotheses']:
        if not isinstance(value[key],list) or len(value[key])>3:raise ValueError('Advisory list cap')
    def short(text):
        if not isinstance(text,str) or len(text)>400:raise ValueError('Advisory text cap')
    for obs in value['observations']:
        if not isinstance(obs,dict) or set(obs)!={'text','evidence_ids'}:raise ValueError('Observation schema')
        short(obs['text'])
        ids=obs['evidence_ids']
        if not isinstance(ids,list) or not 1<=len(ids)<=4 or any(not isinstance(x,str) or x not in known_evidence_ids for x in ids):
            raise ValueError('Unsupported advisory evidence')
    for uncertainty in value['uncertainties']:short(uncertainty)
    for hypothesis in value['hypotheses']:
        if not isinstance(hypothesis,dict) or set(hypothesis)!={'statement','validation_plan'}:raise ValueError('Hypothesis schema')
        short(hypothesis['statement']);short(hypothesis['validation_plan'])
    if expected_kind=='BRIEFING' and value['hypotheses']:raise ValueError('Brief is informative only')
    return value


def build_policy_event(parsed,item,analysis_received_utc,provider_id,calendar_valid):
    """A possible veto; never a trading permission. Native strategy controls still apply."""
    now=utc(analysis_received_utc)
    published=utc(item['published_at_utc'])
    first_seen=utc(item['first_seen_utc'])
    if not published<=first_seen<=now: raise ValueError('Noncausal document timestamps')
    if type(calendar_valid) is not bool or type(item['trusted_official_origin']) is not bool:
        raise ValueError('Boolean source and calendar state required')
    if item['issuer'] not in {'FED','ECB','BOE'}:
        raise ValueError('Issuer outside configured official sources')
    if provider_id not in {p['id'] for p in AI_CONFIG['providers']}:
        raise ValueError('Provider outside cloud allowlist')
    if not calendar_valid or type(item['scheduled_high_impact_match']) is not bool:
        return None
    if item['scheduled_high_impact_match'] or not item['trusted_official_origin']:
        return None
    if not (parsed['event_class']=='MONETARY_DECISION'
            and parsed['temporal_status']=='ANNOUNCED_NOW'
            and parsed['policy_actor']==item['issuer']
            and parsed['stance'] in ['TIGHTENING','EASING','UNCHANGED']
            and len(parsed['evidence_quote'])>=20):
        return None
    expiry=published+timedelta(seconds=900)
    if now>=expiry: return None
    symbols={'FED':['EURUSD','GBPUSD','XAUUSD'],'ECB':['EURUSD'],'BOE':['GBPUSD']}
    return {'event_id':digest({'item_id':item['item_id'],'first_seen':item['first_seen_utc']}),
            'reason_code':'OFFICIAL_UNSCHEDULED_POLICY',
            'canonical_symbols':symbols[item['issuer']],
            'valid_from_utc':now.isoformat(), 'valid_until_utc':expiry.isoformat(),
            'item_id':item['item_id'],'provider_id':provider_id}


def make_snapshot(sequence,generated_utc,events):
    body={'schema':'xp-ai-context-v1','sequence':sequence,'generated_at_utc':generated_utc,
          'integration_digest':digest(AI_CONFIG),'events':events}
    return {'payload':body,'sha256':digest(body)}


def overlay_decision(snapshot,now_utc,canonical_symbol,live=False,financial_gate_passed=False,last_sequence=0,cached_events=()):
    """Missing/invalid optional AI context is neutral, not an ALLOW for mandatory controls."""
    now=utc(now_utc)
    if type(live) is not bool or type(financial_gate_passed) is not bool:
        return 'NEUTRAL'
    if live and not financial_gate_passed: return 'NEUTRAL'
    # cached_events must come only from snapshots validated previously, never directly from a model.
    for event in cached_events:
        if canonical_symbol in event['canonical_symbols'] and utc(event['valid_from_utc'])<=now<utc(event['valid_until_utc']):
            return 'BLOCK'
    try:
        if set(snapshot)!= {'payload','sha256'} or digest(snapshot['payload'])!=snapshot['sha256']:
            return 'NEUTRAL'
        body=snapshot['payload'];generated=utc(body['generated_at_utc'])
        if set(body)!={'schema','sequence','generated_at_utc','integration_digest','events'}:
            return 'NEUTRAL'
        if type(body['sequence']) is not int or body['sequence']<max(1,last_sequence):
            return 'NEUTRAL'
        if body['schema']!='xp-ai-context-v1' or body['integration_digest']!=digest(AI_CONFIG):
            return 'NEUTRAL'
        if not 0 <= (now-generated).total_seconds() <= AI_CONFIG['snapshot_max_age_seconds']:
            return 'NEUTRAL'
        for event in body['events']:
            if set(event)!={'event_id','reason_code','canonical_symbols','valid_from_utc','valid_until_utc','item_id','provider_id'}:
                return 'NEUTRAL'
            if event['reason_code']!='OFFICIAL_UNSCHEDULED_POLICY' or event['provider_id'] not in {p['id'] for p in AI_CONFIG['providers']}:
                return 'NEUTRAL'
            if utc(event['valid_from_utc'])>generated:
                return 'NEUTRAL'
            if canonical_symbol in event['canonical_symbols'] and utc(event['valid_from_utc'])<=now<utc(event['valid_until_utc']):
                return 'BLOCK'
    except (TypeError,ValueError,KeyError,OverflowError):
        return 'NEUTRAL'
    return 'NEUTRAL'


def combined_entry_allowed(mandatory_baseline_allowed,ai_overlay):
    return mandatory_baseline_allowed is True and ai_overlay!='BLOCK'


def token_input_upper_bound(serialized_request_without_secret):
    """Conservative fallback; actual tokenizer including chat/schema wrappers may replace this."""
    return len(serialized_request_without_secret.encode('utf-8'))+512


def reserve_cost_usd(input_tokens_upper=4096,output_tokens_max=2048):
    if not (0<=input_tokens_upper<=4096 and 0<=output_tokens_max<=2048):
        raise ValueError('Token envelope exceeded')
    return (Decimal(input_tokens_upper)*Decimal('.10')+
            Decimal(output_tokens_max)*Decimal('.50'))/Decimal(1000000)


def budget_admits(spent,reserved,next_upper_bound,other_gross_spend='0',tax_fx_reserve='0'):
    spent,reserved,next_upper_bound,other_gross_spend,tax_fx_reserve=map(
        Decimal,map(str,[spent,reserved,next_upper_bound,other_gross_spend,tax_fx_reserve]))
    if min(spent,reserved,next_upper_bound,other_gross_spend,tax_fx_reserve)<0:
        raise ValueError('Negative ledger amount')
    return (spent+reserved+next_upper_bound<=Decimal('3')
            and spent+reserved+next_upper_bound+other_gross_spend+tax_fx_reserve<=Decimal('15'))
