"""Routage A08–A09 ; seuls les ports injectés peuvent produire un effet externe."""
from dataclasses import replace
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, JobIA, ResultatIA,
    ReponseHTTP, canonique, decoder, empreinte, instant, texte, utc)
from xpbots.service_ia.c1a_tokens import preparer_requete
from xpbots.service_ia.c1b_validation import valider_extraction, valider_note
from xpbots.service_ia.c1d_budget import RegistreBudget, ProfilRoute
from xpbots.service_ia.c1e_fournisseurs import construire_requete, decoder_reponse, extraire_usage


def _ms(s):return timedelta(seconds=s)//timedelta(milliseconds=1)


def _job(j):
    return dict(job_id=j.job_id,kind=j.kind,item_id=j.item_id,cree_ms=j.cree_ms,
        utile_jusqua_ms=j.utile_jusqua_ms,dossier=decoder(j.dossier),
        evidence_ids=list(j.evidence_ids),fournisseur=j.fournisseur)


def _charger(v):
    return JobIA(v['job_id'],v['kind'],v['item_id'],v['cree_ms'],v['utile_jusqua_ms'],
        canonique(v['dossier']),tuple(v['evidence_ids']),v['fournisseur'])


def _resultat(v):
    return ResultatIA(v['job_id'],v['fournisseur'],v['recu_ms'],
        canonique(v['valide']) if v['valide'] is not None else None,v['erreur'])


def _retry_after(v,t):
    if not v:return 0
    v=v.strip()
    if v.isascii() and v.isdigit():
        # Un délai dépassant le calendrier représentable reste bloquant.
        # La comparaison textuelle évite aussi int() sur des milliers de chiffres.
        maximum=utc('9999-12-31T23:59:59.999Z')-t
        secondes=str(maximum//_ms(1));chiffres=v.lstrip('0') or '0'
        if len(chiffres)>len(secondes) or len(chiffres)==len(secondes) and chiffres>secondes:
            return maximum
        return int(chiffres)*_ms(1)
    try:
        dt=parsedate_to_datetime(v)
        if dt.tzinfo is None:return 0
        return max(0,utc(dt.astimezone(timezone.utc).isoformat())-t)
    except (ValueError,TypeError,OverflowError):return 0


def _preuves(job,dossier):
    ids=set()
    for cle in ('documents','metrics'):
        for d in dossier.get(cle,[]):
            if type(d) is dict and type(d.get('item_id')) is str:ids.add(d['item_id'])
    return tuple(i for i in job.evidence_ids if i in ids)


class RouteurIA:
    def __init__(self,ressources,depot,http,horloge,profils=(),*,paiement_autorise=False):
        if not isinstance(ressources,RessourcesIA):raise ErreurService('RESSOURCES_CHARGEES_REQUISES')
        if not callable(http) or not callable(getattr(depot,'transaction',None)):
            raise ErreurService('PORTS_ROUTEUR_REQUIS')
        if not all(callable(getattr(horloge,k,None)) for k in ('maintenant_ms','attendre')):
            raise ErreurService('HORLOGE_REQUISE')
        if type(paiement_autorise) is not bool:raise ErreurService('PAIEMENT_BOOLEEN_REQUIS')
        self.r=ressources;self.depot=depot;self.http=http;self.horloge=horloge
        self.budget=RegistreBudget(ressources,depot);self.paiement=paiement_autorise
        self.profils={};self._occupe=False;self._dernier=None
        for p in profils:
            if not isinstance(p,ProfilRoute):raise ErreurService('PROFIL_ROUTE_REQUIS')
            ressources.fournisseur(p.fournisseur)
            if p.fournisseur in self.profils:raise ErreurService('PROFIL_DUPLIQUE')
            self.profils[p.fournisseur]=p

    def _maintenant(self):
        t=instant(self.horloge.maintenant_ms())
        if self._dernier is not None and t<self._dernier:raise ErreurService('HORLOGE_EN_RECUL')
        self._dernier=t;return t

    def enregistrer(self,job):
        if not isinstance(job,JobIA):raise ErreurService('JOB_REEL_REQUIS')
        v=_job(job);signature=empreinte(v)
        def operation(t):
            a=t['llm_jobs'].get(job.job_id)
            if a is not None:
                if a.get('signature')!=signature:raise ErreurService('ID_JOB_REUTILISE')
                return False
            t['llm_jobs'][job.job_id]=dict(job=v,signature=signature,status='QUEUED',
                created_at=job.cree_ms,configuration_digest=self.r.digest,result=None)
            return True
        return self.depot.transaction(operation)

    def en_attente(self):
        return self.depot.transaction(lambda t:tuple(sorted(
            (_charger(a['job']) for a in t['llm_jobs'].values() if a['status']=='QUEUED'),
            key=lambda j:(j.cree_ms,j.job_id))))

    def _terminer(self,j,pid,recu,valide=None,erreur=None):
        v=dict(job_id=j.job_id,fournisseur=pid,recu_ms=recu,
               valide=valide,erreur=erreur)
        resultat=_resultat(v)
        def operation(t):
            a=t['llm_jobs'][j.job_id]
            a.update(status='DONE' if valide is not None else 'FAILED',result=v)
        self.depot.transaction(operation);return resultat

    def annuler(self,job_id,raison):
        texte(job_id);texte(raison);now=self._maintenant()
        a=self.depot.transaction(lambda t:t['llm_jobs'].get(job_id))
        if a is None:raise ErreurService('JOB_INCONNU')
        if a['result'] is not None:return _resultat(a['result'])
        if a['status']=='RUNNING':raise ErreurService('JOB_EN_COURS')
        return self._terminer(_charger(a['job']),None,now,erreur=raison)

    def reprendre(self):
        if self._occupe:raise ErreurService('WORKER_OCCUPE')
        now=self._maintenant()
        def operation(t):
            inconnus={a['job_id'] for a in t['api_attempts'].values() if a['status']=='UNKNOWN'}
            for ident,a in t['llm_jobs'].items():
                if a['status'] not in ('QUEUED','RUNNING'):continue
                raison='RESULTAT_INCONNU' if a['status']=='RUNNING' else 'REDEMARRAGE_SANS_RATTRAPAGE'
                if a['status']=='RUNNING':inconnus.add(ident)
                a.update(status='FAILED',result=dict(job_id=ident,fournisseur=None,
                    recu_ms=now,valide=None,erreur=raison))
            return tuple(sorted(inconnus))
        return self.depot.transaction(operation)

    def executer(self,job):
        if self._occupe:raise ErreurService('WORKER_OCCUPE')
        self._occupe=True
        try:return self._executer(job)
        finally:self._occupe=False

    def _executer(self,job):
        self.enregistrer(job);debut=self._maintenant()
        def prendre(t):
            a=t['llm_jobs'][job.job_id]
            if a['configuration_digest']!=self.r.digest:raise ErreurService('CONFIGURATION_JOB_MODIFIEE')
            if a['result'] is not None:return a['result']
            if a['status']=='RUNNING':
                return dict(job_id=job.job_id,fournisseur=None,recu_ms=debut,valide=None,erreur='RESULTAT_INCONNU')
            a.update(status='RUNNING',started_at=debut);return None
        precedent=self.depot.transaction(prendre)
        if precedent is not None:
            return self._terminer(job,precedent['fournisseur'],precedent['recu_ms'],
                precedent['valide'],precedent['erreur'])
        limite=min(job.utile_jusqua_ms,debut+_ms(self.r.p['job_deadline_seconds']))
        if debut<job.cree_ms:return self._terminer(job,None,debut,erreur='JOB_FUTUR')
        if debut>=limite:return self._terminer(job,None,debut,erreur='JOB_EXPIRE')
        tentatives=0;pauses=0;erreur='AUCUNE_ROUTE_ADMISSIBLE';dernier_pid=None
        for f in self.r.p['providers']:
            pid=f['id'];p=self.profils.get(pid)
            if p is None or job.fournisseur not in (None,pid):continue
            if tentatives>=self.r.p['max_provider_attempts_per_job']:break
            now=self._maintenant()
            if now>=limite:break
            b=preparer_requete(self.r,job.dossier,
                lambda d:construire_requete(self.r,job,pid,d),
                reduire_documents=job.kind not in ('EXTRACTION','GOLDEN'))
            if b is None:erreur='DOSSIER_TROP_LONG';continue
            # Les pauses ne précèdent que les candidats possédant un profil ;
            # l'admission atomique recontrôle ensuite espacement et quotas.
            if tentatives>pauses:
                pause=self.r.p['provider_fallback_delays_seconds'][tentatives-1]
                if now+_ms(pause)>=limite:break
                self.horloge.attendre(pause);now=self._maintenant()
                if now>=limite:break
                pauses=tentatives
            decision=self.budget.reserver(job,p,b.tokens_entree,now,paiement_autorise=self.paiement)
            if not decision.acceptee:continue
            tentatives+=1;dernier_pid=pid
            q=replace(b.requete,timeout_s=min(b.requete.timeout_s,(limite-now)/_ms(1)))
            ident=decision.reservation.tentative_id;dossier=decoder(b.dossier)
            self._avant_http(job,ident,pid,now,q,b.dossier)
            sortie,erreur,recu=self._appel(job,ident,pid,now,limite,q,dossier)
            if sortie is not None:return self._terminer(job,pid,recu,valide=sortie)
        return self._terminer(job,dernier_pid,self._maintenant(),erreur=erreur)

    def _avant_http(self,job,ident,pid,now,q,dossier):
        r=self.r
        def operation(t):
            t['llm_results'][ident]=dict(job_id=job.job_id,attempt_id=ident,provider=pid,
                model_id=r.fournisseur(pid)['model'],prompt_hash=empreinte(r.prompt(job.kind)),
                schema_hash=empreinte(r.schema(job.kind)),sent_at=now,received_at=None,
                validated_at=None,request=decoder(q.corps),dossier=decoder(dossier),
                raw_response=None,validated_json=None,usage=None,error='RESULTAT_INCONNU')
        self.depot.transaction(operation)

    def _appel(self,job,ident,pid,envoye,limite,q,dossier):
        reponse=None;usage=None;valide=None;erreur=None;modele=None
        try:
            reponse=self.http(q)
            if not isinstance(reponse,ReponseHTTP):raise ErreurService('REPONSE_HTTP_REQUISE')
            recu=self._maintenant()
            if not envoye<=reponse.recu_ms<=recu:raise ErreurService('REPONSE_NON_CAUSALE')
            if reponse.statut in (401,403,429):
                self.budget.signaler_echec(pid,recu,reponse.statut,_retry_after(reponse.entete('Retry-After'),recu))
                if reponse.statut in (401,403):
                    self.depot.transaction(lambda t:t['alerts'].__setitem__('auth:'+pid,
                        dict(code='HTTP_AUTH_REFUSEE',provider=pid,instant_ms=recu)))
            if len(reponse.corps)>q.max_octets:raise ErreurService('REPONSE_TROP_LONGUE')
            try:usage=extraire_usage(self.r,pid,reponse)
            except ValueError:pass
            if usage is not None:modele=usage.modele_recu
            rapproche=self.budget.rapprocher(ident,usage.tokens_entree if usage else None,
                usage.tokens_sortie if usage else None,usage.usage if usage else None,recu)
            if rapproche['status'] in ('BOUND_EXCEEDED','CONTRADICTORY'):
                raise ErreurService('CONSOMMATION_HORS_BORNE')
            retour=decoder_reponse(self.r,pid,reponse)
            if recu-envoye>_ms(q.timeout_s) or recu>=limite:raise ErreurService('REPONSE_TARDIVE')
            if job.kind in ('EXTRACTION','GOLDEN'):
                valide=valider_extraction(self.r,retour.texte,dossier)
            else:valide=valider_note(self.r,retour.texte,job.kind,_preuves(job,dossier))
            recu=self._maintenant()
            if recu>=limite:valide=None;erreur='VALIDATION_TARDIVE'
        except (OSError,TimeoutError):valide=None;erreur='TRANSPORT_INCONNU'
        except (ValueError,TypeError,KeyError,IndexError):valide=None;erreur='REPONSE_INUTILISABLE'
        recu=self._maintenant()
        def archiver(t):
            a=t['llm_results'][ident]
            a.update(received_at=reponse.recu_ms if isinstance(reponse,ReponseHTTP) else None,
                validated_at=recu,raw_response=reponse.corps.hex() if isinstance(reponse,ReponseHTTP) and len(reponse.corps)<=q.max_octets else None,
                http_status=reponse.statut if isinstance(reponse,ReponseHTTP) else None,
                usage=usage.usage if usage is not None else None,model_received=modele,
                validated_json=valide,error=erreur)
        self.depot.transaction(archiver)
        return valide,erreur,recu
