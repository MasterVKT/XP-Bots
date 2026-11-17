"""Reglages et fichiers externes synthetiques des jonctions de l'assemblage."""
from pathlib import Path
from robot.outils.qualification_mt5 import T,JOUR,iso,natif,exports,octets,preuve_qualification
from robot.outils.execution_partagee import configuration
from robot.outils.fondamental import message,calendrier
from xpbots.infra.c0a_types import TableHeureServeur,SegmentServeur


def parametres(sdk):
    table=TableHeureServeur('SERVEUR_FIXTURE',1,iso(T-1000),('FIXTURE_S01',),(SegmentServeur(T-14*JOUR,T+30*JOUR,0),))
    options=dict(departs_ticks_utc_ms={'EURUSD':T-1000},depuis_historique_compte_utc_ms=T//JOUR*JOUR,
        seances_max_age_ms=7200000,fermetures_max_age_ms=2*JOUR,max_jours_horaires=14,ecart_horloges_max_ms=1000,
        taille_lot=100,max_ticks_lot=10000,longueur_empreinte=16,max_taches_natives=4)
    return table,preuve_qualification(sdk),options


def installer_controles(common_files,*,t=T,sequence=1,risque='ALLOW'):
    p=configuration().commun;base=Path(common_files)/'XPBots'
    for suffixe in ('fondamental/v1','export/v1'):(base/suffixe).mkdir(parents=True,exist_ok=True)
    m=message(sequence=sequence,risk_state=risque,issued_at_utc=iso(t),known_at_utc=iso(t),valid_from_utc=iso(t),
        valid_until_utc=iso(t+int(p.fundamental_max_validity_seconds*1000)))
    (base/'fondamental/v1/permission_EURUSD.json').write_bytes(octets(m))
    c=calendrier(export_ms=t,export_serveur=natif(t),export_gmt=natif(t),
        fenetre_debut_serveur=natif(t//JOUR*JOUR-JOUR),
        fenetre_fin_serveur=natif(t+int((p.news_forward_coverage_seconds+p.news_calendar_max_age_seconds+60)*1000)))
    (base/'export/v1/calendrier.json').write_bytes(octets(c))
    seances,fermetures=exports(t=t)
    (base/'export/v1/seances_EURUSD.micro.json').write_bytes(octets(seances))
    (base/'export/v1/fermetures_exceptionnelles.json').write_bytes(octets(fermetures))
