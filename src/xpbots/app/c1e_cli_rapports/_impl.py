"""Rapports du bloc C10 et reconstruction stricte des incidents par les blocs réels."""
from collections.abc import Mapping
from hashlib import sha256

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1a_livre_papier import LivrePapier,TYPES_PAPIER
from xpbots.app.c1c_cli_rejeu import charger_archive
from xpbots.app.c1f_composition_moteur import rejouer_incident
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.rejeu.c3_rapports import produire_rapport


def rapporter_archives(configuration,archives):
    archives=tuple(archives)
    if not archives:raise ErreurApplication('ARCHIVES_C10_REQUISES')
    return produire_rapport(tuple(charger_archive(b,configuration)['resultat'] for b in archives))


def rapporter_incident(configuration,archive):
    d=deserialiser_valeur(archive,types_supplementaires=TYPES_PAPIER)
    if (not isinstance(d,Mapping) or set(d)!={'schema','session','decisions'}
            or d['schema']!='xp-archive-incident-v1'):
        raise ErreurApplication('ARCHIVE_INCIDENT_INVALIDE')
    s=d['session']
    obligatoires={'initialisation','checkpoint','entrees','courtier','livres'}
    if (not isinstance(s,Mapping) or not obligatoires<=set(s) or not set(s)<=obligatoires|{'reprises'}
            or 'reprises' in s and type(s['reprises']) is not tuple
            or type(d['decisions']) is not tuple or any(type(b) is not bytes for b in d['decisions'])):
        raise ErreurApplication('SESSION_INCIDENT_INVALIDE')
    i=deserialiser_valeur(s['initialisation'],types_supplementaires=TYPES_PAPIER)
    if (not isinstance(i,Mapping) or set(i)!={'schema','composition','appels_initialisation','livres'}
            or i['schema']!='xp-initialisation-direct-v1' or set(i['livres'])!=set(s['livres'])):
        raise ErreurApplication('INITIALISATION_INCIDENT_INVALIDE')
    moteur,sorties=rejouer_incident(configuration,i['composition'],dict(i['appels_initialisation']),
                                   s['entrees'],s['checkpoint'],reprises=s.get('reprises',()))
    decisions=tuple(serialiser(e).encode('utf-8') for sortie in sorties for e in sortie.enregistrements)
    if decisions!=d['decisions']:raise ErreurApplication('JOURNAL_C09_INCIDENT_DIVERGENT')
    livres={}
    for nom,v in i['livres'].items():
        charge=s['livres'][nom]
        if not isinstance(charge,Mapping) or set(charge)!={'checkpoint','operations'}:
            raise ErreurApplication('LIVRE_INCIDENT_INVALIDE')
        p=LivrePapier(configuration,v['conditions'],v['creation_ms'],v['scenario'],
            checkpoint=deserialiser_valeur(charge['checkpoint']),operations=charge['operations'])
        livres[nom]=sha256(serialiser_valeur(p.checkpoint)).hexdigest()
    commandes=tuple((sortie.numero,nom,c) for sortie in sorties for nom,b in sortie.sorties for c in b.commandes)
    return dict(schema='xp-rapport-incident-v1',statut='IDENTIQUE',entrees=len(s['entrees']),
        decisions=len(decisions),sha256_c09=sha256(b''.join(b+b'\n' for b in decisions)).hexdigest(),
        empreinte_journal=s['checkpoint'].empreinte_journal,
        empreinte_etat=s['checkpoint'].empreinte,commandes_reconstruites=commandes,
        livres_verifies=livres,validation_financiere='NON_EVALUEE',
        limite='Les commandes sont reconstruites ; le rapport ne fournit aucune autorisation native.')
