"""Commandes du service ; lecture des clés seulement à l'exécution autorisée."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from threading import Event
import json
import os
from xpbots.noyau.c0c_configuration import charger_configuration_figee
from xpbots.noyau.c0a_temps import instant_depuis_datetime
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0d_journal import lire_octets,ecrire_atomique
from xpbots.fondamental.c0_types import TableImportance
from xpbots.service_ia.c0_types import RessourcesIA,ErreurService,canonique,decoder,iso,texte,utc
from xpbots.service_ia.c1d_budget import ProfilRoute,RegistreBudget
from xpbots.service_ia.c2a_veto import CorrespondanceCalendrier,TableAppariement
from xpbots.service_ia.c3_planificateur import CasDerive
from ._sqlite import DepotServiceSQLite
from ._physique import HorlogeService
from ._service import ServiceIA,_chemin


def charger_ressources(racine):
    r=_chemin(racine)
    # Ressources livrées avec le code, contrôlées par les empreintes de conservation.
    def lire(nom):return _chemin(r/nom).read_bytes()
    configuration=charger_configuration_figee(lire('config/parametres_figes_v3.json'),
        lire('config/parametres_IA_integration_v1.json'),lire('docs/validation/conservation_ressources.json'))
    return RessourcesIA(configuration,lire('schemas/schema_extraction_LLM_v1.json'),
        lire('schemas/schema_notes_IA_v1.json'),lire('prompts/prompts_IA_v1.json'))


def _profil_exemple(r):
    providers=[]
    for p,env in zip(r.p['providers'],('GROQ_API_KEY','GEMINI_API_KEY','OPENAI_API_KEY')):
        providers.append(dict(fournisseur=p['id'],modele=p['model'],profil_facturation=p['billing_profile'],
            quota_tokens_minute=0,quota_requetes_minute=0,quota_requetes_jour=0,quota_tokens_jour=0,
            verifie_ms=None,gratuit_confirme=False,projet_dedie=False,cle_disponible=False,
            prix_entree=p.get('input_usd_per_million_upper_bound'),
            prix_sortie=p.get('output_usd_per_million_upper_bound'),env_key=env))
    return dict(schema='xp-service-profile-v1',providers=providers,calendar=None,golden_cases=[])


def charger_profil(r,chemin,*,autoriser_cles=False,paiement_autorise=False):
    if type(paiement_autorise) is not bool:raise ErreurService('AUTORISATION_PAIEMENT_INVALIDE')
    if chemin is None:return (),{},None,(),()
    p=_chemin(chemin);v=decoder(lire_octets(p,r.p['rss_max_download_bytes']))
    if set(v)!={'schema','providers','calendar','golden_cases'} or v['schema']!='xp-service-profile-v1':
        raise ErreurService('PROFIL_SERVICE_INVALIDE')
    if type(v['providers']) is not list or type(v['golden_cases']) is not list:
        raise ErreurService('PROFIL_SERVICE_INVALIDE')
    profils=[];cles={};routes=[]
    for a in v['providers']:
        a=dict(a);env=a.pop('env_key');texte(env)
        if not env.isidentifier():raise ErreurService('NOM_VARIABLE_CLE_INVALIDE')
        r.fournisseur(a['fournisseur'])
        cle=os.environ.get(env) if autoriser_cles else None
        a['cle_disponible']=bool(cle)
        profil=ProfilRoute(**a);profils.append(profil)
        if cle:
            cles[profil.fournisseur]=cle
            payant='input_usd_per_million_upper_bound' in r.fournisseur(profil.fournisseur)
            if not payant or paiement_autorise:routes.append(profil.fournisseur)
    cas=tuple(CasDerive(a['case_id'],canonique(a['dossier']),canonique(a['attendu'])) for a in v['golden_cases'])
    calendrier=None
    if v['calendar'] is not None:
        c=v['calendar']
        if set(c)!={'path','server_time_table','importance','issuer_mapping','max_octets'}:raise ErreurService('PROFIL_CALENDRIER_INVALIDE')
        def lire(nom):return decoder(lire_octets(_chemin(p.parent/c[nom]),r.p['rss_max_download_bytes']))
        table=TableHeureServeur.depuis_document(lire('server_time_table'))
        if utc(table.date_releve)>HorlogeService().maintenant_ms():raise ErreurService('TABLE_SERVEUR_FUTURE')
        importance=TableImportance(**lire('importance'));m=lire('issuer_mapping')
        m['correspondances']=tuple(CorrespondanceCalendrier(**a) for a in m['correspondances'])
        mapping=TableAppariement(**m)
        def convertir(natif):
            dt=datetime.strptime(natif,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc)
            return table.utc_de_serveur(instant_depuis_datetime(dt))
        calendrier=dict(chemin=_chemin(p.parent/c['path']),convertir_serveur=convertir,
            table_importance=importance,table_appariement=mapping,max_octets=c['max_octets'])
    return tuple(profils),cles,calendrier,cas,tuple(routes)


def main(argv=None):
    parser=argparse.ArgumentParser(prog='python -m xpbots.service_ia')
    parser.add_argument('--racine-depot',type=Path,default=Path.cwd())
    parser.add_argument('--base',type=Path);parser.add_argument('--profil',type=Path)
    sous=parser.add_subparsers(dest='commande',required=True)
    sous.add_parser('etat')
    exemple=sous.add_parser('profil-exemple');exemple.add_argument('--sortie',type=Path,required=True)
    executer=sous.add_parser('executer');executer.add_argument('--snapshot',type=Path,required=True)
    executer.add_argument('--autoriser-http',action='store_true');executer.add_argument('--paiement',action='store_true')
    executer.add_argument('--agregats',type=Path)
    provision=sous.add_parser('provisionner');provision.add_argument('--mois',required=True)
    provision.add_argument('--autres',required=True);provision.add_argument('--taxes',required=True)
    usage=sous.add_parser('rapprocher');usage.add_argument('--tentative',required=True)
    usage.add_argument('--tokens-entree',type=int,required=True);usage.add_argument('--tokens-sortie',type=int,required=True)
    usage.add_argument('--usage-json',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        r=charger_ressources(args.racine_depot)
        if args.commande=='profil-exemple':
            p=_chemin(args.sortie)
            if p.exists():raise ErreurService('FICHIER_EXISTANT')
            ecrire_atomique(p,canonique(_profil_exemple(r)));print(json.dumps(dict(status='PROFIL_NON_QUALIFIE')));return 0
        if args.base is None:parser.error('--base est requis pour cette commande')
        h=HorlogeService()
        if args.commande=='executer':
            profils,cles,cal,cas,routes=charger_profil(r,args.profil,autoriser_cles=args.autoriser_http,paiement_autorise=args.paiement)
            with ServiceIA(r,args.base,args.snapshot,horloge=h,profils=profils,cles=cles,
                    calendrier=cal,cas_derives=cas,routes_auditees=routes,agregats=args.agregats,
                    autoriser_http_reel=args.autoriser_http,paiement_autorise=args.paiement) as service:
                service.demarrer();print(json.dumps(service.etat()),flush=True)
                try:
                    while not Event().wait(r.p['ea_snapshot_poll_seconds']):pass
                except KeyboardInterrupt:return 0
        with DepotServiceSQLite(_chemin(args.base),r,creer=False) as depot:
            budget=RegistreBudget(r,depot)
            if args.commande=='etat':
                v=depot.transaction(lambda t:dict(mode=r.p['default_evaluation_mode'],
                    sequence=t['schedule_state'].get('snapshot_sequence',{}).get('sequence'),
                    usages_inconnus=sum(a['status']=='UNKNOWN' for a in t['api_attempts'].values()),
                    fournisseurs={k:v for k,v in t['provider_state'].items() if k.startswith('veto:')}))
            elif args.commande=='provisionner':v=budget.provisionner(args.mois,args.autres,args.taxes)
            else:
                brut=decoder(lire_octets(_chemin(args.usage_json),r.p['max_response_bytes']))
                rapproche=budget.rapprocher(args.tentative,args.tokens_entree,args.tokens_sortie,brut,h.maintenant_ms())
                v={k:rapproche[k] for k in ('attempt_id','status','actual_input','actual_output','actual_cost','reserved_usd')}
            print(json.dumps(v,ensure_ascii=False));return 0
    except (OSError,ValueError,TypeError,KeyError):
        print(json.dumps(dict(status='REFUSE',code='SERVICE_CONFIGURATION_OU_ETAT_INDISPONIBLE')));return 1
