"""Composition causale des couches réelles, sans I/O physique ni moteur de trading."""
import calendar
from dataclasses import asdict
from datetime import timedelta, time
from zoneinfo import ZoneInfo
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, DocumentIA, JobIA,
    canonique, decoder, empreinte, instant, texte, iso, utc)
from xpbots.service_ia.c1b_validation import valider_extraction
from xpbots.service_ia.c1d_budget import RegistreBudget
from xpbots.service_ia.c2a_veto import apparier_calendrier, construire_veto
from xpbots.service_ia.c2b_routeur import RouteurIA
from xpbots.service_ia.c2c_collecteur import CollecteurRSS
from xpbots.noyau.c0a_temps import instant_vers_datetime
from ._model import (CasDerive, PRIORITES, MATERIEL, ms, slot, jour_suivant,
    copie, valider_metrique, valider_decision)


class PlanificateurIA:
    def __init__(self,ressources,depot,routeur,collecteur,horloge,calendrier,
                 *,cas_derives=(),routes_auditees=(),selectionner_evenements=None,selectionner_jobs=None):
        if not isinstance(ressources,RessourcesIA) or not isinstance(routeur,RouteurIA) or not isinstance(collecteur,CollecteurRSS):
            raise ErreurService('COMPOSANTS_REELS_REQUIS')
        if not all(callable(x) for x in (getattr(depot,'transaction',None),
                getattr(horloge,'maintenant_ms',None),calendrier)):
            raise ErreurService('PORTS_PLANIFICATEUR_REQUIS')
        for f in (selectionner_evenements,selectionner_jobs):
            if f is not None and not callable(f):raise ErreurService('SELECTEUR_INVALIDE')
        self.r=ressources;self.depot=depot;self.routeur=routeur;self.collecteur=collecteur
        self.horloge=horloge;self.calendrier=calendrier;self._dernier=None
        self.budget=RegistreBudget(ressources,depot)
        self.zone=ZoneInfo(ressources.configuration.technique.commun.session_timezone)
        self._selection_evenements=selectionner_evenements;self._selection_jobs=selectionner_jobs
        self.cas=tuple(cas_derives);self.routes=tuple(routes_auditees)
        if len(self.cas) not in (0,ressources.p['weekly_golden_cases']):raise ErreurService('CORPUS_DERIVE_INCOMPLET')
        if any(not isinstance(c,CasDerive) for c in self.cas) or len({c.case_id for c in self.cas})!=len(self.cas):
            raise ErreurService('CORPUS_DERIVE_INVALIDE')
        for pid in self.routes:texte(pid);ressources.fournisseur(pid)
        if len(set(self.routes))!=len(self.routes):raise ErreurService('ROUTE_AUDIT_DUPLIQUEE')
        for c in self.cas:
            d=decoder(c.dossier)
            valider_extraction(ressources,c.attendu.decode('utf-8'),d)
            if set(d)!={'item_id','title','issuer','provided_text'} or d['issuer'] not in {f['issuer'] for f in ressources.p['feeds']}:
                raise ErreurService('DOSSIER_DERIVE_INVALIDE')
        now=self._maintenant()
        self._initialiser_qualifications(now)

    def _maintenant(self):
        now=instant(self.horloge.maintenant_ms())
        if self._dernier is not None and now<self._dernier:raise ErreurService('HORLOGE_EN_RECUL')
        self._dernier=now;return now

    def _signature(self,pid):
        return empreinte(dict(provider=dict(self.r.fournisseur(pid)),prompt=self.r.prompt('EXTRACTION'),
            schema=self.r.schema('EXTRACTION')))

    def _initialiser_qualifications(self,now):
        def operation(t):
            for f in self.r.p['providers']:
                pid=f['id'];signature=self._signature(pid);cle='veto:'+pid
                s=t['provider_state'].get(cle)
                if s is None:
                    t['provider_state'][cle]=dict(provider=pid,signature=signature,
                        qualification='NON_QUALIFIE',suspended=False,last_model=None)
                elif s['signature']!=signature:
                    s.update(suspended=True,qualification='NON_QUALIFIE',new_signature=signature)
                    t['alerts']['qualification:'+pid]=dict(code='NOUVELLE_QUALIFICATION_REQUISE',provider=pid,instant_ms=now)
            for c in self.cas:
                t['golden_cases'].setdefault('case:'+c.signature,
                    dict(case_id=c.case_id,signature=c.signature,dossier=decoder(c.dossier),attendu=decoder(c.attendu)))
            if not self.cas:
                t['alerts']['corpus_derives']=dict(code='CORPUS_DERIVE_MANQUANT',instant_ms=now)
        self.depot.transaction(operation)

    def collecter(self):
        collectes=[]
        for f in self.r.p['feeds']:
            collecte=self.collecteur.collecter(f['issuer']);collectes.append(collecte)
            now=self._maintenant()
            for d in collecte.nouveaux:
                if (d.couverture!='COMPLETE' or d.publie_ms is None or not d.officiel
                        or not d.publie_ms<=d.premiere_vue_ms<=d.collecte_ms<=now):continue
                fin=d.publie_ms+ms(self.r.p['unscheduled_policy_veto_seconds_from_publication'])
                if now>=fin:continue
                ident=empreinte(dict(kind='EXTRACTION',item_id=d.item_id))
                job=JobIA(ident,'EXTRACTION',d.item_id,now,fin,canonique(dict(
                    item_id=d.item_id,title=d.titre,issuer=d.issuer,provided_text=d.texte)))
                self.routeur.enregistrer(job)
        return tuple(collectes)

    def _dossier_note(self,kind,now):
        local=instant_vers_datetime(now).astimezone(self.zone)
        if kind=='BRIEFING':debut=now-ms(self.r.p['brief_news_lookback_seconds'])
        elif kind=='JOURNAL':debut=slot(local.date(),time().isoformat(),self.zone)
        else:debut=slot((local-timedelta(weeks=1)).date(),local.timetz().replace(tzinfo=None).isoformat(),self.zone)
        docs=self.collecteur.documents(debut_ms=debut,fin_ms=now+1,known_at_ms=now)
        def archives(t):
            metriques=[copie(v) for v in t['experiment_metrics'].values()
                if debut<=v['known_at_ms']<=now]
            coverage={f['issuer']:t['feed_state'].get(f['issuer'],{}).get('coverage','PARTIAL') for f in self.r.p['feeds']}
            return metriques,coverage
        metriques,couverture=self.depot.transaction(archives)
        documents=[dict(item_id=d.item_id,title=d.titre,issuer=d.issuer,url=d.url,
            published_at_utc=iso(d.publie_ms),first_seen_utc=iso(d.premiere_vue_ms),
            content_known_at_utc=iso(d.collecte_ms),coverage=d.couverture,provided_text=d.texte) for d in docs]
        preuves=tuple(d['item_id'] for d in documents)+tuple(m['item_id'] for m in metriques)
        return canonique(dict(kind=kind,known_at_utc=iso(now),documents=documents,
            metrics=metriques,coverage=couverture)),preuves

    def planifier(self):
        now=self._maintenant();local=instant_vers_datetime(now).astimezone(self.zone)
        def avancer(t):
            s=t['schedule_state'].setdefault('planification',dict(last_ms=now-1))
            avant=s['last_ms']
            if avant>now:raise ErreurService('PLANIFICATION_EN_RECUL')
            s['last_ms']=now;return avant
        avant=self.depot.transaction(avancer);nouveaux=[]
        if local.weekday() in self.r.configuration.technique.commun.active_weekdays_local:
            horaires=[('BRIEFING',self.r.p['pre_session_brief_local']),('JOURNAL',self.r.p['daily_journal_local'])]
            for kind,heure in horaires:
                date_slot=slot(local.date(),heure,self.zone)
                if avant<date_slot<=now<date_slot+ms(self.r.p['job_deadline_seconds']):
                    dossier,preuves=self._dossier_note(kind,now)
                    ident=empreinte(dict(kind=kind,slot=date_slot))
                    j=JobIA(ident,kind,None,date_slot,date_slot+ms(self.r.p['job_deadline_seconds']),dossier,preuves)
                    if self.routeur.enregistrer(j):nouveaux.append(ident)
            jour,heure=self.r.p['weekly_review_local'].split(' ',1)
            date_slot=slot(local.date(),heure,self.zone)
            if local.weekday()==getattr(calendar,jour.upper()) and avant<date_slot<=now<date_slot+ms(self.r.p['job_deadline_seconds']):
                fin=slot(local.date()+timedelta(weeks=1),heure,self.zone)
                self._creer_audits(date_slot,fin,now)
        nouveaux.extend(self._enfiler_logiques(now))
        return tuple(nouveaux)

    def _creer_audits(self,debut,fin,now):
        dossier,preuves=self._dossier_note('WEEKLY_REVIEW',now)
        def operation(t):
            cle='task:'+empreinte(dict(kind='WEEKLY_REVIEW',slot=debut))
            t['schedule_state'].setdefault(cle,dict(kind='WEEKLY_REVIEW',provider=None,case_id=None,
                dossier=decoder(dossier),evidence_ids=list(preuves),week=debut,ready_ms=now,
                utile_jusqua_ms=fin,status='READY',job_id=None))
            for pid in self.routes:
                for c in self.cas:
                    cle='task:'+empreinte(dict(kind='GOLDEN',slot=debut,provider=pid,case=c.signature))
                    t['schedule_state'].setdefault(cle,dict(kind='GOLDEN',provider=pid,case_id=c.case_id,
                        dossier=decoder(c.dossier),evidence_ids=[],week=debut,ready_ms=now,
                        utile_jusqua_ms=fin,status='READY',job_id=None,expected=decoder(c.attendu)))
        self.depot.transaction(operation)

    def _enfiler_logiques(self,now):
        def choisir(t):
            return tuple((k,copie(v)) for k,v in t['schedule_state'].items() if k.startswith('task:'))
        toutes=self.depot.transaction(choisir)
        occupees={v['provider'] for _,v in toutes if v['status']=='QUEUED'}
        nouveaux=[]
        for cle,v in sorted(toutes,key=lambda kv:(PRIORITES[kv[1]['kind']],kv[0])):
            if v['status']!='READY' or v['ready_ms']>now:continue
            if now>=v['utile_jusqua_ms']:
                self.depot.transaction(lambda t:t['schedule_state'][cle].update(status='EXPIRED'));continue
            if v['provider'] in occupees:continue
            if v['kind']=='WEEKLY_REVIEW' and any(a['kind']=='GOLDEN' and a['week']==v['week']
                    and a['status'] not in ('DONE','FAILED','EXPIRED') for _,a in toutes):continue
            if v['provider'] is not None:
                etat=self.budget.etat_route(v['provider'])
                minimum=etat['not_before_ms']
                if etat['last_sent_ms'] is not None:
                    minimum=max(minimum,etat['last_sent_ms']+ms(self.r.p['provider_min_request_spacing_seconds']))
                if now<minimum:continue
            ident=empreinte(dict(task=cle,day=iso(now).split('T')[0]))
            j=JobIA(ident,v['kind'],v['dossier'].get('item_id'),now,
                min(v['utile_jusqua_ms'],now+ms(self.r.p['job_deadline_seconds'])),
                canonique(v['dossier']),tuple(v['evidence_ids']),v['provider'])
            if self.routeur.enregistrer(j):nouveaux.append(ident)
            self.depot.transaction(lambda t:t['schedule_state'][cle].update(status='QUEUED',job_id=ident))
            occupees.add(v['provider'])
        return nouveaux

    def executer_un(self):
        self.planifier();now=self._maintenant()
        jobs=tuple(self._selection_jobs() if self._selection_jobs else self.routeur.en_attente())
        if any(not isinstance(j,JobIA) for j in jobs):raise ErreurService('SELECTION_JOBS_INVALIDE')
        jobs=tuple(j for j in jobs if j.cree_ms<=now)
        if not jobs:return None
        j=min(jobs,key=lambda j:(PRIORITES[j.kind],j.cree_ms,j.job_id))
        resultat=self.routeur.annuler(j.job_id,'JOB_EXPIRE') if now>=j.utile_jusqua_ms else self.routeur.executer(j)
        self._traiter(j,resultat)
        return resultat

    def _surveiller_modele(self,j,resultat):
        if resultat.fournisseur is None:return False
        pid=resultat.fournisseur
        def operation(t):
            modele=next((a.get('model_received') for a in t['llm_results'].values()
                if a['job_id']==j.job_id and a['provider']==pid),None)
            s=t['provider_state']['veto:'+pid]
            if modele is not None:
                if s['last_model'] is not None and s['last_model']!=modele:
                    s.update(suspended=True,qualification='NON_QUALIFIE',model_changed_to=modele)
                    t['alerts']['modele:'+pid]=dict(code='MODELE_CHANGE',provider=pid,instant_ms=resultat.recu_ms)
                elif s['last_model'] is None:s['last_model']=modele
            return s['suspended']
        return self.depot.transaction(operation)

    def _traiter(self,j,resultat):
        cle='processed:'+j.job_id
        if self.depot.transaction(lambda t:cle in t['schedule_state']):return
        suspendu=self._surveiller_modele(j,resultat)
        v=decoder(resultat.valide) if resultat.valide is not None else None
        evenement=None;preuve=None;document=None;erreur_calendrier=None
        if j.kind=='EXTRACTION' and v is not None and not suspendu:
            ligne=self.depot.transaction(lambda t:t['source_items'].get(j.item_id))
            if ligne is not None:
                try:
                    document=DocumentIA(**ligne['document'])
                    garde,table,disponible=self.calendrier(resultat.recu_ms)
                    app=apparier_calendrier(self.r,garde,table,document,resultat.recu_ms,source_valide=disponible)
                    preuve=asdict(app)
                    evenement=construire_veto(self.r,resultat.valide.decode('utf-8'),document,
                        decoder(j.dossier)['provided_text'],resultat.recu_ms,resultat.fournisseur,app)
                    if not app.valide:erreur_calendrier='CALENDRIER_NON_ADMISSIBLE'
                except (OSError,ValueError,TypeError,KeyError):erreur_calendrier='PREUVE_CALENDRIER_INDISPONIBLE'
            else:erreur_calendrier='SOURCE_ARCHIVEE_ABSENTE'
        def operation(t):
            if cle in t['schedule_state']:return
            if evenement is not None:
                ident=evenement['event_id'];ancien=t['policy_events'].get(ident)
                if ancien is not None and ancien['event']!=evenement:raise ErreurService('EVENEMENT_REECRIT')
                if ancien is None:
                    t['policy_events'][ident]=dict(event_id=ident,item_id=j.item_id,
                        valid_from=evenement['valid_from_utc'],valid_until=evenement['valid_until_utc'],
                        provider_id=resultat.fournisseur,reason=evenement['reason_code'],
                        event=copie(evenement),document=asdict(document),calendar=copie(preuve),
                        validated_at=resultat.recu_ms)
            if v is not None and j.kind in ('BRIEFING','JOURNAL','WEEKLY_REVIEW'):
                self._archiver_note(t,j,resultat,v)
            if j.kind=='GOLDEN' and resultat.erreur not in ('AUCUNE_ROUTE_ADMISSIBLE','JOB_EXPIRE'):
                self._archiver_derive(t,j,resultat,v)
            if erreur_calendrier:
                t['alerts']['calendrier:'+j.job_id]=dict(code=erreur_calendrier,instant_ms=resultat.recu_ms)
            for k,task in t['schedule_state'].items():
                if not k.startswith('task:') or task['job_id']!=j.job_id:continue
                if resultat.erreur in ('AUCUNE_ROUTE_ADMISSIBLE','JOB_EXPIRE'):
                    task.update(status='READY',ready_ms=jour_suivant(resultat.recu_ms),job_id=None)
                else:task.update(status='DONE' if v is not None else 'FAILED')
            t['schedule_state'][cle]=dict(job_id=j.job_id,kind=j.kind,received_at=resultat.recu_ms,
                error=resultat.erreur,event_id=evenement['event_id'] if evenement else None,
                calendar=copie(preuve) if preuve is not None else None,calendar_error=erreur_calendrier,
                document=asdict(document) if document is not None else None)
        self.depot.transaction(operation)

    def _archiver_note(self,t,j,resultat,v):
        publie=copie(v);retenues=[];omises=0
        mois=iso(resultat.recu_ms).split('T')[0].rsplit('-',1)[0]
        nombre=sum(a['created_month']==mois for a in t['research_hypotheses'].values())
        for h in v['hypotheses']:
            ident=empreinte(h)
            if ident not in t['research_hypotheses']:
                if nombre>=self.r.p['new_research_hypotheses_max_per_month']:omises+=1;continue
                t['research_hypotheses'][ident]=dict(schema='xp-research-ticket-v1',version=1,
                    ticket_id=ident,created_at=resultat.recu_ms,created_month=mois,source_job=j.job_id,
                    statement=h['statement'],validation_plan=h['validation_plan'],status='PROPOSED')
                nombre+=1
            retenues.append(copie(h))
        publie['hypotheses']=retenues
        t['advisories'][j.job_id]=dict(job_id=j.job_id,kind=j.kind,provider=resultat.fournisseur,
            received_at=resultat.recu_ms,raw_validated=copie(v),published=publie,hypotheses_omitted=omises)

    def _archiver_derive(self,t,j,resultat,v):
        task=next((a for k,a in t['schedule_state'].items() if k.startswith('task:') and a['job_id']==j.job_id),None)
        if task is None:raise ErreurService('TACHE_DERIVE_MANQUANTE')
        pid=task['provider'];audit='audit:'+empreinte(dict(week=task['week'],provider=pid))
        a=t['golden_cases'].setdefault(audit,dict(provider=pid,week=task['week'],results={},
            changed=0,complete=False,status='INCOMPLETE'))
        if task['case_id'] in a['results']:return
        change=v is not None and any(v[k]!=task['expected'][k] for k in MATERIEL)
        a['results'][task['case_id']]=dict(job_id=j.job_id,valid=v is not None,changed=change,
            received_at=resultat.recu_ms)
        a['changed']+=int(change)
        a['complete']=(len(a['results'])==self.r.p['weekly_golden_cases']
            and all(x['valid'] for x in a['results'].values()))
        a['status']='COMPLETE' if a['complete'] else 'INCOMPLETE'
        if a['changed']>self.r.p['golden_drift_suspend_if_changed_cases_greater_than']:
            t['provider_state']['veto:'+pid].update(suspended=True,qualification='NON_QUALIFIE')
            t['alerts']['derive:'+pid]=dict(code='DERIVE_MATERIELLE',provider=pid,
                changed=a['changed'],instant_ms=resultat.recu_ms)

    def recevoir_metriques(self,metriques,*,decisions=()):
        now=self._maintenant()
        if not isinstance(metriques,(list,tuple)) or not isinstance(decisions,(list,tuple)):
            raise ErreurService('AGREGATS_EXPLICITES_REQUIS')
        valeurs=tuple(valider_metrique(self.r,v,now,self.zone) for v in metriques)
        candidats=tuple(valider_decision(self.r,v,now) for v in decisions)
        def operation(t):
            compte=dict(metrics_created=0,decisions_created=0)
            for v in valeurs:
                ident=v['item_id'];ancien=t['experiment_metrics'].get(ident)
                if ancien is not None and ancien!=v:raise ErreurService('METRIQUE_REECRITE')
                if ancien is None:t['experiment_metrics'][ident]=copie(v);compte['metrics_created']+=1
            for v in candidats:
                ident=empreinte(v)
                if ident not in t['candidate_decisions']:
                    t['candidate_decisions'][ident]=copie(v);compte['decisions_created']+=1
            return compte
        return self.depot.transaction(operation)

    def evenements(self,instant_ms):
        instant(instant_ms)
        if self._selection_evenements is not None:events=tuple(self._selection_evenements(instant_ms))
        else:events=self.depot.transaction(lambda t:tuple(copie(v['event']) for v in t['policy_events'].values()))
        suspendus=self.depot.transaction(lambda t:{v['provider'] for k,v in t['provider_state'].items()
            if k.startswith('veto:') and v['suspended']})
        return tuple(copie(e) for e in sorted(events,key=lambda e:e['event_id'])
            if e['provider_id'] not in suspendus and utc(e['valid_from_utc'])<=instant_ms<utc(e['valid_until_utc']))

    def reprendre(self):
        now=self._maintenant();inconnus=self.routeur.reprendre()
        def operation(t):
            t['schedule_state']['planification']=dict(last_ms=now-1)
            for k,a in t['schedule_state'].items():
                if not k.startswith('task:') or a['status'] in ('DONE','FAILED','EXPIRED'):continue
                a.update(status='READY' if now<a['utile_jusqua_ms'] else 'EXPIRED',
                    ready_ms=jour_suivant(now),job_id=None)
            # Un résultat sans preuve de calendrier antérieure reste une observation.
            for ident,a in t['llm_jobs'].items():
                cle='processed:'+ident
                if a['result'] is not None and cle not in t['schedule_state']:
                    t['schedule_state'][cle]=dict(job_id=ident,received_at=a['result']['recu_ms'],
                        event_id=None,recovered_without_new_veto=True)
            if inconnus:t['alerts']['rapprochement_reprise']=dict(code='USAGES_INCONNUS_A_RAPPROCHER',
                job_ids=list(inconnus),instant_ms=now)
        self.depot.transaction(operation)
        return inconnus
