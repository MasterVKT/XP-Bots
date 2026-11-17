"""Normalisation des faits natifs ; les decisions restent dans le vrai C08."""
from dataclasses import replace
from decimal import Context,Decimal,localcontext
from hashlib import sha256
from xpbots.infra.c0a_types import ErreurInfra,champ_natif,entier_natif,nombre_decimal
from xpbots.execution.c0a_types import EtatCompte,PositionCompte,RefusExecution
from xpbots.execution.c1b_gardes import MouvementCompte,reconstituer_base_utc
from xpbots.execution.c4_cycle import NatureCommande,NatureReponse,ReponseCourtier,PreuveAbsence,identifier_courtier
from xpbots.execution.c5b_reprise import ObservationNative,PositionNative,OrdreNatif
from xpbots.noyau.c1b_instrument import Intervalle,ProfilCompte
from xpbots.noyau.c1c_domaine import CauseCloture
from xpbots.noyau.c0a_temps import instant_vers_datetime,instant_depuis_datetime,verifier_instant
from ._valeurs import ticket_natif,RapportObservationMT5


def _texte(n,nom):
    v=champ_natif(n,nom)
    if type(v) is not str:raise ErreurInfra('texte natif absent')
    return v


def _positif(n,nom):
    v=nombre_decimal(champ_natif(n,nom))
    if v<=0:raise ErreurInfra('valeur native positive requise')
    return v


def _protection(n,nom):
    v=nombre_decimal(champ_natif(n,nom))
    if v<0:raise ErreurInfra('protection native negative')
    return v if v else None


def _uniques(lignes,cle):
    d={}
    for v in lignes:
        k=v[cle]
        if k in d:raise ErreurInfra('ticket natif duplique')
        d[k]=v
    return d


class ObservationMT5:
    def _instant_natif(self,n,nom,t):
        ms=self._table.utc_de_serveur(entier_natif(champ_natif(n,nom)))
        if ms>t:raise ErreurInfra('fait natif futur')
        return ms

    def _position(self,n,t):
        typ=entier_natif(champ_natif(n,'type'));sdk=self._session.sdk
        if typ not in (sdk.POSITION_TYPE_BUY,sdk.POSITION_TYPE_SELL):raise ErreurInfra('type position inconnu')
        return dict(ticket=ticket_natif(champ_natif(n,'ticket')),identifiant=ticket_natif(champ_natif(n,'identifier')),
            symbole=_texte(n,'symbol'),volume=_positif(n,'volume'),magic=entier_natif(champ_natif(n,'magic')),
            commentaire=_texte(n,'comment'),instant_ms=self._instant_natif(n,'time_msc',t),
            signe=1 if typ==sdk.POSITION_TYPE_BUY else -1,sl=_protection(n,'sl'),tp=_protection(n,'tp'))

    def _ordre(self,n,t,*,historique=False):
        d=dict(ticket=ticket_natif(champ_natif(n,'ticket')),position=ticket_natif(champ_natif(n,'position_id'),absent=True),
            symbole=_texte(n,'symbol'),magic=entier_natif(champ_natif(n,'magic')),commentaire=_texte(n,'comment'),
            instant_ms=self._instant_natif(n,'time_setup_msc',t),etat=entier_natif(champ_natif(n,'state')),
            volume=nombre_decimal(champ_natif(n,'volume_current')))
        sdk=self._session.sdk
        if historique and d['etat'] in (sdk.ORDER_STATE_FILLED,sdk.ORDER_STATE_CANCELED,sdk.ORDER_STATE_REJECTED,sdk.ORDER_STATE_EXPIRED):
            d['fin_ms']=self._instant_natif(n,'time_done_msc',t)
            if d['fin_ms']<d['instant_ms']:raise ErreurInfra('ordre historique termine avant creation')
        return d

    def _deal(self,n,t):
        d=dict(ticket=ticket_natif(champ_natif(n,'ticket')),ordre=ticket_natif(champ_natif(n,'order'),absent=True),
            position=ticket_natif(champ_natif(n,'position_id'),absent=True),symbole=_texte(n,'symbol'),
            magic=entier_natif(champ_natif(n,'magic')),commentaire=_texte(n,'comment'),
            instant_ms=self._instant_natif(n,'time_msc',t),type=entier_natif(champ_natif(n,'type')),
            entree=entier_natif(champ_natif(n,'entry')),cause=entier_natif(champ_natif(n,'reason')))
        for k in ('volume','price','commission','swap','profit','fee'):d[k]=nombre_decimal(champ_natif(n,k))
        return d

    def _correspond(self,n,c):
        identite=identifier_courtier(c.cle,self._longueur)
        return (n['symbole'],n['magic'],n['commentaire'])==(self._liaisons[c.cle.symbole],identite.magic,identite.commentaire)

    def _fait(self,nature,c,t,donnees,faits):
        # Decimal/enum ont des representations canoniques stables, aucun objet SDK.
        contenu=(nature.value,c.cle.texte(),tuple((k,str(v)) for k,v in sorted(donnees.items())))
        ref='mt5:fait:'+sha256(repr(contenu).encode('utf-8')).hexdigest()
        r=faits.get(ref)
        if r is None:
            r=ReponseCourtier(nature,c.cle,ref,t,donnees);faits[ref]=r
        return r

    def _cause_sortie(self,d,c,registre):
        sdk=self._session.sdk
        if d['cause']==sdk.DEAL_REASON_SL:return CauseCloture.STOP_LOSS
        if d['cause']==sdk.DEAL_REASON_TP:return CauseCloture.TAKE_PROFIT
        connues=[r for r in registre.values() if r['commande'].nature is NatureCommande.CLOTURE
            and r['commande'].cle==c.cle and r['commande'].instant_ms<=d['instant_ms']
            and (r['ordre']==d['ordre'] or r['ordre'] is None and r['statut'] in ('EN_COURS','INCONNUE','ACCEPTEE'))]
        if len(connues)!=1:raise ErreurInfra('cause de sortie non attribuable')
        return connues[0]['commande'].donnees['cause']

    def observer(self,*,depuis_flux_ms=None):
        if depuis_flux_ms is not None:verifier_instant(depuis_flux_ms)
        try:
            return self._observer(depuis_flux_ms)
        except (ValueError,TypeError,AttributeError,KeyError,OverflowError):
            t=self._horloge.utc_ms();self._temps(t)
            self._exclusivites_courantes=set();self._flux_non_neutralise=True
            return RapportObservationMT5(t,alertes=('MT5_OBSERVATION_INCOMPLETE',))

    def _observer(self,depuis_flux_ms):
        self._verifier_compte()
        avant=self._horloge.utc_ms();self._temps(avant)
        if self._depuis>avant or depuis_flux_ms is not None and depuis_flux_ms>avant:raise ErreurInfra('depart historique futur')
        a=instant_vers_datetime(self._table.serveur_de_utc(self._depuis))
        b=instant_vers_datetime(self._table.serveur_de_utc(avant))
        compte_avant=self._session.appeler('account_info')
        positions=self._session.appeler('positions_get');ordres=self._session.appeler('orders_get')
        historiques=self._session.appeler('history_orders_get',a,b)
        deals=self._session.appeler('history_deals_get',a,b)
        compte_natif=self._session.appeler('account_info')
        self._verifier_compte(compte_avant);self._verifier_compte(compte_natif)
        # Chaque reception est connue seulement apres la derniere lecture.
        t=self._horloge.utc_ms();self._temps(t);self._verifier_compte()
        if any(nombre_decimal(champ_natif(compte_avant,k))!=nombre_decimal(champ_natif(compte_natif,k)) for k in ('balance','margin')):
            raise ErreurInfra('compte modifie pendant lecture historique')
        pc=self._qualification_compte(t);preuve=self._preuve_compte(t)
        if not isinstance(pc,ProfilCompte) or type(preuve) is not dict:raise ErreurInfra('qualification compte absente')
        complet=preuve.get('historique_complet') is True
        ps=_uniques((self._position(n,t) for n in positions),'ticket')
        os=_uniques((self._ordre(n,t) for n in ordres),'ticket')
        hs=_uniques((self._ordre(n,t,historique=True) for n in historiques),'ticket')
        ds=_uniques((self._deal(n,t) for n in deals),'ticket')
        self._transactions_lues=dict(ds)
        ps_apres=self._session.appeler('positions_get');os_apres=self._session.appeler('orders_get')
        t=self._horloge.utc_ms();self._temps(t)
        if (ps!=_uniques((self._position(n,t) for n in ps_apres),'ticket')
                or os!=_uniques((self._ordre(n,t) for n in os_apres),'ticket')):
            raise ErreurInfra('positions ou ordres modifies pendant observation')
        if any(d['instant_ms']<self._depuis for d in ds.values()):raise ErreurInfra('transaction hors couverture demandee')
        with self._verrou:registre={k:dict(v) for k,v in self._registre.items()};faits=dict(self._faits)
        par_cle={}
        for r in sorted(registre.values(),key=lambda r:r['numero']):
            if r['commande'].nature is NatureCommande.ENTREE:par_cle[r['commande'].cle]=r
        entrees=list(par_cle.values())
        sdk=self._session.sdk;par_id=_uniques(ps.values(),'identifiant');tickets=dict(self._tickets_positions)
        if any(p['identifiant'] in tickets and tickets[p['identifiant']]!=p['ticket'] for p in ps.values()):
            raise ErreurInfra('ticket de position modifie : rapprochement operateur requis')
        tickets.update((p['identifiant'],p['ticket']) for p in ps.values())
        propres={};reponses=[];exclusivites=set(preuve.get('exclusivites_netting',())) if complet else set();absences=[];mouvements=[]
        commerce=(sdk.DEAL_TYPE_BUY,sdk.DEAL_TYPE_SELL)
        with localcontext(Context(prec=48)):
            for d in sorted(ds.values(),key=lambda d:(d['instant_ms'],int(d['ticket']))):
                typ=d['type']
                if typ not in (*commerce,sdk.DEAL_TYPE_BALANCE):raise ErreurInfra('mouvement monetaire non qualifie')
                variation=sum((d[k] for k in ('profit','commission','swap','fee')),Decimal(0))
                mouvements.append(MouvementCompte('mt5:deal:'+d['ticket'],d['instant_ms'],variation,typ==sdk.DEAL_TYPE_BALANCE))
                if typ in commerce and (d['position'] is None or d['volume']<=0 or d['price']<=0
                        or d['entree'] not in (sdk.DEAL_ENTRY_IN,sdk.DEAL_ENTRY_OUT,sdk.DEAL_ENTRY_OUT_BY)):
                    raise ErreurInfra('transaction de marche non qualifiee')
            if self._solde_rapproche is not None:
                # Comparer les differences de faits, y compris une commission corrigee.
                avant_mouv={m.reference:m for m in self._mouvements}
                apres_mouv={m.reference:m for m in mouvements}
                if not set(avant_mouv)<=set(apres_mouv):raise ErreurInfra('historique monetaire a recule')
                for ref,m in avant_mouv.items():
                    apres=apres_mouv[ref]
                    if (m.instant_ms,m.flux_externe)!=(apres.instant_ms,apres.flux_externe):raise ErreurInfra('mouvement monetaire contradictoire')
                    if m.flux_externe and apres!=m:raise ErreurInfra('correction de capital exige decision explicite')
                delta=sum((m.variation_solde-avant_mouv.get(ref,MouvementCompte(ref,m.instant_ms,Decimal(0))).variation_solde
                    for ref,m in apres_mouv.items()),Decimal(0))
                if nombre_decimal(champ_natif(compte_natif,'balance'))!=self._solde_rapproche+delta:
                    raise ErreurInfra('solde natif non explique par historique')
            for r in entrees:
                c=r['commande'];tous=[d for d in ds.values() if d['type'] in commerce and self._correspond(d,c)]
                ins=sorted((d for d in tous if d['entree']==sdk.DEAL_ENTRY_IN),key=lambda d:(d['instant_ms'],int(d['ticket'])))
                # Une meme intention ne peut posseder plusieurs positions natives.
                ids={d['position'] for d in ins}
                if len(ids)>1:raise ErreurInfra('intention avec plusieurs positions natives')
                if not ids:
                    trace=any(self._correspond(n,c) for n in (*ps.values(),*os.values(),*hs.values())) or bool(tous)
                    if complet and r['envoi_termine'] and not trace and self._depuis<=c.instant_ms:
                        absences.append(PreuveAbsence(c.cle,t,self._depuis,t,True,True,True,True,True,True))
                    continue
                identifiant=next(iter(ids));p=par_id.get(identifiant);ticket=tickets.get(identifiant,identifiant)
                contributeurs=[d for d in ds.values() if d['position']==identifiant and d['type'] in commerce]
                exclusif=all(d['entree']!=sdk.DEAL_ENTRY_IN or self._correspond(d,c) for d in contributeurs)
                if self._mode_compte=='NETTING':
                    exclusif=exclusif and complet and c.cle.symbole in preuve.get('exclusivites_netting',())
                    if exclusif:exclusivites.add(c.cle.symbole)
                if p is not None and (not exclusif or not self._correspond(p,c)):
                    continue
                cum=Decimal(0);prix=Decimal(0);frais=Decimal(0)
                volume_position=p['volume'] if p else Decimal(0)
                if volume_position>sum((d['volume'] for d in ins),Decimal(0)):
                    raise ErreurInfra('volume position non explique par entrees identifiees')
                for d in ins:
                    cum+=d['volume'];prix+=d['volume']*d['price'];frais+=max(Decimal(0),-d['commission']-d['fee'])
                    if cum>c.donnees['volume']:raise ErreurInfra('volume natif depasse intention')
                    hist=hs.get(d['ordre']);courant=os.get(d['ordre'])
                    if cum==c.donnees['volume'] and courant is not None and courant['volume']>0:
                        raise ErreurInfra('execution integrale avec reliquat natif contradictoire')
                    terminal=hist is not None and hist['etat'] in (sdk.ORDER_STATE_FILLED,sdk.ORDER_STATE_CANCELED,sdk.ORDER_STATE_REJECTED,sdk.ORDER_STATE_EXPIRED)
                    annule=cum==c.donnees['volume'] or complet and courant is None and terminal
                    reliquat=Decimal(0) if annule else max(Decimal(0),c.donnees['volume']-cum)
                    data=dict(transaction=d['ticket'],ticket=ticket,ordre=d['ordre'],volume_cumule=cum,
                        volume_position=min(cum,volume_position),prix_moyen=prix/cum,execution_ms=ins[0]['instant_ms'],
                        frais_entree=frais,sl=p['sl'] if p else None,tp=p['tp'] if p else None,
                        reliquat=reliquat,reliquat_annule=bool(annule))
                    reponses.append(self._fait(NatureReponse.REMPLISSAGE,c,t,data,faits))
                if p is not None:
                    profil=r['profil']
                    if profil is None:raise ErreurInfra('profil de propriete absent')
                    propres[ticket]=PositionCompte(ticket,c.cle.symbole,profil.sous_jacent,p['volume'],c.donnees['risque_initial'],c.cle)
                    reponses.append(self._fait(NatureReponse.PROTECTIONS,c,t,dict(ticket=ticket,sl=p['sl'],tp=p['tp']),faits))
                sorties=sorted((d for d in contributeurs if d['entree'] in (sdk.DEAL_ENTRY_OUT,sdk.DEAL_ENTRY_OUT_BY)),key=lambda d:(d['instant_ms'],int(d['ticket'])))
                ferme=Decimal(0)
                for d in sorties:
                    if not self._correspond(d,c) and d['cause'] not in (sdk.DEAL_REASON_SL,sdk.DEAL_REASON_TP):raise ErreurInfra('sortie etrangere non qualifiee')
                    ferme+=d['volume']
                    if ferme>cum:raise ErreurInfra('clotures depassent entrees')
                    data=dict(ticket=ticket,volume_restant=cum-ferme,prix=d['price'],execution_ms=d['instant_ms'],
                        frais_sortie=max(Decimal(0),-d['commission']-d['fee']),cause=self._cause_sortie(d,c,registre))
                    reponses.append(self._fait(NatureReponse.CLOTURE,c,t,data,faits))
                for defense in registre.values():
                    ac=defense['commande']
                    if ac.cle==c.cle and ac.nature is NatureCommande.ANNULATION:
                        h=hs.get(ac.donnees['ordre'])
                        if complet and ac.donnees['ordre'] not in os and h is not None and h['etat'] in (sdk.ORDER_STATE_CANCELED,sdk.ORDER_STATE_EXPIRED):
                            reponses.append(self._fait(NatureReponse.ANNULATION,c,t,dict(ordre=ac.donnees['ordre'],confirmee=True),faits))
        # Reconstruire les volumes a minuit depuis les mouvements signes de tout le compte.
        moment=instant_vers_datetime(t);minuit=instant_depuis_datetime(moment.replace(hour=0,minute=0,second=0,microsecond=0))
        volumes={p['identifiant']:p['volume']*p['signe'] for p in ps.values()}
        with localcontext(Context(prec=48)):
            for d in ds.values():
                if d['type'] in commerce and d['instant_ms']>=minuit:
                    volumes[d['position']]=volumes.get(d['position'],Decimal(0))-d['volume']*(1 if d['type']==sdk.DEAL_TYPE_BUY else -1)
        aucune_minuit=complet and self._depuis<=minuit and all(v==0 for v in volumes.values())
        brut=EtatCompte(t,nombre_decimal(champ_natif(compte_natif,'equity')),nombre_decimal(champ_natif(compte_natif,'balance')),
            nombre_decimal(champ_natif(compte_natif,'margin')),flux_externe_non_neutralise=not complet)
        base=reconstituer_base_utc(brut,mouvements,Intervalle(self._depuis,t+1),aucune_position_minuit=aucune_minuit,depuis_flux_ms=depuis_flux_ms)
        if isinstance(base,RefusExecution):brut=replace(brut,flux_externe_non_neutralise=True)
        inverse={b:s for s,b in self._liaisons.items()}
        for p in ps.values():
            if p['ticket'] not in propres:exclusivites.discard(inverse.get(p['symbole']))
        for o in os.values():
            if not any(self._correspond(o,r['commande']) for r in entrees):exclusivites.discard(inverse.get(o['symbole']))
        natifs=tuple(PositionNative(p['ticket'],p['symbole'],p['volume'],p['magic'],p['commentaire'],
            p['ticket'] in propres and (self._mode_compte!='NETTING' or propres[p['ticket']].symbole in exclusivites),sl=p['sl'],tp=p['tp']) for p in ps.values())
        ordres_publics=[]
        for o in os.values():
            if o['volume']<=0:raise ErreurInfra('volume ordre courant invalide')
            sortie=any(r['commande'].nature is NatureCommande.CLOTURE and r['ordre']==o['ticket'] for r in registre.values())
            ordres_publics.append(OrdreNatif(o['ticket'],o['symbole'],o['volume'],o['magic'],o['commentaire'],NatureCommande.CLOTURE if sortie else NatureCommande.ENTREE))
        observation=ObservationNative(brut,self._depuis,complet,natifs,tuple(ordres_publics),tuple(dict((r.reference,r) for r in reponses).values()),
            tuple(dict((p.cle,p) for p in absences).values()),tuple(sorted(exclusivites)))
        with self._verrou:
            self._proprietaires=propres;self._exclusivites_courantes=exclusivites;self._faits=faits
            self._tickets_positions=tickets;self._transactions=ds;self._mouvements=tuple(mouvements)
            self._solde_rapproche=brut.solde;self._flux_non_neutralise=brut.flux_externe_non_neutralise;self._dernier_rapport_ms=t
        return RapportObservationMT5(t,observation,base,('MT5_BASE_UTC_INDISPONIBLE',) if isinstance(base,RefusExecution) else ())
