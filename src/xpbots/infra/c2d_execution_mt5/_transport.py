"""Emission native separee de la boucle ; le worker ne modifie pas le registre."""
from dataclasses import replace
from decimal import Decimal
from datetime import timedelta
from hashlib import sha256
from queue import SimpleQueue,Empty
from threading import Thread,RLock
from xpbots.infra.c0a_types import ErreurInfra,ErreurNative,champ_natif,entier_natif,nombre_decimal
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.noyau.c0c_configuration import ParametresCommuns
from xpbots.noyau.c1b_instrument import ProfilInstrument,ProfilCompte
from xpbots.execution.c4_cycle import (CommandeExecution,NatureCommande,ReponseCourtier,NatureReponse,
    StatutAccuse,PreuvePersistance,identifier_courtier)
from ._valeurs import PreparationNative,ReceptionNative,reel,ticket_natif,classer


def _ms(v):return timedelta(seconds=v)//timedelta(milliseconds=1)


class TransportMT5:
    def _initialiser_transport(self,session,commun,table,liaisons,horloge,profil,preuve,qualification_compte,preuve_compte,
            longueur_empreinte,max_taches_natives,depuis_utc_ms,convention_ticks):
        if not isinstance(session,SessionMT5) or not isinstance(commun,ParametresCommuns) or not isinstance(horloge,HorlogeSysteme):
            raise ErreurInfra('session, configuration et horloge reelles requises')
        if type(convention_ticks) is not str or convention_ticks not in ('UTC','SERVEUR_S01'):
            raise ErreurInfra('convention de ticks qualifiee S01 requise')
        self._convention_ticks=convention_ticks
        if type(liaisons) is not dict or not liaisons or len(set(liaisons.values()))!=len(liaisons):raise ErreurInfra('liaisons uniques requises')
        if any(s not in commun.universe_priority or type(b) is not str or not b for s,b in liaisons.items()):raise ErreurInfra('liaison native invalide')
        if not all(callable(c) for c in (profil,preuve,qualification_compte,preuve_compte)):raise ErreurInfra('callbacks de qualification requis')
        if type(longueur_empreinte) is not int or longueur_empreinte<=0 or type(max_taches_natives) is not int or max_taches_natives<=1:
            raise ErreurInfra('limites natives explicites requises')
        verifier_instant(depuis_utc_ms)
        self._session,self._commun,self._table,self._horloge=session,commun,table,horloge
        self._liaisons=dict(liaisons);self._profil,self._preuve,self._qualification_compte=profil,preuve,qualification_compte
        self._preuve_compte=preuve_compte;self._exclusivites_courantes=set()
        self._longueur,self._maximum,self._depuis=longueur_empreinte,max_taches_natives,depuis_utc_ms
        self._registre={};self._autorisees=set();self._revision=0;self._numero=0;self._dernier=0
        self._verrou=RLock();self._resultats=SimpleQueue();self._taches={};self._ferme=False
        self._proprietaires={};self._derniere_observation=None

    def _temps(self,t):
        verifier_instant(t)
        if t<self._dernier:raise ErreurInfra('horloge native en recul')
        self._dernier=t

    def _entree_connue(self,cle,registre=None):
        with self._verrou:
            source=self._registre if registre is None else registre
            return sorted((r for r in source.values() if r['commande'].cle==cle and r['commande'].nature is NatureCommande.ENTREE),key=lambda r:r['numero'])

    def preparer_entrees(self,commandes,instant_ms):
        self._temps(instant_ms)
        with self._verrou:
            if self._ferme or self._session.mode not in ('DEMO','REEL'):raise ErreurInfra('emission native interdite dans ce mode')
            prepares=dict(self._registre);numero=self._numero;revision=self._revision
            for c in tuple(commandes):
                if not isinstance(c,CommandeExecution):raise ErreurInfra('commande publique requise')
                if c.nature is not NatureCommande.ENTREE:continue
                connue=prepares.get(c.reference)
                if connue is not None:
                    if connue['commande']!=c:raise ErreurInfra('reference native contradictoire')
                    continue
                if c.instant_ms>instant_ms or self._liaisons.get(c.cle.symbole)!=c.donnees['symbole_courtier']:
                    raise ErreurInfra('commande future ou hors liaison')
                precedentes=self._entree_connue(c.cle,prepares)
                if precedentes and precedentes[-1]['statut']!='REFUS_PRIX':raise ErreurInfra('intention deja emise ou inconnue')
                if any(p.cle==c.cle for p in self._proprietaires.values()):raise ErreurInfra('intention deja remplie')
                identite=identifier_courtier(c.cle,self._longueur)
                if (c.donnees['magic'],c.donnees['commentaire'])!=(identite.magic,identite.commentaire):raise ErreurInfra('identite D08 incoherente')
                p=self._profil(c.cle.symbole,instant_ms)
                if not isinstance(p,ProfilInstrument):p=None
                numero+=1
                prepares[c.reference]=dict(numero=numero,commande=c,profil=p,statut='PREPAREE',appel_termine=False,
                    envoi_termine=False,ordre=None,code=None)
                revision+=1
            self._registre,self._numero,self._revision=prepares,numero,revision
            refs=tuple(r for r,v in self._registre.items() if v['commande'].nature is NatureCommande.ENTREE and v['statut']=='PREPAREE')
            return PreparationNative(self._revision,refs)

    def autoriser_entrees(self,preuve):
        if not isinstance(preuve,PreuvePersistance):raise ErreurInfra('preuve native de COMMIT requise')
        with self._verrou:
            if preuve.references and all(r in self._autorisees for r in preuve.references):return
            attendues={r for r,v in self._registre.items() if v['commande'].nature is NatureCommande.ENTREE and v['statut']=='PREPAREE'}
            if preuve.revision!=self._revision or set(preuve.references)!=attendues:raise ErreurInfra('preuve native etrangere ou perimee')
            for ref in preuve.references:
                self._autorisees.add(ref);self._demarrer(ref)

    def soumettre_defenses(self,commandes,instant_ms):
        self._temps(instant_ms)
        commandes=tuple(commandes)
        if any(not isinstance(c,CommandeExecution) for c in commandes):raise ErreurInfra('commande publique requise')
        for c in sorted(commandes,key=lambda c:c.donnees.get('priorite',0)):
            if c.nature not in (NatureCommande.TP,NatureCommande.CLOTURE,NatureCommande.ANNULATION):continue
            with self._verrou:
                connue=self._registre.get(c.reference)
                if connue is not None:
                    if connue['commande']!=c:raise ErreurInfra('reference defensive contradictoire')
                    continue
                if c.instant_ms>instant_ms:raise ErreurInfra('defense future')
                self._numero+=1
                self._registre[c.reference]=dict(numero=self._numero,commande=c,profil=None,statut='PREPAREE',appel_termine=False,
                    envoi_termine=False,ordre=None,code=None)
                self._demarrer(c.reference)

    def _demarrer(self,ref):
        r=self._registre[ref]
        limite=self._maximum-1 if r['commande'].nature is NatureCommande.ENTREE else self._maximum
        if self._ferme or len(self._taches)>=limite:
            r['statut']='INCONNUE'
            self._resultats.put(dict(reference=ref,phase='LOCAL',retour=None,code='LOCAL_CAPACITE_NATIVE',envoi=False))
            return
        r['statut']='EN_COURS'
        t=Thread(target=self._worker,args=(ref,r['commande'],r['profil']),name='XPBots-ordre',daemon=True)
        self._taches[ref]=t
        try:t.start()
        except BaseException:
            self._taches.pop(ref,None)
            self._resultats.put(dict(reference=ref,phase='LOCAL',retour=None,code='LOCAL_TACHE_INDISPONIBLE',envoi=False))

    def _verifier_delai(self,c,t):
        verifier_instant(t)
        if t<c.instant_ms:raise ErreurInfra('horloge native avant commande')
        if c.nature is NatureCommande.ENTREE:
            if t>=c.donnees['expire_ms'] or t-c.instant_ms>_ms(self._commun.quote_max_age_seconds):
                raise ErreurInfra('delai transport expire')

    def _requete_entree(self,c,p,t):
        if not isinstance(p,ProfilInstrument):raise ErreurInfra('profil prepare indisponible')
        self._verifier_compte()
        session=self._session.actualiser()
        if not session.connecte or not session.droits:raise ErreurInfra('droits natifs indisponibles')
        pc=self._qualification_compte(t);courant=self._profil(c.cle.symbole,t);q=self._preuve(c.cle.symbole,t)
        if not isinstance(pc,ProfilCompte) or not isinstance(courant,ProfilInstrument):raise ErreurInfra('qualification courante indisponible')
        if (courant.symbole_courtier,courant.tick_size,courant.point)!=(p.symbole_courtier,p.tick_size,p.point):raise ErreurInfra('specifications natives modifiees')
        if c.donnees['mode_remplissage'] not in courant.modes_remplissage or len(c.donnees['commentaire'])>q['longueur_commentaire_max']:
            raise ErreurInfra('capacite native non qualifiee')
        if c.donnees['risque_initial']>c.donnees['budget_gele']:raise ErreurInfra('risque non autorise')
        sdk=self._session.sdk;d=c.donnees
        return dict(action=sdk.TRADE_ACTION_DEAL,symbol=d['symbole_courtier'],volume=reel(d['volume']),
            type=sdk.ORDER_TYPE_BUY if d['sens'].signe>0 else sdk.ORDER_TYPE_SELL,price=reel(d['prix']),
            sl=reel(d['sl']),tp=reel(d['tp']),deviation=d['deviation_points'],
            type_filling=getattr(sdk,'ORDER_FILLING_'+d['mode_remplissage']),type_time=sdk.ORDER_TIME_GTC,
            magic=d['magic'],comment=d['commentaire'])

    def _position_possedee(self,c):
        ticket=ticket_natif(c.donnees['ticket'])
        with self._verrou:p=self._proprietaires.get(ticket)
        if p is None or p.cle!=c.cle:raise ErreurInfra('position non possedee')
        if self._mode_compte=='NETTING' and c.cle.symbole not in self._exclusivites_courantes:raise ErreurInfra('exclusivite netting non rapprochee')
        ns=self._session.appeler('positions_get',ticket=int(ticket))
        if len(ns)!=1:raise ErreurInfra('position courante non prouvee')
        n=ns[0];identite=identifier_courtier(c.cle,self._longueur)
        if (champ_natif(n,'symbol'),entier_natif(champ_natif(n,'magic')),champ_natif(n,'comment'))!=(self._liaisons[c.cle.symbole],identite.magic,identite.commentaire):
            raise ErreurInfra('identite de position non concordante')
        return p,n

    def _requete_defense(self,c,t):
        self._verifier_compte()
        sdk=self._session.sdk;d=c.donnees
        if c.nature is NatureCommande.ANNULATION:
            ticket=ticket_natif(d['ordre']);ns=self._session.appeler('orders_get',ticket=int(ticket))
            identite=identifier_courtier(c.cle,self._longueur)
            if len(ns)!=1 or (champ_natif(ns[0],'symbol'),entier_natif(champ_natif(ns[0],'magic')),champ_natif(ns[0],'comment'))!=(self._liaisons.get(c.cle.symbole),identite.magic,identite.commentaire):
                raise ErreurInfra('reliquat non possede')
            return dict(action=sdk.TRADE_ACTION_REMOVE,order=int(ticket))
        p,n=self._position_possedee(c)
        if c.nature is NatureCommande.TP:
            if nombre_decimal(champ_natif(n,'sl'))!=d['sl']:raise ErreurInfra('SL fixe natif absent ou different')
            return dict(action=sdk.TRADE_ACTION_SLTP,position=int(p.identifiant),sl=reel(d['sl']),tp=reel(d['tp']))
        volume=nombre_decimal(champ_natif(n,'volume'))
        if d['volume']>volume:raise ErreurInfra('volume de fermeture depasse la position')
        q=self._session.appeler('symbol_info_tick',self._liaisons[c.cle.symbole])
        instant=entier_natif(champ_natif(q,'time_msc'));verifier_instant(instant)
        if self._convention_ticks=='SERVEUR_S01':instant=self._table.utc_de_serveur(instant)
        if not 0<=t-instant<=_ms(self._commun.quote_max_age_seconds):raise ErreurInfra('cotation de defense non fraiche')
        bid,ask=nombre_decimal(champ_natif(q,'bid')),nombre_decimal(champ_natif(q,'ask'))
        if ask<bid or bid<=0:raise ErreurInfra('cotation de defense invalide')
        achete=entier_natif(champ_natif(n,'type'))==sdk.POSITION_TYPE_BUY
        if entier_natif(champ_natif(n,'type')) not in (sdk.POSITION_TYPE_BUY,sdk.POSITION_TYPE_SELL):raise ErreurInfra('sens de position inconnu')
        entrees=self._entree_connue(c.cle);ancienne=entrees[-1] if entrees else None
        courant=self._profil(c.cle.symbole,t)
        if not isinstance(courant,ProfilInstrument):courant=ancienne['profil'] if ancienne else None
        if not isinstance(courant,ProfilInstrument) or ancienne is None:raise ErreurInfra('profil defensif indisponible')
        mode=next((m for m in ('FOK','IOC','RETURN') if m in courant.modes_remplissage),None)
        if mode is None:raise ErreurInfra('remplissage defensif indisponible')
        identite=identifier_courtier(c.cle,self._longueur)
        return dict(action=sdk.TRADE_ACTION_DEAL,position=int(p.identifiant),symbol=self._liaisons[c.cle.symbole],
            type=sdk.ORDER_TYPE_SELL if achete else sdk.ORDER_TYPE_BUY,volume=reel(d['volume']),
            price=reel(bid if achete else ask),deviation=ancienne['commande'].donnees['deviation_points'],
            type_filling=getattr(sdk,'ORDER_FILLING_'+mode),type_time=sdk.ORDER_TIME_GTC,magic=identite.magic,comment=identite.commentaire)

    def _worker(self,ref,c,profil):
        envoi=False;phase='LOCAL';retour=None;code=None
        try:
            t=self._horloge.utc_ms();self._verifier_delai(c,t)
            requete=self._requete_entree(c,profil,t) if c.nature is NatureCommande.ENTREE else self._requete_defense(c,t)
            phase='CHECK';controle=self._session.appeler('order_check',requete)
            if entier_natif(champ_natif(controle,'retcode'))!=0:
                retour=controle
            else:
                self._verifier_delai(c,self._horloge.utc_ms());phase='SEND';envoi=True
                retour=self._session.appeler('order_send',requete)
        except BaseException as e:
            code='RES_'+str(e.code) if isinstance(e,ErreurNative) else 'LOCAL_ENVIRONMENT_NOT_READY'
        self._resultats.put(dict(reference=ref,phase=phase,retour=retour,code=code,envoi=envoi))

    def collecter(self):
        bruts=[]
        while True:
            try:bruts.append(self._resultats.get_nowait())
            except Empty:break
        t=self._horloge.utc_ms();self._temps(t);reponses=[];alertes=[]
        with self._verrou:
            for b in bruts:
                ref=b['reference'];r=self._registre[ref];c=r['commande'];n=b['retour']
                r['appel_termine']=True;self._taches.pop(ref,None)
                if n is None:
                    statut,definitif= (StatutAccuse.INCONNU,False) if b['envoi'] else (StatutAccuse.REFUSE,True)
                    code=b['code'] or 'LOCAL_ENVIRONMENT_NOT_READY';ordre=None
                    r['envoi_termine']=not b['envoi']
                else:
                    try:
                        statut,definitif,code=classer(self._session.sdk,champ_natif(n,'retcode'),precontrole=b['phase']=='CHECK')
                        ordre=None if b['phase']=='CHECK' else ticket_natif(champ_natif(n,'order'),absent=True)
                        r['envoi_termine']=True
                    except (ValueError,TypeError,AttributeError):
                        statut,definitif,code,ordre=StatutAccuse.INCONNU,False,'RESULTAT_NATIF_INCOMPLET',None
                        r['envoi_termine']=False
                r['ordre'],r['code']=ordre,code
                r['statut']='REFUS_PRIX' if statut is StatutAccuse.REFUSE and not definitif else 'REFUS_DEFINITIF' if statut is StatutAccuse.REFUSE else 'ACCEPTEE' if statut is StatutAccuse.ACCEPTE else 'INCONNUE'
                empreinte=sha256((ref+'|'+statut.value+'|'+code+'|'+str(ordre)).encode()).hexdigest()
                reponses.append(ReponseCourtier(NatureReponse.ACCUSE,c.cle,'mt5:ack:'+empreinte,t,
                    dict(commande=ref,statut=statut,code_natif=code,definitif=definitif,ordre=ordre)))
                if statut is StatutAccuse.INCONNU:alertes.append('MT5_ORDRE_INCONNU')
                if b['phase']=='LOCAL' or code.startswith('LOCAL_'):alertes.append('MT5_ENVIRONMENT_NOT_READY')
        return ReceptionNative(t,tuple(reponses),tuple(alertes))

    def fermer(self,attente_ms):
        if type(attente_ms) is not int or attente_ms<0:raise ErreurInfra('attente de fermeture explicite requise')
        self._ferme=True
        fin=self._horloge.monotone_ns()+attente_ms*1_000_000
        for t in tuple(self._taches.values()):
            reste=max(0,fin-self._horloge.monotone_ns())/1_000_000_000
            t.join(reste)
        return not any(t.is_alive() for t in self._taches.values())
