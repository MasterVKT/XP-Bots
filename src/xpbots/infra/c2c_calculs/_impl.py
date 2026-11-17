"""CalculCourtier natif : chiffres du SDK et frais C04 qualifiés."""
from decimal import Decimal,Context,localcontext
from math import isfinite
from xpbots.infra.c0a_types import ErreurInfra,champ_natif,entier_natif,nombre_decimal
from xpbots.infra.c1_session import SessionMT5
from xpbots.execution.c0a_types import (EtatCompte,PositionCompte,ControleNatif,OrdreCalcule,decimal_fini)
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import ProfilInstrument,ProfilCompte
from xpbots.noyau.c1c_domaine import Sens

_CENT_POUR_CENT=100


def _nombre(objet,nom):return nombre_decimal(champ_natif(objet,nom))
def _entier(objet,nom):return entier_natif(champ_natif(objet,nom))


def _texte(objet,nom):
    v=champ_natif(objet,nom)
    if type(v) is not str or not v:raise ErreurInfra('champ natif texte absent : '+nom)
    return v


def _flottant(v):
    decimal_fini(v,'valeur native',Decimal(0),True)
    n=float(v)
    if not isfinite(n) or n<=0:raise ErreurInfra('conversion native non positive ou non finie')
    return n


class CalculsMT5:
    def __init__(self,session,commun,liaisons,instant_ms,*,profil,qualification_compte,proprietaire,
                 flux_externe,assiette_stop_out):
        if not isinstance(session,SessionMT5) or not isinstance(commun,ParametresCommuns):raise ErreurInfra('session et parametres reels requis')
        if (type(liaisons) is not dict or not liaisons or len(set(liaisons.values()))!=len(liaisons)
                or any(s not in commun.universe_priority or type(b) is not str or not b for s,b in liaisons.items())):
            raise ErreurInfra('liaisons fixes requises')
        if not all(callable(f) for f in (profil,qualification_compte,proprietaire,flux_externe)):
            raise ErreurInfra('callbacks physiques explicites requis')
        if assiette_stop_out not in (None,'EQUITY','FREE_MARGIN'):raise ErreurInfra('assiette stop-out inconnue')
        verifier_instant(instant_ms)
        self._session,self._commun,self._liaisons=session,commun,dict(liaisons)
        self._profil,self._qualification_compte,self._proprietaire,self._flux_externe=profil,qualification_compte,proprietaire,flux_externe
        self._assiette,self._instant=assiette_stop_out,instant_ms

    def actualiser_instant(self,t):
        verifier_instant(t)
        if t<self._instant:raise ErreurInfra('instant de calcul non causal')
        self._instant=t

    def specifications(self,symbole):
        p=self._profil(symbole,self._instant)
        if (not isinstance(p,ProfilInstrument) or p.symbole!=symbole or self._liaisons.get(symbole)!=p.symbole_courtier
                or p.releve_ms>self._instant):raise ErreurInfra('profil courant indisponible')
        return p

    def _compte(self):
        p=self._qualification_compte(self._instant)
        if not isinstance(p,ProfilCompte) or p.releve_ms>self._instant:raise ErreurInfra('compte qualifie indisponible')
        n=self._session.appeler('account_info')
        if (_texte(n,'currency')!=p.devise or p.devise!=self._commun.account_currency or _entier(n,'leverage')!=p.levier
                or p.levier!=self._commun.account_leverage or _texte(n,'server')!=p.serveur or _texte(n,'company')!=p.entite):
            raise ErreurInfra('compte natif different du profil')
        sdk=self._session.sdk;mode=_entier(n,'margin_so_mode')
        mode_marge=_entier(n,'margin_mode')
        if (p.mode_marge=='HEDGING' and mode_marge!=sdk.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
                or p.mode_marge=='NETTING' and mode_marge not in (sdk.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,sdk.ACCOUNT_MARGIN_MODE_EXCHANGE)
                or p.mode_marge not in ('NETTING','HEDGING')):raise ErreurInfra('mode marge natif different')
        if (p.mode_stop_out=='PERCENT' and mode!=sdk.ACCOUNT_STOPOUT_MODE_PERCENT
                or p.mode_stop_out=='MONEY' and mode!=sdk.ACCOUNT_STOPOUT_MODE_MONEY
                or p.mode_stop_out not in ('PERCENT','MONEY')):raise ErreurInfra('mode stop-out natif different')
        if _nombre(n,'margin_so_so')!=p.niveau_stop_out:raise ErreurInfra('seuil stop-out modifie')
        return p,n

    def _type(self,sens):
        if not isinstance(sens,Sens):raise ErreurInfra('sens reel requis')
        return self._session.sdk.ORDER_TYPE_BUY if sens is Sens.ACHAT else self._session.sdk.ORDER_TYPE_SELL

    def _arguments(self,p,sens,volume):
        if not isinstance(p,ProfilInstrument) or self._liaisons.get(p.symbole)!=p.symbole_courtier:
            raise ErreurInfra('profil non lie')
        return self._type(sens),p.symbole_courtier,_flottant(volume)

    def profit(self,profil,sens,volume,entree,sortie):
        r=self._session.appeler('order_calc_profit',*self._arguments(profil,sens,volume),_flottant(entree),_flottant(sortie))
        return nombre_decimal(r)

    def marge(self,profil,sens,volume,entree):
        r=nombre_decimal(self._session.appeler('order_calc_margin',*self._arguments(profil,sens,volume),_flottant(entree)))
        if r<0:raise ErreurInfra('marge native negative')
        return r

    def _cote(self,profil,sens,volume):
        self._arguments(profil,sens,volume)
        if profil.devise_frais!=self._commun.account_currency:raise ErreurInfra('frais hors devise de compte')
        a,b=profil.commission_par_lot_par_cote,profil.commission_minimum_par_ordre
        decimal_fini(a,'commission',Decimal(0));decimal_fini(b,'minimum',Decimal(0))
        if not profil.commission_nulle_confirmee and a==b==0:raise ErreurInfra('commission nulle non prouvee')
        with localcontext(Context(prec=48)):return max(a*volume,b)

    def frais_aller_retour(self,profil,sens,volume):
        cote=self._cote(profil,sens,volume)
        with localcontext(Context(prec=48)):return cote+cote

    def frais_sortie(self,profil,sens,volume):return self._cote(profil,sens,volume)

    def _positions(self):
        natifs=self._session.appeler('positions_get');resultat=[]
        inverse={b:s for s,b in self._liaisons.items()}
        for n in natifs:
            numero=_entier(n,'ticket');symbole=_texte(n,'symbol');volume=_nombre(n,'volume')
            if numero<=0 or volume<=0:raise ErreurInfra('position native incomplete')
            ticket=str(numero);propriete=self._proprietaire(ticket)
            canonique=inverse.get(symbole,symbole)
            if propriete is None:
                p=PositionCompte(ticket,canonique,canonique,volume,None)
            elif (not isinstance(propriete,PositionCompte) or propriete.identifiant!=ticket or propriete.cle is None
                    or propriete.symbole!=canonique):raise ErreurInfra('propriete native non prouvee')
            else:p=PositionCompte(ticket,propriete.symbole,propriete.sous_jacent,volume,propriete.risque_initial,propriete.cle)
            resultat.append((p,n))
        if len({p.identifiant for p,n in resultat})!=len(resultat):raise ErreurInfra('ticket natif duplique')
        return tuple(resultat)

    def etat_compte(self):
        p,n=self._compte();solde=_nombre(n,'balance');flux=self._flux_externe(self._instant,solde)
        if type(flux) is not bool:raise ErreurInfra('historique de flux incomplet')
        return EtatCompte(self._instant,_nombre(n,'equity'),solde,_nombre(n,'margin'),
            tuple(p for p,n in self._positions()),flux)

    def _stop_out(self,profil,equity,marge,libre):
        if marge<0:raise ErreurInfra('marge native negative')
        with localcontext(Context(prec=48)):
            if profil.mode_stop_out=='PERCENT':return marge==0 or equity*_CENT_POUR_CENT/marge>profil.niveau_stop_out
            if profil.mode_stop_out=='MONEY':
                if self._assiette is None:raise ErreurInfra('assiette MONEY non qualifiee')
                return (equity if self._assiette=='EQUITY' else libre)>profil.niveau_stop_out
        raise ErreurInfra('mode stop-out inconnu')

    def _code(self,n):
        if n==0:return 'CHECK_OK'
        noms=[k for k in dir(self._session.sdk) if k.startswith('TRADE_RETCODE_') and getattr(self._session.sdk,k)==n]
        return noms[0] if len(noms)==1 else 'CHECK_CODE_'+str(n)

    def controler(self,ordre,compte,remplacement=False):
        if not isinstance(ordre,OrdreCalcule) or not isinstance(compte,EtatCompte) or type(remplacement) is not bool:
            raise ErreurInfra('ordre, compte et mode reels requis')
        if compte.instant_ms!=self._instant:raise ErreurInfra('compte de controle non courant')
        pc,natif=self._compte();p=self.specifications(ordre.cle.symbole);sdk=self._session.sdk
        if ordre.symbole_courtier!=p.symbole_courtier:raise ErreurInfra('symbole de controle different')
        if remplacement:
            positions=[(p,n) for p,n in self._positions() if p.cle==ordre.cle]
            if len(positions)!=1:raise ErreurInfra('position de remplacement non prouvee')
            position,n=positions[0]
            if position.volume<ordre.volume or _nombre(n,'sl')!=ordre.stop:raise ErreurInfra('volume ou SL de remplacement incoherent')
            requete=dict(action=sdk.TRADE_ACTION_SLTP,position=int(position.identifiant),sl=_flottant(ordre.stop),tp=_flottant(ordre.objectif))
        else:
            mode=next((m for m in ('FOK','IOC','RETURN') if m in p.modes_remplissage),None)
            if mode is None or mode=='RETURN' and p.mode_execution=='MARKET':raise ErreurInfra('remplissage non qualifie')
            requete=dict(action=sdk.TRADE_ACTION_DEAL,symbol=p.symbole_courtier,volume=_flottant(ordre.volume),
                type=self._type(ordre.cle.sens),price=_flottant(ordre.entree),sl=_flottant(ordre.stop),tp=_flottant(ordre.objectif),
                type_filling=getattr(sdk,'ORDER_FILLING_'+mode),type_time=sdk.ORDER_TIME_GTC)
        r=self._session.appeler('order_check',requete);code=_entier(r,'retcode')
        base=natif if remplacement else r
        marge=_nombre(base,'margin');libre=_nombre(base,'margin_free');equity=_nombre(base,'equity')
        return ControleNatif(code==0,marge,libre,self._stop_out(pc,equity,marge,libre),self._code(code))
