"""Composition publique de la couture réelle ; données et port papier synthétiques explicites."""
from dataclasses import replace
from decimal import Decimal as D
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_journees_london import journee_london_prechargee
from robot.outils.fabrique_ticks import ticks_de_bougies,TickFabrique
from xpbots.app.rejeu_squelette import composer_rejeu_papier
from xpbots.orchestration.squelette import fabriquer_moteur_minimal,composer_coordinateur_neutre
from xpbots.rejeu.squelette import ContratPapier,rejouer


def composer(ticks,strategie=None,configuration=None,horaires=None,periodes=None):
    configuration=configuration or configuration_figee()
    symboles={t.symbole for t in ticks}
    tailles={s:D('.00001') for s in symboles}
    contrats={s:ContratPapier(D('1000'),D('.1'),D('1'),D('.1')) for s in symboles}
    m,e,s=composer_rejeu_papier(configuration,ticks,tailles,contrats,strategie=strategie,
        scenario='TECHNICAL_CONTROL_NEUTRAL')
    if horaires is not None or periodes is not None:
        from xpbots.rejeu.squelette import hypotheses_marche_squelette
        h,p=hypotheses_marche_squelette(ticks,configuration)
        m=fabriquer_moteur_minimal(strategie,configuration,'REJEU',horaires=h if horaires is None else horaires,
            periodes_couvertes=p if periodes is None else periodes,
            coordinateur=composer_coordinateur_neutre(configuration,'squelette',e.profils,e,e.instant_ms,
                observation=e.observation(),base_utc=e.base_utc()),profils=e.profils,
            profil_compte=e.profil_compte,scenario_fondamental='TECHNICAL_CONTROL_NEUTRAL')
    return m,e,s


def enregistrements(ticks,strategie=None,configuration=None,horaires=None,periodes=None):
    m,e,s=composer(ticks,strategie,configuration,horaires,periodes)
    return [x.vers_dict() for x in rejouer(ticks,m,e,s).enregistrements]


def journee_executable(jour,technique,symbole='EURUSD'):
    """Vraie journée préchargée ; seule l'ouverture après cassure évite un gap artificiel."""
    bougies,_=journee_london_prechargee(jour,technique,symbole=symbole,base=D('1.1'),tr_m15=D('.0008'),tr_h1=D('.0008'))
    for i in range(1,len(bougies)):
        precedente=bougies[i-1]
        if D(precedente.cloture)>D('1.1008') and precedente.cloture!=precedente.ouverture:
            bougies[i]=replace(bougies[i],ouverture=precedente.cloture,
                haut=str(max(D(bougies[i].haut),D(precedente.cloture))))
    ticks=ticks_de_bougies(symbole,bougies)
    ticks.append(TickFabrique(symbole,symbole,bougies[-1].debut_ms+900000,ticks[-1].sequence+1,
        bougies[-1].cloture,str(D(bougies[-1].cloture)+D('.0001'))))
    return bougies,ticks
