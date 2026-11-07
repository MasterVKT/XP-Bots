"""Implémentation de la couche 1c (registre_reservations). Révisable à comportement constant sous harnais complet."""
from dataclasses import replace
from decimal import Context,Decimal,localcontext
from xpbots.execution.c0a_types import EtatCompte,EtatReservations,Reservation,RefusExecution,ErreurExecution,decimal_fini,texte
from xpbots.noyau.c0b_nombres import decimal_depuis
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1c_domaine import CleIntention,Issue,NatureIssue,Motif

class RegistreReservations:
    def __init__(self,commun,etat=None):
        if not isinstance(commun,ParametresCommuns) or etat is not None and not isinstance(etat,EtatReservations): raise ErreurExecution('paramètres et état attendus')
        self._p,self._etat=commun,etat or EtatReservations()
        rs=self._etat.reservations
        if (len(rs)>commun.account_max_positions
                or any(sum(v.cle.symbole==r.cle.symbole for v in rs)>commun.max_positions_per_canonical_symbol for r in rs)
                or any(sum(v.sous_jacent==r.sous_jacent for v in rs)>commun.max_positions_per_canonical_symbol for r in rs)):
            raise ErreurExecution('occupations restaurées incohérentes')
    @property
    def etat(self): return self._etat
    def _positions(self,compte,exclure=None):
        if not isinstance(compte,EtatCompte): raise ErreurExecution('compte attendu')
        return tuple(p for p in compte.positions if p.cle!=exclure or p.cle is None)
    def risque_total(self,compte,exclure=None):
        ps=self._positions(compte,exclure);rs={r.cle:r for r in self._etat.reservations if r.cle!=exclure}
        if any(p.cle is None for p in ps): return RefusExecution(Motif.ACCOUNT_RISK_CAP,'POSITIONS_EXTERNES')
        with localcontext(Context(prec=48)):
            total=Decimal(0)
            for p in ps:
                r=rs.pop(p.cle,None)
                total+=max(p.risque_initial,r.risque_initial if r else Decimal(0))
            return total+sum((r.risque_initial for r in rs.values()),Decimal(0))
    def marge_en_attente(self,compte,exclure=None):
        presentes={p.cle for p in self._positions(compte,exclure)}
        with localcontext(Context(prec=48)):
            return sum((r.marge_initiale for r in self._etat.reservations if r.cle not in presentes and r.cle!=exclure),Decimal(0))
    def verifier_admission(self,cle,sous_jacent,risque,compte,*,remplacement=False):
        if not isinstance(cle,CleIntention) or type(remplacement) is not bool: raise ErreurExecution('clé et remplacement attendus')
        texte(sous_jacent);decimal_fini(risque,'risque',Decimal(0))
        if cle.strategie not in self._p.simultaneous_strategy_priority or cle.symbole not in self._p.universe_priority: raise ErreurExecution('clé non configurée')
        if any(p.cle is None for p in compte.positions): return RefusExecution(Motif.ACCOUNT_RISK_CAP,'POSITIONS_EXTERNES')
        if remplacement:
            r=next((r for r in self._etat.reservations if r.cle==cle),None)
            if r is None or not r.remplie: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'reservation_remplie')
        exclure=cle if remplacement else None
        ps=self._positions(compte,exclure)
        rs=tuple(r for r in self._etat.reservations if r.cle!=exclure)
        if cle.symbole in self._etat.verrous or sous_jacent in self._etat.verrous:
            return RefusExecution(Motif.SYMBOL_BUSY,'ETAT_ORDRE_INCONNU')
        presentes={p.cle for p in ps}
        occupations=sum(p.symbole==cle.symbole or p.sous_jacent==sous_jacent for p in ps)+sum((r.cle.symbole==cle.symbole or r.sous_jacent==sous_jacent) and r.cle not in presentes for r in rs)
        if occupations>=self._p.max_positions_per_canonical_symbol:
            return RefusExecution(Motif.SYMBOL_BUSY,'POSITION_AUTRE_METHODE')
        presentes={p.cle for p in ps}
        if len(ps)+sum(r.cle not in presentes for r in rs)+1>self._p.account_max_positions:
            return RefusExecution(Motif.ACCOUNT_RISK_CAP,'NOMBRE_POSITIONS')
        total=self.risque_total(compte,exclure)
        if isinstance(total,RefusExecution): return total
        with localcontext(Context(prec=48)):
            if total+risque>decimal_depuis(self._p.account_max_initial_reserved_risk_fraction)*compte.fonds_propres:
                return RefusExecution(Motif.ACCOUNT_RISK_CAP,'RESERVE_TOTALE')
        return None
    def reserver(self,reservation,compte,version_attendue):
        if not isinstance(reservation,Reservation): raise ErreurExecution('réservation attendue')
        existante=next((r for r in self._etat.reservations if r.cle==reservation.cle),None)
        if existante is not None:
            if replace(existante,remplie=False)!=replace(reservation,remplie=False): raise ErreurExecution('clé répétée avec montants différents')
            return self._etat
        if reservation.cle in self._etat.terminees: return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'cle_terminee')
        if type(version_attendue) is not int or version_attendue!=self._etat.version:
            return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'version_reservations')
        if reservation.remplie: raise ErreurExecution('une nouvelle réserve précède le premier fill')
        refus=self.verifier_admission(reservation.cle,reservation.sous_jacent,reservation.risque_initial,compte)
        if refus is not None: return refus
        self._etat=replace(self._etat,version=self._etat.version+1,reservations=self._etat.reservations+(reservation,))
        return self._etat
    def sur_issue(self,issue):
        if not isinstance(issue,Issue): raise ErreurExecution('issue attendue')
        r=next((r for r in self._etat.reservations if r.cle==issue.cle),None)
        if r is None:
            if issue.cle in self._etat.terminees: return self._etat
            raise ErreurExecution('réservation absente')
        if issue.nature is NatureIssue.REMPLIE:
            if r.remplie: return self._etat
            rs=tuple(replace(v,remplie=True) if v.cle==r.cle else v for v in self._etat.reservations)
            self._etat=replace(self._etat,version=self._etat.version+1,reservations=rs)
        else:
            if r.remplie and issue.nature is not NatureIssue.CLOTUREE: raise ErreurExecution('réserve remplie libérable seulement à clôture')
            self._etat=replace(self._etat,version=self._etat.version+1,reservations=tuple(v for v in self._etat.reservations if v.cle!=r.cle),terminees=self._etat.terminees+(r.cle,))
        return self._etat
    def verrouiller(self,sous_jacent):
        texte(sous_jacent)
        if sous_jacent not in self._etat.verrous:
            self._etat=replace(self._etat,version=self._etat.version+1,verrous=self._etat.verrous+(sous_jacent,))
        return self._etat
