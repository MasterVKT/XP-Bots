"""Points d'entrée London : arguments, frontières physiques et blocs MCL réels."""
import argparse
import json
import re
import sys

from xpbots.app.c0_configuration import (ErreurApplication,analyser_registre,gabarit_registre,
    gabarit_fermetures,parametres_export)
from xpbots.app.c1c_cli_rejeu import decoder_rejeu,lancer_rejeu
from xpbots.app.c1d_cli_qualification import qualifier
from xpbots.app.c1e_cli_rapports import rapporter_archives,rapporter_incident
from xpbots.app.c2_boucle_direct import BoucleDirect
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c0d_journal import alerter
from xpbots.infra.c0h_verrou import VerrouProcessus
from xpbots.infra.c4_assemblage import InfrastructurePhysique,lire_configuration,lire_fichier,ecrire_fichier
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c0c_configuration import charger_configuration_figee
from xpbots.rejeu.c2_executeur import AutorisationReserve,DemandeRejeu
from xpbots.rejeu.c3_rapports import serialiser_rapport
from ._reserve import joindre,octets_document,contexte,creer_gel,AttestationReserve

_PLAFOND_DOCUMENT=64*1024*1024  # Borne technique ajustable, distincte des paramètres métier.


class _Parseur(argparse.ArgumentParser):
    def error(self,message):
        # Un argument inconnu peut contenir une valeur privée : ne pas le recopier.
        self.print_usage(sys.stderr)
        self.exit(2,'{"schema":"xp-erreur-cli-v1","code":"ARGUMENTS_INVALIDES"}\n')


def _parseur():
    p=_Parseur(prog='python -m xpbots.app',description='Commandes du robot London M15.')
    p.add_argument('--racine-depot',default='.',help='Racine des sources et ressources de confiance.')
    p.add_argument('--max-octets-document',type=int,default=_PLAFOND_DOCUMENT,
                   help='Borne technique de lecture des documents et archives.')
    sous=p.add_subparsers(dest='commande',required=True)
    options={
        'gabarits':('sortie-registre','sortie-fermetures'),
        'parametres-export':('registre','sortie'),
        'qualifier':('registre','sortie'),
        'direct':('registre','archive-incident'),
        'rejeu':('registre','demande','ticks','archive','rapport'),
        'rapports':('registre','sortie'),
        'incident':('archive','sortie'),
        'geler-code':('registre','sortie')}
    for nom,arguments in options.items():
        c=sous.add_parser(nom)
        for a in arguments:c.add_argument('--'+a,required=True)
        c.add_argument('--ecraser',action='store_true',help='Autoriser le remplacement des sorties explicites.')
        if nom in ('qualifier','direct'):c.add_argument('--terminal',help='Chemin du terminal déjà configuré, sans identifiant.')
        if nom=='direct':
            c.add_argument('--jusqua-utc');c.add_argument('--max-iterations',type=int)
        if nom=='rejeu':
            c.add_argument('--ouvrir-reserve',action='store_true');c.add_argument('--gel')
        if nom=='rapports':c.add_argument('--archives',nargs='+',required=True)
    return p


def _configuration(a):
    noms=('config/parametres_figes_v3.json','config/parametres_IA_integration_v1.json',
          'docs/validation/conservation_ressources.json')
    return charger_configuration_figee(*(lire_fichier(joindre(a.racine_depot,n),a.max_octets_document)
                                         for n in noms))


def _ecrire(a,chemin,v):ecrire_fichier(chemin,octets_document(v),ecraser=a.ecraser)

def _dossier(application,rapport):
    return dict(schema='xp-dossier-validation-v1',**contexte(application),rapport=rapport)


def _fermer(i,application):
    signale=False
    while not i.fermer(application.ingenierie['attente_arret_ms']):
        if not signale:
            alerter('ARRET_NATIVE_EN_COURS','CONSERVER_LE_PROCESSUS_ET_RAPPROCHER_A_LA_REPRISE');signale=True
        i.horloge.attendre_ms(application.ingenierie['boucle_ms'])


def _physique(a,configuration,application,sdk):
    chemins=application.registre['chemins'];plafond=a.max_octets_document
    table=TableHeureServeur.depuis_document(lire_configuration(chemins['table_heure'],plafond))
    preuve=lire_configuration(chemins['qualification'],plafond)
    i=InfrastructurePhysique(configuration.technique.commun,application.meta,application.liaisons,
        racine=chemins['racine'],max_octets_echange=application.ingenierie['max_octets_echange'],
        snapshot_max_octets=configuration.ia.parametres['snapshot_max_bytes'],sdk=sdk,chemin_terminal=a.terminal)
    try:
        if a.commande=='qualifier':
            r=qualifier(application,i,table,preuve);_ecrire(a,a.sortie,r);return r,0
        b=BoucleDirect(application,i,table,preuve);code=0
        try:
            fin=None if a.jusqua_utc is None else instant_depuis_iso(a.jusqua_utc)
            r=b.executer(jusqua_ms=fin,max_iterations=a.max_iterations)
        except KeyboardInterrupt:
            code=130;r=dict(schema='xp-rapport-direct-v1',arret='DEMANDE_OPERATEUR',validation_financiere='NON_EVALUEE')
        try:
            archive=b.archive_incident()
        except ErreurApplication as erreur:
            if code!=130 or str(erreur)!='AUCUN_COMMIT_A_ARCHIVER':raise
            r=dict(r,archive_incident=None)
        else:
            ecrire_fichier(a.archive_incident,archive,ecraser=a.ecraser)
            r=dict(r,archive_incident=a.archive_incident,archive_limitee_au_dernier_commit=True)
        return r,code
    finally:_fermer(i,application)


def _rejeu(a,configuration,application,horloge):
    d=decoder_rejeu(lire_fichier(a.demande,a.max_octets_document))
    if type(d) is not dict or not isinstance(d.get('demande'),DemandeRejeu):
        raise ErreurApplication('DEMANDE_REJEU_INVALIDE')
    if bool(a.gel)!=a.ouvrir_reserve:raise ErreurApplication('OPTION_ET_GEL_RESERVE_REQUIS_ENSEMBLE')
    trace=()
    if a.ouvrir_reserve:
        verrou=joindre(a.racine_depot,'.local/validation/registre_reserve.lock')
        with VerrouProcessus(verrou):
            port=AttestationReserve(application,a.racine_depot,a.gel,horloge,a.max_octets_document,
                                    __file__,d['demande'].identifiant)
            autorisation=AutorisationReserve(True,port.empreinte,port)
            try:r=lancer_rejeu(configuration,d,a.ticks,autorisation=autorisation)
            except (ValueError,OSError):
                if port.raison_refus:raise ErreurApplication(port.raison_refus) from None
                raise
            trace=tuple(port.trace)
    else:r=lancer_rejeu(configuration,d,a.ticks)
    ecrire_fichier(a.archive,r['archive'],ecraser=a.ecraser)
    _ecrire(a,a.rapport,_dossier(application,r['rapport']))
    return dict(schema='xp-resultat-commande-v1',commande='rejeu',archive=a.archive,rapport=a.rapport,
                statut=r['rapport']['statut'],trace_reserve=trace)


def _executer(a,sdk):
    if a.max_octets_document<=0:raise ErreurApplication('PLAFOND_DOCUMENT_INVALIDE')
    c=_configuration(a);h=HorlogeSysteme()
    if a.commande=='gabarits':
        _ecrire(a,a.sortie_registre,gabarit_registre(c));_ecrire(a,a.sortie_fermetures,gabarit_fermetures())
        return dict(schema='xp-resultat-commande-v1',commande=a.commande,statut='GABARITS_NON_EXECUTABLES'),0
    if a.commande=='incident':
        r=rapporter_incident(c,lire_fichier(a.archive,a.max_octets_document));_ecrire(a,a.sortie,r)
        return r,0
    application=analyser_registre(lire_configuration(a.registre,a.max_octets_document),c,h.utc_ms(),
                                 qualification=a.commande!='direct')
    if a.commande in ('qualifier','direct'):return _physique(a,c,application,sdk)
    if a.commande=='parametres-export':
        table=TableHeureServeur.depuis_document(lire_configuration(application.registre['chemins']['table_heure'],a.max_octets_document))
        b=parametres_export(c,table,application.liaisons,application.ingenierie)
        ecrire_fichier(a.sortie,b,ecraser=a.ecraser)
        return dict(schema='xp-resultat-commande-v1',commande=a.commande,octets=len(b)),0
    if a.commande=='geler-code':
        r=creer_gel(application,a.racine_depot,h.utc_ms(),a.max_octets_document,__file__)
        _ecrire(a,a.sortie,r)
        return dict(schema='xp-resultat-commande-v1',commande=a.commande,sha256=r['inventaire']['sha256']),0
    if a.commande=='rejeu':return _rejeu(a,c,application,h),0
    if a.commande=='rapports':
        r=rapporter_archives(c,tuple(lire_fichier(p,a.max_octets_document) for p in a.archives))
        _ecrire(a,a.sortie,_dossier(application,r))
        return dict(schema='xp-resultat-commande-v1',commande=a.commande,statut=r['statut']),0
    raise ErreurApplication('COMMANDE_INCONNUE')


def main(argv=None,*,sdk=None):
    try:a=_parseur().parse_args(argv)
    except SystemExit as sortie:return int(sortie.code)
    try:r,code=_executer(a,sdk)
    except KeyboardInterrupt:
        r=dict(schema='xp-erreur-cli-v1',code='ARRET_DEMANDE');code=130
    except (ValueError,OSError,TypeError,KeyError) as erreur:
        texte=str(erreur)
        r=dict(schema='xp-erreur-cli-v1',code=texte if re.fullmatch('[A-Z][A-Z0-9_]*',texte) else 'OPERATION_REFUSEE');code=2
    # JSON ASCII sur console ; les artefacts sont toujours UTF-8 par le sérialiseur réel.
    print(json.dumps(json.loads(serialiser_rapport(r)),ensure_ascii=True,sort_keys=True,separators=(',',':')))
    return code
