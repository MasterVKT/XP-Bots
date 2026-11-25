"""Implémentation de la couche 1d (registre), révisable sous harnais complet."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from xpbots.service_ia.c0_types import (ErreurService, JobIA, entier, instant,
    texte, montant, iso, empreinte, canonique, decoder)
from ._model import (_ressources, _cout, ProfilRoute, ReservationAPI,
    DecisionBudget, cout_maximal, budget_admet)

_MINUTE_MS=timedelta(minutes=1)//timedelta(milliseconds=1)
_PROFIL_GRATUIT_VERIFIE='FREE_CONFIRMED'  # Variante de facturation reconnue, jamais un défaut de compte.


def _ms(secondes):return timedelta(seconds=secondes)//timedelta(milliseconds=1)


def _periode(mois):
    texte(mois)
    try:
        if date.fromisoformat(mois+'-01').strftime('%Y-%m')!=mois:raise ValueError
    except ValueError:raise ErreurService('MOIS_UTC_INVALIDE') from None
    return mois


def _budget(t,mois):
    b=t['api_budget'].setdefault(mois,dict(month=mois,spent_usd='0',reserved_usd='0',
        other_costs_usd='0',tax_fx_reserve_usd='0',provisions_verifiees=False))
    for cle in ('spent_usd','reserved_usd','other_costs_usd','tax_fx_reserve_usd'):montant(b[cle])
    if type(b.get('provisions_verifiees')) is not bool:raise ErreurService('ETAT_BUDGET_INVALIDE')
    return b


def _compteurs(table,cle):
    q=table.setdefault(cle,dict(attempts=0,event_attempts=0,reserved_tokens=0))
    for nom in ('attempts','event_attempts','reserved_tokens'):entier(q[nom])
    return q


def _route(t,pid):
    s=t['provider_state'].setdefault('route:'+pid,dict(provider=pid,disabled=False,
        not_before_ms=0,last_sent_ms=None))
    if type(s['disabled']) is not bool:raise ErreurService('ETAT_ROUTE_INVALIDE')
    instant(s['not_before_ms'])
    if s['last_sent_ms'] is not None:instant(s['last_sent_ms'])
    return s


def _profil_pret(r,p,maintenant,paiement):
    f=r.fournisseur(p.fournisseur)
    if (p.modele!=f['model'] or p.profil_facturation!=f['billing_profile']
            or not p.cle_disponible or p.verifie_ms is None or p.verifie_ms>maintenant
            or min(p.quota_tokens_minute,p.quota_requetes_minute,p.quota_requetes_jour,p.quota_tokens_jour)<=0):
        return 'ROUTE_NON_QUALIFIEE'
    if f['billing_profile']==_PROFIL_GRATUIT_VERIFIE:
        if not p.gratuit_confirme or any(v not in (None,Decimal(0)) for v in (p.prix_entree,p.prix_sortie)):
            return 'GRATUITE_NON_CONFIRMEE'
    else:
        if not paiement:return 'ROUTE_PAYANTE_DESACTIVEE'
        if not p.projet_dedie:return 'PROJET_DEDIE_REQUIS'
        age=timedelta(days=r.p['paid_price_review_max_age_days'])//timedelta(milliseconds=1)
        if maintenant-p.verifie_ms>age:return 'PRIX_PERIMES'
        if (p.prix_entree!=montant(f['input_usd_per_million_upper_bound'])
                or p.prix_sortie!=montant(f['output_usd_per_million_upper_bound'])):return 'PRIX_NON_CONFORMES'
    return None


class RegistreBudget:
    def __init__(self,ressources,depot):
        self.r=_ressources(ressources)
        if not callable(getattr(depot,'transaction',None)):raise ErreurService('DEPOT_TRANSACTIONNEL_REQUIS')
        self.depot=depot

    def _transaction(self,operation):
        try:return self.depot.transaction(operation)
        except ErreurService:raise
        except (KeyError,TypeError,ValueError):raise ErreurService('ETAT_REGISTRE_INVALIDE') from None

    def consulter(self,mois):
        _periode(mois)
        return self._transaction(lambda t:dict(_budget(t,mois)))

    def provisionner(self,mois,autres,taxes):
        _periode(mois);a=montant(autres);x=montant(taxes)
        def operation(t):
            b=_budget(t,mois)
            b.update(other_costs_usd=str(a),tax_fx_reserve_usd=str(x),provisions_verifiees=True)
            return dict(b)
        return self._transaction(operation)

    def etat_route(self,fournisseur):
        self.r.fournisseur(fournisseur)
        return self._transaction(lambda t:dict(_route(t,fournisseur)))

    def reserver(self,job,profil,entree_bornee,instant_ms,*,paiement_autorise=False):
        r=self.r;instant(instant_ms);entier(entree_bornee)
        if not isinstance(job,JobIA) or not isinstance(profil,ProfilRoute):raise ErreurService('JOB_ET_PROFIL_REQUIS')
        if type(paiement_autorise) is not bool:raise ErreurService('CHOIX_PAIEMENT_BOOLEEN_REQUIS')
        if job.fournisseur is not None and job.fournisseur!=profil.fournisseur:
            return DecisionBudget(raison='FOURNISSEUR_JOB_INCOMPATIBLE')
        if entree_bornee>r.p['max_input_tokens_upper_bound']:raise ErreurService('ENVELOPPE_TOKENS_DEPASSEE')
        if not job.cree_ms<=instant_ms<job.utile_jusqua_ms:return DecisionBudget(raison='JOB_EXPIRE_OU_FUTUR')
        refus=_profil_pret(r,profil,instant_ms,paiement_autorise)
        if refus:return DecisionBudget(raison=refus)
        pid=profil.fournisseur;f=r.fournisseur(pid)
        payant=f['billing_profile']!=_PROFIL_GRATUIT_VERIFIE
        cout=cout_maximal(r,entree_bornee) if payant else Decimal(0)
        jour=iso(instant_ms).split('T')[0];mois=jour.rsplit('-',1)[0]
        total=entree_bornee+r.p['max_output_tokens_including_reasoning']
        cle=empreinte(dict(job_id=job.job_id,provider=pid))
        def operation(t):
            return self._reserver(t,job,profil,entree_bornee,instant_ms,cle,jour,mois,total,cout,payant)
        return self._transaction(operation)

    def _reserver(self,t,job,profil,entree,maintenant,cle,jour,mois,total,cout,payant):
        r=self.r;pid=profil.fournisseur;s=_route(t,pid)
        if cle in t['api_attempts']:return DecisionBudget(raison='DEJA_TENTEE')
        if s['disabled']:return DecisionBudget(raison='ROUTE_DESACTIVEE')
        fraction=montant(r.p['provider_quota_safety_fraction'])
        espacement=max(_ms(r.p['provider_min_request_spacing_seconds']),
            int((Decimal(_MINUTE_MS)/(Decimal(profil.quota_requetes_minute)*fraction)).to_integral_value(rounding=ROUND_CEILING)))
        if (maintenant<s['not_before_ms'] or s['last_sent_ms'] is not None
                and maintenant-s['last_sent_ms']<espacement):return DecisionBudget(raison='ESPACEMENT_FOURNISSEUR')
        if Decimal(total)>Decimal(profil.quota_tokens_minute)*fraction:
            return DecisionBudget(raison='QUOTA_FOURNISSEUR')
        q=_compteurs(t['schedule_state'],'quota:'+jour)
        p=_compteurs(t['provider_state'],'quota:'+pid+':'+jour)
        evenement=job.kind=='EXTRACTION'
        if q['attempts']>=r.p['max_api_attempts_per_utc_day']:
            return DecisionBudget(raison='QUOTA_TENTATIVES')
        if evenement and q['event_attempts']>=r.p['max_event_classification_attempts_per_day']:
            return DecisionBudget(raison='QUOTA_CLASSIFICATIONS')
        if q['reserved_tokens']+total>r.p['max_reserved_tokens_per_utc_day']:
            return DecisionBudget(raison='QUOTA_TOKENS')
        if (Decimal(p['attempts']+1)>Decimal(profil.quota_requetes_jour)*fraction
                or Decimal(p['reserved_tokens']+total)>Decimal(profil.quota_tokens_jour)*fraction):
            return DecisionBudget(raison='QUOTA_FOURNISSEUR')
        b=_budget(t,mois)
        if payant and not b['provisions_verifiees']:return DecisionBudget(raison='PROVISION_NON_VERIFIEE')
        if not budget_admet(r,b['spent_usd'],b['reserved_usd'],cout,b['other_costs_usd'],b['tax_fx_reserve_usd']):
            return DecisionBudget(raison='BUDGET_EPUISE')
        for compteur in (q,p):
            compteur['attempts']+=1;compteur['reserved_tokens']+=total
            compteur['event_attempts']+=int(evenement)
        b['reserved_usd']=str(montant(b['reserved_usd'])+cout)
        s['last_sent_ms']=maintenant
        t['api_attempts'][cle]=dict(attempt_id=cle,job_id=job.job_id,provider=pid,kind=job.kind,
            day=jour,month=mois,sent_ms=maintenant,input_upper=entree,
            output_max=r.p['max_output_tokens_including_reasoning'],reserved_usd=str(cout),
            input_price=str(profil.prix_entree or Decimal(0)),
            output_price=str(profil.prix_sortie or Decimal(0)),status='UNKNOWN',
            actual_input=None,actual_output=None,actual_cost=None,usage=None)
        return DecisionBudget(ReservationAPI(cle,job.job_id,pid,jour,mois,entree,
            r.p['max_output_tokens_including_reasoning'],cout))

    def signaler_echec(self,fournisseur,instant_ms,statut=None,retry_after_ms=0):
        self.r.fournisseur(fournisseur);instant(instant_ms);entier(retry_after_ms)
        if statut is not None:entier(statut)
        def operation(t):
            s=_route(t,fournisseur)
            s['not_before_ms']=max(s['not_before_ms'],instant_ms+retry_after_ms)
            if statut in (401,403):s.update(disabled=True,reason='HTTP_AUTH_REFUSEE')
            return dict(s)
        return self._transaction(operation)

    def rapprocher(self,tentative_id,tokens_entree,tokens_sortie,usage_brut,instant_ms):
        texte(tentative_id);instant(instant_ms)
        for valeur in (tokens_entree,tokens_sortie):
            if valeur is not None:entier(valeur)
        if usage_brut is not None and type(usage_brut) is not dict:
            raise ErreurService('USAGE_BRUT_INVALIDE')
        usage=decoder(canonique(usage_brut)) if usage_brut is not None else None
        def operation(t):
            a=t['api_attempts'].get(tentative_id)
            if a is None:raise ErreurService('TENTATIVE_INCONNUE')
            if instant_ms<a['sent_ms']:raise ErreurService('RAPPROCHEMENT_NON_CAUSAL')
            s=_route(t,a['provider'])
            if a['status']!='UNKNOWN':
                if (tokens_entree is not None and tokens_sortie is not None
                        and (tokens_entree!=a['actual_input'] or tokens_sortie!=a['actual_output'])):
                    s.update(disabled=True,reason='RAPPROCHEMENT_CONTRADICTOIRE')
                    a.update(status='CONTRADICTORY',conflicting_usage=usage)
                    t['alerts']['budget:'+tentative_id]=dict(code='RAPPROCHEMENT_CONTRADICTOIRE',instant_ms=instant_ms)
                return dict(a)
            a.update(usage=usage,reconciled_ms=instant_ms)
            if tokens_entree is None or tokens_sortie is None:return dict(a)
            cout=_cout(tokens_entree,tokens_sortie,a['input_price'],a['output_price'])
            b=_budget(t,a['month']);reserve=montant(a['reserved_usd'])
            if montant(b['reserved_usd'])<reserve:raise ErreurService('RESERVE_REGISTRE_INCOHERENTE')
            b['reserved_usd']=str(montant(b['reserved_usd'])-reserve)
            b['spent_usd']=str(montant(b['spent_usd'])+cout)
            depasse=(cout>reserve or tokens_entree>a['input_upper'] or tokens_sortie>a['output_max'])
            a.update(actual_input=tokens_entree,actual_output=tokens_sortie,actual_cost=str(cout),
                     status='BOUND_EXCEEDED' if depasse else 'KNOWN')
            if depasse:
                s.update(disabled=True,reason='CONSOMMATION_HORS_BORNE')
                t['alerts']['budget:'+tentative_id]=dict(code='CONSOMMATION_HORS_BORNE',instant_ms=instant_ms)
            return dict(a)
        return self._transaction(operation)
