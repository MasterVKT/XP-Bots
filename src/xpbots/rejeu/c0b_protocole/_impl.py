"""Valeurs exclusivement textuelles C10 centralisées ; valeurs exportées chargées."""
from dataclasses import dataclass,fields
from datetime import date,datetime,timezone
from decimal import Decimal
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1b_instrument import Intervalle


class ErreurProtocole(ValueError):pass

_CENT_POUR_CENT=100
_CHAMPS_ECART=('nom','champ','valeur')

def _entier(v,minimum=0):
    if type(v) is not int or v<minimum:raise ErreurProtocole('entier de protocole invalide')


def _decimal(v,minimum=Decimal(0),strict=False):
    if not isinstance(v,Decimal) or not v.is_finite() or v<minimum or strict and v==minimum:
        raise ErreurProtocole('décimal de protocole invalide')


def _texte(v):
    if type(v) is not str or not v.strip():raise ErreurProtocole('nom de protocole requis')
    try:v.encode('utf-8')
    except UnicodeError as e:raise ErreurProtocole('nom UTF-8 requis') from e


@dataclass(frozen=True)
class BlocC10:
    nom:str
    debut:date
    fin_exclusive:date
    usage:str
    def __post_init__(self):
        _texte(self.nom);_texte(self.usage)
        if type(self.debut) is not date or type(self.fin_exclusive) is not date or self.fin_exclusive<=self.debut:
            raise ErreurProtocole('bloc de dates invalide')
    @property
    def intervalle_ms(self):
        def ms(j):return instant_depuis_datetime(datetime(j.year,j.month,j.day,tzinfo=timezone.utc))
        return Intervalle(ms(self.debut),ms(self.fin_exclusive))


@dataclass(frozen=True)
class ScenarioExecution:
    nom:str
    delai_ms:int
    ticks_adverses:int
    facteur_spread:Decimal
    def __post_init__(self):
        _texte(self.nom);_entier(self.delai_ms);_entier(self.ticks_adverses)
        _decimal(self.facteur_spread,Decimal(0),True)


@dataclass(frozen=True)
class ParametresBootstrap:
    replications:int
    bloc_jours:int
    graine:int
    percentile_bas:Decimal
    percentile_haut:Decimal
    def __post_init__(self):
        _entier(self.replications,1);_entier(self.bloc_jours,1);_entier(self.graine)
        _decimal(self.percentile_bas);_decimal(self.percentile_haut)
        if not self.percentile_bas<self.percentile_haut<=Decimal(_CENT_POUR_CENT):raise ErreurProtocole('percentiles inversés ou hors bornes')


@dataclass(frozen=True)
class SeuilsC10:
    min_trades_total:int
    min_trades_reserve:int
    min_trades_symbole:int
    min_reference:int
    profit_factor_reference:Decimal
    profit_factor_stress:Decimal
    drawdown_reference:Decimal
    drawdown_stress:Decimal
    retention:Decimal
    frequence_forex:Decimal
    jours_ia:int
    trades_ia:int
    affectes_ia:int
    jours_affectes_ia:int
    retention_ia:Decimal
    def __post_init__(self):
        for n in ('min_trades_total','min_trades_reserve','min_trades_symbole','min_reference',
                  'jours_ia','trades_ia','affectes_ia','jours_affectes_ia'):_entier(getattr(self,n),1)
        for n in ('profit_factor_reference','profit_factor_stress','frequence_forex'):_decimal(getattr(self,n),Decimal(0),True)
        for n in ('drawdown_reference','drawdown_stress','retention','retention_ia'):
            v=getattr(self,n);_decimal(v,Decimal(0),True)
            if v>1:raise ErreurProtocole('fraction de seuil hors bornes')


@dataclass(frozen=True)
class ProtocoleC10:
    blocs:tuple[BlocC10,...]
    continu:BlocC10
    prospectif:BlocC10
    debut_diagnostic_v3:date
    scenarios:tuple[ScenarioExecution,...]
    bootstrap:ParametresBootstrap
    seuils:SeuilsC10
    perturbations:tuple
    prospectif_min_trades:int
    def __post_init__(self):
        for nom,classe in (('blocs',BlocC10),('scenarios',ScenarioExecution)):
            v=getattr(self,nom)
            if not isinstance(v,(tuple,list)) or not v or any(not isinstance(x,classe) for x in v) or len({x.nom for x in v})!=len(v):
                raise ErreurProtocole('collection de protocole invalide')
            object.__setattr__(self,nom,tuple(v))
        if (not isinstance(self.continu,BlocC10) or not isinstance(self.prospectif,BlocC10)
                or type(self.debut_diagnostic_v3) is not date or not isinstance(self.bootstrap,ParametresBootstrap)
                or not isinstance(self.seuils,SeuilsC10)):raise ErreurProtocole('sous-protocoles réels requis')
        if any(a.fin_exclusive!=b.debut for a,b in zip(self.blocs,self.blocs[1:])):raise ErreurProtocole('blocs non contigus')
        _entier(self.prospectif_min_trades,1)
        if not isinstance(self.perturbations,(tuple,list)):raise ErreurProtocole('perturbations explicites requises')
        ecarts=[]
        for ligne in self.perturbations:
            if not isinstance(ligne,(tuple,list)) or len(ligne)!=len(_CHAMPS_ECART):raise ErreurProtocole('triple de perturbation requis')
            nom,champ,v=ligne;_texte(nom)
            if champ in ('OBJECTIF','BUFFER'):_decimal(v,Decimal(0),True)
            elif champ=='DUREE':_entier(v,1)
            else:raise ErreurProtocole('champ de perturbation inconnu')
            ecarts.append(tuple(ligne))
        if len({e[0] for e in ecarts})!=len(ecarts):raise ErreurProtocole('perturbations dupliquées')
        object.__setattr__(self,'perturbations',tuple(ecarts))
    def scenario(self,nom):
        for s in self.scenarios:
            if s.nom==nom:return s
        raise ErreurProtocole('scénario absent du protocole')


# Ces bornes et seuils ne sont pas des paramètres à ajuster : C10 textuel 3.1.0.
_BORNES=(date(2019,12,2),date(2020,1,1),date(2023,1,1),date(2025,1,1),date(2026,5,1),date(2026,11,4))
_NOMS=('INITIALISATION','DEVELOPPEMENT','VALIDATION','RESERVE','DIAGNOSTIC')
_SEUILS_TEXTUELS_C10=(200,100,50,50,Decimal('1.15'),Decimal('1.00'),Decimal('.10'),Decimal('.15'))
_PROSPECTIF_C10=(date(2026,11,5),date(2027,2,5),100)
_SCENARIOS_C10=(('REFERENCE',250,1,Decimal(1)),('STRESS',1000,2,Decimal('1.25')))
_DEBUT_DIAGNOSTIC_V3=date(2026,5,11)
_BAS=Decimal('0.9');_HAUT=Decimal('1.1')
_ECARTS=(('OBJECTIF_0_9','OBJECTIF',_BAS),('OBJECTIF_1_1','OBJECTIF',_HAUT),
    ('BUFFER_0_9','BUFFER',_BAS),('BUFFER_1_1','BUFFER',_HAUT),
    ('DUREE_6480','DUREE',6480),('DUREE_7920','DUREE',7920))


def charger_protocole(configuration):
    if not isinstance(configuration,ConfigurationFigee):raise ErreurProtocole('configuration chargée requise')
    p=configuration.ia.parametres;c=configuration.technique.commun
    try:
        bootstrap=ParametresBootstrap(p['bootstrap_replications'],p['bootstrap_block_market_days'],p['bootstrap_seed'],
            Decimal(str(p['bootstrap_lower_percentile'])),Decimal(str(p['bootstrap_upper_percentile'])))
        seuils=SeuilsC10(*_SEUILS_TEXTUELS_C10,
            Decimal(str(c.trade_count_retention_target)),Decimal(str(c.combined_mean_fills_per_trading_day_target)),
            p['financial_min_market_days'],p['financial_min_closed_trades_per_strategy'],p['financial_min_affected_baseline_trades'],
            p['financial_min_affected_market_days'],Decimal(str(p['financial_min_retention'])))
    except (KeyError,TypeError,ValueError,ArithmeticError) as e:raise ErreurProtocole('paramètres de protocole invalides') from e
    blocs=tuple(BlocC10(n,a,b,n) for n,a,b in zip(_NOMS,_BORNES,_BORNES[1:]))
    return ProtocoleC10(blocs,BlocC10('CONTINU',_BORNES[1],_BORNES[-1],'CONTINU'),
        BlocC10('DEMONSTRATION',_PROSPECTIF_C10[0],_PROSPECTIF_C10[1],'PROSPECTIF'),_DEBUT_DIAGNOSTIC_V3,
        tuple(ScenarioExecution(*s) for s in _SCENARIOS_C10),
        bootstrap,seuils,_ECARTS,_PROSPECTIF_C10[-1])
