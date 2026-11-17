"""Réceptions C05/A10 valides nombreuses : aucun backend ni historique réel."""
from robot.outils.orchestration import C,ticks_courts
from robot.outils.pilote_orchestration import duo
from robot.outils.fondamental import ConversionServeurScenario,message,calendrier,octets,heure_native,table_importance
from robot.outils.contexte_ia import snapshot,evenement,octets as octets_ia
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.orchestration.c0_contrats import EntreeMoteur,ReceptionExterne
from xpbots.noyau.c0a_temps import instant_vers_iso


def composition_controles():
    fond=PermissionsFondamentales(C.technique.commun,ConversionServeurScenario(0))
    return duo(ticks_courts(),fondamental=fond)


def controles_repetes(nombre=300):
    m,ports,ia,h,c=composition_controles();debut=ticks_courts()[0].instant_reception_ms;sorties=[]
    horizon=int((C.technique.commun.news_forward_coverage_seconds+C.technique.commun.news_calendar_max_age_seconds+60)*1000)
    for n in range(nombre):
        t=debut+n*1000
        for p in ports.values():p.avancer_au(t)
        permission=message(sequence=n+1,issued_at_utc=instant_vers_iso(t),known_at_utc=instant_vers_iso(t),
            valid_from_utc=instant_vers_iso(t),valid_until_utc=instant_vers_iso(t+int(C.technique.commun.fundamental_max_validity_seconds*1000)))
        cal=calendrier(version=n+1,export_ms=t,export_serveur=heure_native(t,0),export_gmt=heure_native(t,0),
            fenetre_debut_serveur=heure_native(debut-86400000,0),fenetre_fin_serveur=heure_native(t+horizon,0))
        ev=evenement(debut=t,fin=t+1000,event_id='evenement_'+str(n))
        snap=snapshot(sequence=n+1,genere=t,evenements=[ev])
        sorties.append(m.traiter(EntreeMoteur(t,n+1,receptions=(
            ReceptionExterne('PERMISSION',octets(permission),'EURUSD'),
            ReceptionExterne('CALENDRIER',octets(cal),table=table_importance()),
            ReceptionExterne('SNAPSHOT',octets_ia(snap))))))
    return m,ports,tuple(sorties)
