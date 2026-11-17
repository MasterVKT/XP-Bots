"""Ticks natifs en ordre, occurrences conservées et couverture explicite."""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,champ_natif,entier_natif,nombre_decimal
from xpbots.infra.c1_session import SessionMT5
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import Intervalle

_EPOQUE=datetime.fromtimestamp(0,timezone.utc)
_SECONDE_MS=timedelta(seconds=1)//timedelta(milliseconds=1)


@dataclass(frozen=True)
class LotFluxMT5:
    ticks:tuple
    couvertures:tuple
    erreurs:tuple
    a_jour:tuple


def _entier(v,minimum=0):
    if type(v) is not int or v<minimum:raise ErreurInfra('entier de curseur explicite requis')
    return v


def _ligne(ligne):
    ms=entier_natif(champ_natif(ligne,'time_msc'));verifier_instant(ms)
    bid,ask=nombre_decimal(champ_natif(ligne,'bid')),nombre_decimal(champ_natif(ligne,'ask'))
    flags=entier_natif(champ_natif(ligne,'flags'))
    if bid<=0 or ask<=0 or flags<0:raise ErreurInfra('tick natif invalide')
    return ms,float(bid).hex(),float(ask).hex(),flags


class FluxMT5:
    def __init__(self,session,table,liaisons,departs_utc_ms,*,taille_lot,max_ticks_lot,historique_complet,etat=None,
                 convention_ticks='SERVEUR_S01'):
        if not isinstance(session,SessionMT5) or not isinstance(table,TableHeureServeur):raise ErreurInfra('session et table reelles requises')
        if type(convention_ticks) is not str or convention_ticks not in ('UTC','SERVEUR_S01'):
            raise ErreurInfra('convention de ticks qualifiee S01 requise')
        self._convention_ticks=convention_ticks
        if (type(liaisons) is not dict or not liaisons or any(type(s) is not str or not s or type(b) is not str or not b for s,b in liaisons.items())
                or len(set(liaisons.values()))!=len(liaisons) or type(departs_utc_ms) is not dict or set(departs_utc_ms)!=set(liaisons)
                or type(historique_complet) is not dict or set(historique_complet)!=set(liaisons)
                or any(type(v) is not bool for v in historique_complet.values())):
            raise ErreurInfra('liaisons, departs et preuve S08 explicites requis')
        for t in departs_utc_ms.values():verifier_instant(t)
        self._taille=_entier(taille_lot,1);self._maximum=_entier(max_ticks_lot,self._taille)
        self._session,self._table=session,table
        self._liaisons=dict(liaisons);self._departs=dict(departs_utc_ms);self._preuves=dict(historique_complet)
        d=dict(liaisons=liaisons,departs=departs_utc_ms,preuves=historique_complet,taille=self._taille,maximum=self._maximum,
            horodatage_ticks=convention_ticks,
            table=dict(serveur=table.serveur,version=table.version,date_releve=table.date_releve,mesures=table.mesures,
                segments=[(s.debut_utc_ms,s.fin_utc_ms,s.decalage_secondes) for s in table.segments]))
        self._empreinte=sha256(json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self._curseurs={s:dict(dernier_natif_ms=None,prefixe=(),couverture_fin_ms=t) for s,t in self._departs.items()}
        self._numero=0;self._dernier_ms=0
        if etat is not None:self._restaurer(etat)

    def _interroger(self,symbole,t):
        if not self._preuves[symbole]:raise ErreurInfra('HISTORIQUE_NON_QUALIFIE')
        debut=self._departs[symbole];c=self._curseurs[symbole]
        if t<debut or instant_releve(self._table)>t:raise ErreurInfra('INSTANT_NON_CAUSAL')
        curseur=c['dernier_natif_ms']
        recherche=(debut if self._convention_ticks=='UTC' else self._table.serveur_de_utc(debut)) if curseur is None else curseur
        date=_EPOQUE+timedelta(milliseconds=recherche//_SECONDE_MS*_SECONDE_MS)
        compte=self._taille
        while True:
            tableau=self._session.appeler('copy_ticks_from',self._liaisons[symbole],date,compte,self._session.sdk.COPY_TICKS_ALL)
            if not hasattr(tableau,'__len__'):raise ErreurInfra('TABLEAU_NATIF_INVALIDE')
            if len(tableau)>compte:raise ErreurInfra('TABLEAU_NATIF_TROP_LONG')
            lignes=tuple(_ligne(v) for v in tableau)
            if any(b[0]<a[0] for a,b in zip(lignes,lignes[1:])):raise ErreurInfra('ORDRE_NATIF_INVALIDE')
            lignes=tuple(v for v in lignes if v[0]>=recherche)
            plein=len(tableau)==compte
            prefixe=tuple(v for v in lignes if v[0]==curseur) if curseur is not None else ()
            ancien=c['prefixe']
            if curseur is not None and (len(prefixe)<len(ancien) or prefixe[:len(ancien)]!=ancien):
                if plein and len(prefixe)<=len(ancien) and compte<self._maximum:
                    compte=min(self._maximum,compte+compte);continue
                raise ErreurInfra('PREFIXE_NATIF_REECRIT')
            completes=tuple(v for v in lignes if not plein or v[0]!=lignes[-1][0])
            nouvelles=completes[len(ancien):] if curseur is not None else completes
            if not nouvelles and plein:
                if compte>=self._maximum:raise ErreurInfra('PREFIXE_NATIF_HORS_PLAFOND')
                compte=min(self._maximum,compte+compte);continue
            break
        ticks=[]
        for v in nouvelles:
            heure,bid_hex,ask_hex,drapeaux=v
            utc=heure if self._convention_ticks=='UTC' else self._table.utc_de_serveur(heure)
            if not debut<=utc<=t:raise ErreurInfra('TICK_FUTUR_OU_HORS_DEPART')
            ticks.append(Tick(symbole,self._liaisons[symbole],utc,t,self._numero+len(ticks)+1,
                float.fromhex(bid_hex),float.fromhex(ask_hex),drapeaux))
        if any(b.instant_fournisseur_ms<a.instant_fournisseur_ms for a,b in zip(ticks,ticks[1:])):
            raise ErreurInfra('ORDRE_UTC_INVALIDE')
        fin=t if not plein else (lignes[-1][0] if self._convention_ticks=='UTC' else self._table.utc_de_serveur(lignes[-1][0]))
        if fin>t or fin<c['couverture_fin_ms']:raise ErreurInfra('COUVERTURE_NON_CAUSALE')
        if nouvelles:
            dernier=nouvelles[-1][0]
            nouveau=dict(dernier_natif_ms=dernier,prefixe=tuple(v for v in completes if v[0]==dernier),couverture_fin_ms=fin)
        else:nouveau=dict(c,couverture_fin_ms=fin)
        return tuple(ticks),nouveau,not plein

    def lire(self,t):
        verifier_instant(t)
        if t<self._dernier_ms:raise ErreurInfra('reception de flux non causale')
        ticks=[];erreurs=[];a_jour=[]
        try:
            terminal=self._session.appeler('terminal_info');connecte=champ_natif(terminal,'connected')
            if type(connecte) is not bool or not connecte:raise ErreurInfra('CONNEXION_INDISPONIBLE')
        except (ValueError,TypeError,AttributeError):
            connecte=False
        for s in self._liaisons:
            try:
                if not connecte:raise ErreurInfra('CONNEXION_INDISPONIBLE')
                bloc,courant,pret=self._interroger(s,t)
                self._curseurs[s]=courant;self._numero+=len(bloc);ticks.extend(bloc);a_jour.append((s,pret))
                if not pret:erreurs.append((s,'RATTRAPAGE_EN_COURS'))
            except (ValueError,TypeError,KeyError,AttributeError,OverflowError):
                erreurs.append((s,'DONNEES_NATIVES_INDISPONIBLES'));a_jour.append((s,False))
        self._dernier_ms=t
        couvertures=tuple((s,(Intervalle(self._departs[s],c['couverture_fin_ms']),)
            if c['couverture_fin_ms']>self._departs[s] else ()) for s,c in self._curseurs.items())
        return LotFluxMT5(tuple(ticks),couvertures,tuple(erreurs),tuple(a_jour))

    def exporter_etat(self):
        return dict(schema='xp-flux-mt5-v1',configuration_sha256=self._empreinte,numero=self._numero,
            dernier_ms=self._dernier_ms,curseurs={s:dict(c) for s,c in self._curseurs.items()})

    def _restaurer(self,d):
        if (type(d) is not dict or set(d)!={'schema','configuration_sha256','numero','dernier_ms','curseurs'}
                or d['schema']!='xp-flux-mt5-v1' or d['configuration_sha256']!=self._empreinte
                or type(d['curseurs']) is not dict or set(d['curseurs'])!=set(self._liaisons)):
            raise ErreurInfra('etat de flux incompatible')
        _entier(d['numero']);verifier_instant(d['dernier_ms'])
        total=0
        for s,c in d['curseurs'].items():
            if type(c) is not dict or set(c)!={'dernier_natif_ms','prefixe','couverture_fin_ms'}:raise ErreurInfra('curseur invalide')
            verifier_instant(c['couverture_fin_ms'])
            if not self._departs[s]<=c['couverture_fin_ms']<=max(d['dernier_ms'],self._departs[s]):raise ErreurInfra('couverture restauree future')
            if not isinstance(c['prefixe'],(tuple,list)):raise ErreurInfra('prefixe explicite requis')
            prefixe=tuple(tuple(v) for v in c['prefixe'])
            if c['dernier_natif_ms'] is None:
                if prefixe:raise ErreurInfra('prefixe sans curseur')
            else:
                verifier_instant(c['dernier_natif_ms'])
                if c['couverture_fin_ms']>d['dernier_ms']:raise ErreurInfra('curseur restaure apres derniere reception')
                if not prefixe or len(prefixe)>self._maximum:raise ErreurInfra('prefixe restaure vide ou excessif')
                for v in prefixe:
                    if len(v)!=len(('heure','bid','ask','flags')) or type(v[0]) is not int or v[0]!=c['dernier_natif_ms']:
                        raise ErreurInfra('ligne de prefixe invalide')
                    _entier(v[-1])
                    if any(type(x) is not str or float.fromhex(x)<=0 or not nombre_decimal(float.fromhex(x)).is_finite() for x in v[1:-1]):
                        raise ErreurInfra('prix de prefixe invalide')
                utc=c['dernier_natif_ms'] if self._convention_ticks=='UTC' else self._table.utc_de_serveur(c['dernier_natif_ms'])
                if not self._departs[s]<=utc<=c['couverture_fin_ms']:raise ErreurInfra('curseur hors couverture')
            self._curseurs[s]=dict(c,prefixe=prefixe);total+=len(prefixe)
        if total>d['numero'] or bool(total)!=bool(d['numero']):raise ErreurInfra('numero de flux incoherent')
        self._numero=d['numero'];self._dernier_ms=d['dernier_ms']


def instant_releve(table):
    from xpbots.noyau.c0a_temps import instant_depuis_iso
    return instant_depuis_iso(table.date_releve)
