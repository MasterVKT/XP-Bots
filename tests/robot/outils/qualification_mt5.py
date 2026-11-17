"""Preuves externes synthétiques explicites, jamais un compte qualifié réel."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
from hashlib import sha256
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur,SegmentServeur
from xpbots.infra.c1_session import SessionMT5
import json

T=1794301200000
JOUR=86400000


def octets(v):return json.dumps(v,ensure_ascii=False,separators=(',',':')).encode('utf-8')
def iso(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def natif(t):return datetime.fromtimestamp(t/1000,timezone.utc).strftime('%Y.%m.%d %H:%M:%S')


def preuve_qualification(sdk=None,t=T):
    sdk=sdk or FauxMT5()
    n=sdk.symboles['EURUSD.micro']
    return dict(schema='xp-qualification-mt5-v1',known_at_utc_ms=t-1000,valid_until_utc_ms=t+10*JOUR,
        decision_id='FIXTURE-C04-NON-QUALIFIEE',preuves=['SONDES_SYNTHETIQUES_S01_S02_S03_S04_S08'],catalogue_complet=True,
        convention_ticks='UTC',
        debut_horaires_ms=t//JOUR*JOUR-2*JOUR,fin_horaires_ms=t//JOUR*JOUR+8*JOUR,
        compte=dict(entite='COURTIER_FIXTURE',serveur='SERVEUR_FIXTURE',type_compte='STANDARD',devise='USD',levier=100,
            mode_marge='HEDGING',mode_stop_out='PERCENT',empreinte_compte_sha256=sha256((sdk.compte.server+'\0'+str(sdk.compte.login)).encode()).hexdigest(),
            assiette_stop_out=None,historique_complet=True,exclusivites_netting=[]),
        symboles={'EURUSD.micro':dict(canonique='EURUSD',sous_jacent='EURUSD',commission_par_lot_par_cote='0',
            commission_minimum_par_ordre='0',commission_nulle_confirmee=True,devise_frais='USD',
            convention_swap='POINTS_PROUVES_PAR_FIXTURE',protections_a_l_entree=True,convention_declenchement_verifiee=True,
            modes_remplissage=['IOC'],flags_natifs={k:getattr(n,k) for k in ('filling_mode','order_mode','trade_exemode','chart_mode')},
            minuit_egal_fin_24h=False,cout_aller_retour_usd_volume_min='0',longueur_commentaire_max=31,historique_ticks_complet=True)})


def exports(t=T,version=1,*,jours=None,fermetures=None,nom='EURUSD.micro'):
    jours=jours if jours is not None else [dict(jour=j,cotation=[] if j in (0,6) else [dict(debut='00:00:00',fin='24:00:00')],
        negociation=[] if j in (0,6) else [dict(debut='00:00:00',fin='23:00:00')]) for j in range(7)]
    return (dict(schema='xp-export-seances-v1',version=version,export_serveur=natif(t),export_gmt=natif(t),symbole=nom,jours=jours),
        dict(schema='xp-fermetures-v1',version=version,date_releve=iso(t),fermetures=fermetures or []))


def frontiere(root,*,t=T,qualification=None,sdk=None,table=None,etat=None,mode='PAPER'):
    from xpbots.infra.c2a_specifications import SpecificationsMT5
    sdk=sdk or FauxMT5(Path(root).resolve(),instant_ms=t)
    session=SessionMT5(sdk,mode);session.attacher()
    table=table or TableHeureServeur('SERVEUR_FIXTURE',1,iso(t-1000),('MESURE_SYNTHETIQUE_S01',),
        (SegmentServeur(t-14*JOUR,t+30*JOUR,0),))
    q=deepcopy(preuve_qualification(sdk,t) if qualification is None else qualification)
    try:
        specs=SpecificationsMT5(session,configuration().commun,table,q,{'EURUSD':'EURUSD.micro'},
            seances_max_age_ms=7200000,fermetures_max_age_ms=2*JOUR,max_jours_horaires=14,ecart_horloges_max_ms=1000,etat=etat)
    except BaseException:
        session.fermer();raise
    return sdk,session,specs
