"""Implémentation de la couche 0e (echeances_sortie). Révisable à comportement constant sous harnais complet."""
from dataclasses import dataclass
from datetime import time,timedelta
from xpbots.donnees.c0b_sessions import CalendrierLondres
from xpbots.noyau.c0a_temps import verifier_instant,instant_vers_datetime,instant_depuis_datetime
from xpbots.noyau.c0c_configuration import ExportTechnique
from xpbots.noyau.c1b_instrument import HorairesCotation
from xpbots.noyau.c1c_domaine import CauseCloture,Motif,verifier_motif

@dataclass(frozen=True)
class EcheanceSortie:
    instant_ms: int | None
    causes: tuple[CauseCloture,...] = ()
    motif: Motif | None = None
    detail: str | None = None
    def __post_init__(self):
        object.__setattr__(self,'causes',tuple(self.causes))
        if self.instant_ms is None:
            if self.motif is not Motif.ENVIRONMENT_NOT_READY or self.causes: raise ValueError('échéance inconnue sans motif')
            verifier_motif(self.motif,self.detail)
        else:
            verifier_instant(self.instant_ms)
            if not self.causes or any(not isinstance(c,CauseCloture) for c in self.causes) or self.motif is not None or self.detail is not None:
                raise ValueError('échéance incohérente')

def premiere_echeance(premier_remplissage_ms,strategie,technique,horaires):
    verifier_instant(premier_remplissage_ms)
    if not isinstance(technique,ExportTechnique): raise ValueError('export technique attendu')
    configurations=(technique.london,technique.ema)
    methode=next((p for p in configurations if p['strategy_id']==strategie),None)
    if methode is None: raise ValueError('méthode inconnue')
    if not isinstance(horaires,HorairesCotation): return EcheanceSortie(None,motif=Motif.ENVIRONMENT_NOT_READY,detail='horaires')
    commun=technique.commun; calendrier=CalendrierLondres.depuis_parametres(commun)
    ms=lambda sec:timedelta(seconds=sec)//timedelta(milliseconds=1)
    try:
        if not horaires.ouvert_a(premier_remplissage_ms): return EcheanceSortie(None,motif=Motif.ENVIRONMENT_NOT_READY,detail='horaires')
        fermeture=horaires.prochaine_fermeture_apres(premier_remplissage_ms)
    except ValueError:
        return EcheanceSortie(None,motif=Motif.ENVIRONMENT_NOT_READY,detail='horaires')
    if fermeture is None: return EcheanceSortie(None,motif=Motif.ENVIRONMENT_NOT_READY,detail='fermeture_native')
    local=calendrier.instant_local(calendrier.jour_local(premier_remplissage_ms),time.fromisoformat(methode['force_exit_local']))
    blackout=calendrier.prochain_debut_blackout(premier_remplissage_ms)
    if calendrier.dans_blackout(premier_remplissage_ms):
        moment=instant_vers_datetime(premier_remplissage_ms)
        debut=commun.rollover_blackout_utc_start
        borne=moment.replace(hour=debut.hour,minute=debut.minute,second=debut.second,microsecond=0)
        if borne>moment: borne-=timedelta(days=1)
        blackout=instant_depuis_datetime(borne)
    echeances=((premier_remplissage_ms+ms(commun.max_position_wallclock_seconds),CauseCloture.DUREE_MAXIMALE),
               (local,CauseCloture.HEURE_SORTIE),(fermeture-ms(commun.native_market_close_guard_seconds),CauseCloture.FERMETURE_NATIVE),(blackout,CauseCloture.BLACKOUT))
    premier=min(t for t,c in echeances)
    return EcheanceSortie(premier,tuple(c for t,c in echeances if t==premier))
