"""Profils de quotas et de prix synthétiques dérivés des exports figés."""
from decimal import Decimal, ROUND_CEILING
from xpbots.service_ia.c0_types import JobIA, canonique, iso
from xpbots.service_ia.c1d_budget import ProfilRoute, RegistreBudget
from .support import ressources, document, job, Memoire


def profil(r=None,t=None,payant=False,**changements):
    r=r or ressources();t=document().collecte_ms if t is None else t
    f=next(p for p in r.p['providers'] if 'input_usd_per_million_upper_bound' in p) if payant else r.p['providers'][0]
    fraction=Decimal(str(r.p['provider_quota_safety_fraction']))
    def plafond(n):return int((Decimal(n)/fraction).to_integral_value(rounding=ROUND_CEILING))
    v=dict(fournisseur=f['id'],modele=f['model'],profil_facturation=f['billing_profile'],
        quota_tokens_minute=plafond(r.p['max_input_tokens_upper_bound']+r.p['max_output_tokens_including_reasoning']),
        quota_requetes_minute=r.p['max_api_attempts_per_utc_day'],
        quota_requetes_jour=plafond(r.p['max_api_attempts_per_utc_day']),
        quota_tokens_jour=plafond(r.p['max_reserved_tokens_per_utc_day']),verifie_ms=t,
        gratuit_confirme=not payant,projet_dedie=payant,cle_disponible=True,
        prix_entree=Decimal(f['input_usd_per_million_upper_bound']) if payant else None,
        prix_sortie=Decimal(f['output_usd_per_million_upper_bound']) if payant else None)
    v.update(changements);return ProfilRoute(**v)


def registre(t=None,payant=False):
    r=ressources();m=Memoire();b=RegistreBudget(r,m)
    t=document().collecte_ms if t is None else t
    if payant:b.provisionner(iso(t)[:7],'0','0')
    return r,m,b,profil(r,t,payant),t


def demande(t,ident='j',kind='EXTRACTION'):
    if kind in ('EXTRACTION','GOLDEN'):return job(document(t=t,item_id='article-'+ident),job_id=ident,kind=kind)
    return JobIA(ident,kind,None,t,t+ressources().p['job_deadline_seconds']*1000,
        canonique(dict(documents=[])))
