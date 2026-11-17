"""Rapport C04 en lecture seule ; les ressources appartiennent à l'enveloppe."""
from collections.abc import Mapping
from dataclasses import fields,is_dataclass
from decimal import Decimal
from enum import Enum

from xpbots.app.c0_configuration import ConfigurationApplication,ErreurApplication
from xpbots.infra.c0a_types import TableHeureServeur,champ_natif,entier_natif
from xpbots.infra.c4_assemblage import InfrastructurePhysique
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument


def _valeur(v):
    if isinstance(v,Enum):return v.value
    if isinstance(v,Decimal):return str(v)
    if is_dataclass(v):return {f.name:_valeur(getattr(v,f.name)) for f in fields(v)}
    if isinstance(v,Mapping):return {k:_valeur(x) for k,x in v.items()}
    if isinstance(v,(set,frozenset)):return tuple(sorted(_valeur(x) for x in v))
    if isinstance(v,(tuple,list)):return tuple(_valeur(x) for x in v)
    return v


def qualifier(application,infrastructure,table,qualification):
    if (not isinstance(application,ConfigurationApplication) or not isinstance(infrastructure,InfrastructurePhysique)
            or not isinstance(table,TableHeureServeur) or infrastructure.meta!=application.meta):
        raise ErreurApplication('COMPOSITION_QUALIFICATION_INCOHERENTE')
    a=application;i=infrastructure;ingenierie=a.ingenierie
    historique=a.registre['historique'];erreurs=[];profils={};compte=None;type_natif='INCONNU';preuve_s08=False
    etat=i.session.etat
    try:
        etat=i.session.actualiser()
        if not etat.connecte:erreurs.append('SESSION_DECONNECTEE')
        if a.mode in ('DEMO','REEL') and not etat.droits:erreurs.append('DROITS_NATIFS_INSUFFISANTS')
        brut=i.session.appeler('account_info')
        mode=entier_natif(champ_natif(brut,'trade_mode'));sdk=i.session.sdk
        modes=((sdk.ACCOUNT_TRADE_MODE_DEMO,'DEMO'),(sdk.ACCOUNT_TRADE_MODE_REAL,'REEL'),
               (sdk.ACCOUNT_TRADE_MODE_CONTEST,'CONTEST'))
        type_natif=next((n for v,n in modes if v==mode),'INCONNU')
        if type_natif=='INCONNU':erreurs.append('TYPE_COMPTE_NATIF_INCONNU')
    except (ValueError,OSError):erreurs.append('ETAT_SESSION_ILLISIBLE')
    options=dict(departs_ticks_utc_ms=dict(historique['departs_ticks_utc_ms']),
        depuis_historique_compte_utc_ms=historique['depuis_compte_utc_ms'],
        seances_max_age_ms=ingenierie['seances_max_age_ms'],fermetures_max_age_ms=ingenierie['fermetures_max_age_ms'],
        max_jours_horaires=ingenierie['max_jours_horaires'],ecart_horloges_max_ms=ingenierie['ecart_horloges_max_ms'],
        taille_lot=ingenierie['taille_lot_ticks'],max_ticks_lot=ingenierie['max_ticks_lot'],
        longueur_empreinte=ingenierie['longueur_empreinte'],max_taches_natives=ingenierie['max_taches_natives'])
    try:
        courtier=i.initialiser_courtier(table,qualification,options)
        receptions=i.lire_controles()
        seances={a.liaisons[r.symbole]:r.octets for r in receptions if r.nature=='SEANCES'}
        fermetures=next(r.octets for r in receptions if r.nature=='FERMETURES')
        t=i.horloge.utc_ms();courtier.recevoir_exports(t,seances=seances,fermetures=fermetures)
        pc=courtier.profil_compte(t)
        preuve_compte=courtier.specifications.preuve_compte(t)
        preuve_s08=isinstance(preuve_compte,Mapping) and preuve_compte.get('historique_complet') is True
        if isinstance(pc,ProfilCompte):compte=_valeur(pc)
        else:erreurs.append('COMPTE_C04_NON_PRET')
        for symbole in a.liaisons:
            p=courtier.specifications.instrument(symbole,t)
            if isinstance(p,ProfilInstrument):profils[symbole]=dict(profil=_valeur(p),environnement_non_pret=())
            else:
                erreurs.append('INSTRUMENT_C04_NON_PRET:'+symbole)
                profils[symbole]=dict(profil=None,environnement_non_pret=('ENVIRONMENT_NOT_READY',))
        if courtier.specifications.erreurs_exports:erreurs.append('EXPORTS_D12_NON_PRETS')
    except (ValueError,OSError):
        t=i.horloge.utc_ms();erreurs.append('INITIALISATION_C04_REFUSEE')
    sondes={
        'S01':dict(statut='TABLE_EXTERNE_DECLAREE',version=table.version,date_releve=table.date_releve,
                   mesures=table.mesures),
        'S02':dict(statut='A_CONFRONTER_13_1',objet='PROTECTIONS_A_L_ENTREE'),
        'S03':dict(statut='A_CONFRONTER_13_1',objet='CODES_ET_FLAGS_NATIFS'),
        'S04':dict(statut='A_CONFRONTER_13_1',objet='TRANSACTIONS_ET_PARTIELS'),
        'S05':dict(statut='A_CONFRONTER_13_1',objet='MAGIC_COMMENTAIRE_ET_PROPRIETE'),
        'S06':dict(statut='A_CONFRONTER_13_1',objet='LATENCES_ET_ACCUSES_AMBIGUS'),
        'S07':dict(statut='NON_EXECUTEE_SANS_SCENARIO_DATE',objet='PROFIT_MARGE_CONTROLE_ORDRE'),
        'S08':dict(statut='PREUVE_EXTERNE_DECLAREE' if preuve_s08 else 'PREUVE_ABSENTE_OU_INVALIDE',objet='COMPLETUDE_DES_HISTORIQUES'),
    }
    return dict(schema='xp-rapport-qualification-v1',deploiement=a.deploiement,mode=a.mode,instant_utc_ms=t,
        versions=dict(paquet=etat.version_paquet,terminal=etat.version_terminal,build=etat.build),
        type_compte_natif=type_natif,compte=compte,liaisons=dict(a.liaisons),instruments=profils,
        sondes=sondes,environnement_non_pret=tuple(sorted(set(erreurs))),
        faisabilite_volume_minimal=dict(statut='NON_EVALUABLE_SANS_SIGNAL_C06',
                                       raison='DISTANCE_DE_STOP_ET_COTATION_DATEES_REQUISES'),
        conclusion='ENVIRONMENT_NOT_READY' if erreurs else 'LECTURES_C04_COMPLETES',
        autorisation_execution=False,validation_financiere='NON_EVALUEE')
