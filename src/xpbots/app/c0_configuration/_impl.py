"""Configuration pure de la coquille ; aucune lecture physique ou horloge."""
from collections.abc import Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType

from xpbots.noyau.c0a_temps import instant_depuis_iso,verifier_instant
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.infra.c0a_types import TableHeureServeur


class ErreurApplication(ValueError):
    """Configuration d'exécution absente, incohérente ou non autorisée."""


# D-09 et protocole du service MQL5 ; constantes d'ingénierie, hors stratégie.
_INGENIERIE={
    'boucle_ms':100,'minuterie_ms':1000,'controles_ms':1000,'snapshot_ms':1000,
    'calendrier_export_ms':60000,'seances_export_ms':3600000,
    'max_octets_echange':1048576,'taille_lot_ticks':4096,'max_ticks_lot':1048576,
    'max_taches_natives':4,'longueur_empreinte':16,'attente_arret_ms':3000,
    'seances_max_age_ms':7200000,'fermetures_max_age_ms':86400000,
    'max_jours_horaires':64,'ecart_horloges_max_ms':1000,
}
_CADENCES=('boucle_ms','minuterie_ms','controles_ms','snapshot_ms',
           'calendrier_export_ms','seances_export_ms')
_MODES=('PAPER','PAPER_AB','DEMO','REEL')
_MS_PAR_SECONDE=1000
_MAX_PARAMETRES_MQL5=131072
_CLES={'schema','deploiement','mode','commit','empreintes','liaisons',
       'justifications_liaisons','chemins','historique','ingenierie',
       'scenario_fondamental','activation_veto','statut_a13','decisions'}


def _champs(v,cles):
    if not isinstance(v,Mapping) or set(v)!=set(cles):
        raise ErreurApplication('CHAMPS_REGISTRE_INVALIDES')
    return v


def _texte(v):
    if type(v) is not str or not v.strip() or any(c in v for c in ('\r','\n','\t','\0')):
        raise ErreurApplication('TEXTE_REGISTRE_INVALIDE')
    return v


def _nom(v):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',_texte(v)) or '..' in v:
        raise ErreurApplication('NOM_REGISTRE_INVALIDE')
    return v


def _sha(v,*,commit=False):
    tailles=(40,64) if commit else (64,)
    if type(v) is not str or len(v) not in tailles or any(c not in '0123456789abcdef' for c in v):
        raise ErreurApplication('EMPREINTE_REGISTRE_INVALIDE')
    return v


def _chemin(v):
    _texte(v)
    # La résolution physique et les liens sont contrôlés dans l'infrastructure.
    if any(p.casefold()=='.env' or p.casefold().startswith('.env.') for p in v.replace('\\','/').split('/')):
        raise ErreurApplication('FICHIER_ENV_INTERDIT')
    return v


def _instant(v):
    try:return verifier_instant(v)
    except ValueError:raise ErreurApplication('INSTANT_REGISTRE_INVALIDE') from None


def _figer(v):
    if isinstance(v,Mapping):return MappingProxyType({k:_figer(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(_figer(x) for x in v)
    return v


def _ingenierie(v):
    _champs(v,_INGENIERIE)
    if any(type(n) is not int or n<=0 for n in v.values()):
        raise ErreurApplication('CONSTANTES_INGENIERIE_INVALIDES')
    if any(v[k]!=_INGENIERIE[k] for k in _CADENCES):
        raise ErreurApplication('CADENCES_D09_MQL5_NON_CONFORMES')
    if v['max_ticks_lot']<v['taille_lot_ticks'] or v['max_taches_natives']<=1:
        raise ErreurApplication('CAPACITE_INGENIERIE_INVALIDE')
    return v


def _preuves(v):
    if not isinstance(v,Mapping):raise ErreurApplication('PREUVES_DECISION_REQUISES')
    for nature,p in v.items():
        _texte(nature);_champs(p,('chemin','sha256'));_chemin(p['chemin']);_sha(p['sha256'])


@dataclass(frozen=True)
class ConfigurationApplication:
    configuration:ConfigurationFigee
    registre:Mapping

    @property
    def deploiement(self):return self.registre['deploiement']
    @property
    def mode(self):return self.registre['mode']
    @property
    def liaisons(self):return self.registre['liaisons']
    @property
    def ingenierie(self):return self.registre['ingenierie']
    @property
    def meta(self):
        return dict(deploiement=self.deploiement,mode=self.mode,commit=self.registre['commit'],
                    empreintes=dict(self.registre['empreintes']))


def analyser_registre(document,configuration,instant_ms,*,qualification=False):
    if not isinstance(configuration,ConfigurationFigee) or type(qualification) is not bool:
        raise ErreurApplication('CONFIGURATION_FIGEE_REQUISE')
    t=_instant(instant_ms);d=_champs(document,_CLES)
    if d['schema']!='xp-deploiement-v1' or d['mode'] not in _MODES:
        raise ErreurApplication('SCHEMA_OU_MODE_INVALIDE')
    _nom(d['deploiement']);_sha(d['commit'],commit=True)
    e=_champs(d['empreintes'],('technique','ia'))
    attendues={'technique':configuration.technique.empreinte_octets,'ia':configuration.ia.empreinte_octets}
    if dict(e)!=attendues:raise ErreurApplication('CONFIGURATIONS_ETRANGERES')
    l=d['liaisons'];j=d['justifications_liaisons']
    if not isinstance(l,Mapping) or not l or not set(l)<=set(configuration.technique.commun.universe_priority):
        raise ErreurApplication('LIAISONS_REQUISES')
    _champs(j,l)
    for s,n in l.items():_nom(n);_texte(j[s])
    if len(set(l.values()))!=len(l):raise ErreurApplication('LIAISON_NATIVE_DUPLIQUEE')
    _champs(d['chemins'],('racine','qualification','table_heure'))
    for v in d['chemins'].values():_chemin(v)
    h=_champs(d['historique'],('departs_ticks_utc_ms','depuis_compte_utc_ms'))
    _champs(h['departs_ticks_utc_ms'],l)
    for v in (*h['departs_ticks_utc_ms'].values(),h['depuis_compte_utc_ms']):
        if _instant(v)>t:raise ErreurApplication('HISTORIQUE_FUTUR')
    _ingenierie(d['ingenierie'])
    scenario=d['scenario_fondamental']
    if scenario not in (None,'TECHNICAL_CONTROL_NEUTRAL'):
        raise ErreurApplication('SCENARIO_FONDAMENTAL_INVALIDE')
    natif=d['mode'] in ('DEMO','REEL')
    if natif and scenario is not None:raise ErreurApplication('NEUTRALITE_NATIVE_INTERDITE')
    if type(d['activation_veto']) is not bool:raise ErreurApplication('ACTIVATION_VETO_INVALIDE')
    a13=_champs(d['statut_a13'],('statut','rapport','empreinte'))
    if a13['statut'] not in ('VALIDE','NON_VALIDE'):raise ErreurApplication('STATUT_A13_INVALIDE')
    if a13['statut']=='VALIDE':_chemin(a13['rapport']);_sha(a13['empreinte'])
    elif a13['rapport'] is not None or a13['empreinte'] is not None:
        raise ErreurApplication('STATUT_A13_INCOHERENT')
    decisions=d['decisions']
    if not isinstance(decisions,(tuple,list)):raise ErreurApplication('DECISIONS_REQUISES')
    ids=set()
    for x in decisions:
        _champs(x,('id','instant_utc','objet','responsable','commit','empreintes','preuves'))
        _nom(x['id']);_texte(x['responsable']);_texte(x['objet']);_sha(x['commit'],commit=True)
        _champs(x['empreintes'],('technique','ia'))
        for v in x['empreintes'].values():_sha(v)
        try:date=instant_depuis_iso(x['instant_utc'])
        except (TypeError,ValueError):raise ErreurApplication('DATE_DECISION_INVALIDE') from None
        if date>t or x['id'] in ids:raise ErreurApplication('DECISION_FUTURE_OU_DUPLIQUEE')
        ids.add(x['id']);_preuves(x['preuves'])
    def decide(objet,preuves):
        return any(x['objet']==objet and x['commit']==d['commit'] and dict(x['empreintes'])==dict(e)
                   and set(preuves)<=set(x['preuves']) for x in decisions)
    if not qualification:
        if d['mode']=='REEL' and not decide('DEPLOIEMENT_REEL',('C10_RESERVE','C10_DEMO')):
            raise ErreurApplication('DECISION_DEPLOIEMENT_REEL_REQUISE')
        if natif and d['activation_veto']:
            reference=dict(chemin=a13['rapport'],sha256=a13['empreinte'])
            concorde=any(x['objet']=='ACTIVATION_VETO_A13' and x['commit']==d['commit']
                         and dict(x['empreintes'])==dict(e) and x['preuves'].get('A13')==reference for x in decisions)
            if a13['statut']!='VALIDE' or not concorde:
                raise ErreurApplication('VALIDATION_FINANCIERE_A13_REQUISE')
    return ConfigurationApplication(configuration,_figer(d))


def gabarit_registre(configuration):
    if not isinstance(configuration,ConfigurationFigee):raise ErreurApplication('CONFIGURATION_FIGEE_REQUISE')
    return dict(schema='xp-deploiement-v1',deploiement=None,
        mode=configuration.ia.parametres['default_evaluation_mode'],commit=None,
        empreintes=dict(technique=configuration.technique.empreinte_octets,ia=configuration.ia.empreinte_octets),
        liaisons={},justifications_liaisons={},chemins=dict(racine='.local',
            qualification='.local/qualification/compte.json',table_heure='.local/qualification/heure_serveur.json'),
        historique=dict(departs_ticks_utc_ms={},depuis_compte_utc_ms=None),ingenierie=dict(_INGENIERIE),
        scenario_fondamental=None,activation_veto=False,
        statut_a13=dict(statut='NON_VALIDE',rapport=None,empreinte=None),decisions=[])


def ingenierie_par_defaut():
    """Plafonds de lecture de démarrage, avant le chargement du registre."""
    return MappingProxyType(dict(_INGENIERIE))


def gabarit_fermetures():
    # Les heures et la version doivent être renseignées par l'opérateur.
    return dict(schema='xp-fermetures-v1',version=None,date_releve=None,fermetures=[])


def parametres_export(configuration,table,liaisons,ingenierie):
    if not isinstance(configuration,ConfigurationFigee) or not isinstance(table,TableHeureServeur):
        raise ErreurApplication('TABLE_S01_ET_CONFIGURATION_REQUISES')
    _ingenierie(ingenierie)
    if not isinstance(liaisons,Mapping) or not liaisons or not set(liaisons)<=set(configuration.technique.commun.universe_priority):
        raise ErreurApplication('LIAISONS_REQUISES')
    _texte(table.serveur)
    noms=tuple(_nom(liaisons[s]) for s in configuration.technique.commun.universe_priority if s in liaisons)
    if len(set(noms))!=len(noms):raise ErreurApplication('LIAISON_NATIVE_DUPLIQUEE')
    c=configuration.technique.commun
    horizon=c.news_forward_coverage_seconds+c.news_calendar_max_age_seconds+ingenierie['calendrier_export_ms']//_MS_PAR_SECONDE
    if int(horizon)!=horizon:raise ErreurApplication('HORIZON_ENTIER_REQUIS')
    lignes=['schema\txp-parametres-export-v1','serveur\t'+table.serveur,
            'version_table\t'+str(table.version),'couverture_future_secondes\t'+str(int(horizon))]
    for s in table.segments:
        if s.debut_utc_ms%_MS_PAR_SECONDE or s.fin_utc_ms%_MS_PAR_SECONDE:
            raise ErreurApplication('SEGMENTS_S01_SECONDES_EXACTES_REQUIS')
        lignes.append('segment\t'+str(s.debut_utc_ms//_MS_PAR_SECONDE)+'\t'+
                      str(s.fin_utc_ms//_MS_PAR_SECONDE)+'\t'+str(s.decalage_secondes))
    lignes.extend('symbole\t'+s for s in noms)
    b=('\n'.join(lignes)+'\n').encode('utf-8')
    if len(b)>_MAX_PARAMETRES_MQL5:raise ErreurApplication('PARAMETRES_MQL5_TROP_VOLUMINEUX')
    return b
