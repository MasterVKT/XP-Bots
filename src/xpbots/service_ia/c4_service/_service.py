"""Processus partagé : aucun lien vers l'exécution ni les stratégies."""
from pathlib import Path
from threading import Event, Lock, Thread
from xpbots.infra.c0d_journal import lire_octets, ecrire_atomique, alerter
from xpbots.infra.c0h_verrou import VerrouProcessus
from xpbots.fondamental.c1b_annonces import GardeAnnonces
from xpbots.service_ia.c0_types import ErreurService, canonique, decoder, empreinte
from xpbots.service_ia.c1f_snapshot import EcrivainSnapshot
from xpbots.service_ia.c2b_routeur import RouteurIA
from xpbots.service_ia.c2c_collecteur import CollecteurRSS
from xpbots.service_ia.c3_planificateur import PlanificateurIA
from ._sqlite import DepotServiceSQLite
from ._physique import HorlogeService, PublieurSnapshot
from ._http import TransportHTTP
from ._calendrier import CalendrierService


def _chemin(v):
    p=Path(v).resolve()
    if p.name.casefold()=='.env' or p.name.casefold().startswith('.env.'):
        raise ErreurService('FICHIER_ENV_INTERDIT')
    return p


class ServiceIA:
    def __init__(self,ressources,chemin_base,chemin_snapshot,*,horloge=None,ouvreur=None,cles=None,
                 profils=(),autoriser_http_reel=False,paiement_autorise=False,calendrier=None,
                 cas_derives=(),routes_auditees=(),agregats=None):
        self.r=ressources;self.horloge=horloge or HorlogeService();self._threads=[]
        self._stop=Event();self._pub_lock=Lock();self._infer_lock=Lock();self._collect_lock=Lock()
        self._alert_lock=Lock()
        self._verrous=[];self.depot=None;self._ferme=False;self._inconnus=()
        base=_chemin(chemin_base);snapshot=_chemin(chemin_snapshot)
        if base==snapshot:raise ErreurService('CHEMINS_SERVICE_CONFONDUS')
        manifeste=snapshot.with_name('service_identity.json')
        self._agregats=None if agregats is None else _chemin(agregats)
        if self._agregats in (base,snapshot,manifeste):raise ErreurService('CHEMINS_SERVICE_CONFONDUS')
        try:
            for p in sorted((base.with_name(base.name+'.service.lock'),snapshot.with_name(snapshot.name+'.lock')),key=str):
                v=VerrouProcessus(p);v.acquerir();self._verrous.append(v)
            if manifeste.exists() and not base.exists():raise ErreurService('BASE_PERSISTANTE_PERDUE')
            if snapshot.exists() and not manifeste.exists():raise ErreurService('MANIFESTE_SERVICE_ABSENT')
            self.depot=DepotServiceSQLite(base,ressources)
            ident=dict(schema='xp-service-identity-v1',database_instance=self.depot.identite['instance_id'],
                database_path=str(base),snapshot_path=str(snapshot),integration_digest=ressources.digest)
            if manifeste.exists():
                if decoder(lire_octets(manifeste,ressources.p['snapshot_max_bytes']))!=ident:
                    raise ErreurService('IDENTITE_SERVICE_INCOMPATIBLE')
            else:ecrire_atomique(manifeste,canonique(ident))
            http=TransportHTTP(ressources,self.horloge,ouvreur=ouvreur,cles=cles,autoriser_http_reel=autoriser_http_reel)
            self.routeur=RouteurIA(ressources,self.depot,http,self.horloge,profils,paiement_autorise=paiement_autorise)
            self.collecteur=CollecteurRSS(ressources,self.depot,http,self.horloge,selectionner=self.depot.selectionner_documents)
            if isinstance(calendrier,dict):
                calendrier=CalendrierService(ressources,self.depot,horloge=self.horloge,**calendrier)
            if calendrier is None:
                garde=GardeAnnonces(ressources.configuration.technique.commun,lambda v:(_ for _ in ()).throw(ValueError('CONVERSION_ABSENTE')))
                calendrier=lambda t:(garde,None,False)
            self.calendrier=calendrier
            self.planificateur=PlanificateurIA(ressources,self.depot,self.routeur,self.collecteur,
                self.horloge,calendrier,cas_derives=cas_derives,routes_auditees=routes_auditees,
                selectionner_jobs=self.depot.selectionner_jobs,selectionner_evenements=self.depot.selectionner_evenements)
            self._writer=EcrivainSnapshot(ressources,self.depot,PublieurSnapshot(ressources,snapshot,self.horloge))
            self._inconnus=self.planificateur.reprendre()
        except BaseException:
            if self.depot is not None:self.depot.fermer()
            for v in reversed(self._verrous):v.liberer()
            self._ferme=True;raise

    def _ouvert(self):
        if self._ferme:raise ErreurService('SERVICE_FERME')

    def collecter(self):
        self._ouvert()
        with self._collect_lock:
            self._importer_agregats()
            actualiser=getattr(self.calendrier,'actualiser',None)
            if callable(actualiser):actualiser()
            return self.planificateur.collecter()

    def _importer_agregats(self):
        if self._agregats is None:return
        try:
            v=decoder(lire_octets(self._agregats,self.r.p['rss_max_download_bytes']))
            if set(v)!={'schema','metriques','decisions'} or v['schema']!='xp-code-aggregates-v1':
                raise ErreurService('AGREGATS_INVALIDES')
            digest=empreinte(v)
            ancien=self.depot.transaction(lambda t:t['schedule_state'].get('agregats_importes'))
            if ancien is not None and ancien['sha256']==digest:return
            self.planificateur.recevoir_metriques(v['metriques'],decisions=v['decisions'])
            # Une interruption avant ce marqueur mène à un réimport amont idempotent.
            self.depot.transaction(lambda t:t['schedule_state'].__setitem__('agregats_importes',dict(sha256=digest)))
        except (OSError,ValueError,TypeError,KeyError):
            self.depot.transaction(lambda t:t['alerts'].setdefault('agregats',
                dict(code='AGREGATS_INDISPONIBLES',instant_ms=self.horloge.maintenant_ms())))

    def _afficher_alertes(self):
        # Aucun texte provenant d'une API, d'un fichier ou d'une exception ne sort ici.
        connus={'NOUVELLE_QUALIFICATION_REQUISE','CORPUS_DERIVE_MANQUANT','MODELE_CHANGE',
            'DERIVE_MATERIELLE','USAGES_INCONNUS_A_RAPPROCHER','RAPPROCHEMENT_CONTRADICTOIRE',
            'CONSOMMATION_HORS_BORNE','WORKER_INDISPONIBLE','AGREGATS_INDISPONIBLES',
            'PUBLICATION_SNAPSHOT_INDISPONIBLE'}
        with self._alert_lock:
            alertes=self.depot.transaction(lambda t:tuple((k,dict(v)) for k,v in t['alerts'].items()))
            for k,v in alertes:
                cle='alerte_affichee:'+empreinte(k)
                digest=empreinte({champ:valeur for champ,valeur in v.items() if champ!='instant_ms'})
                ancien=self.depot.transaction(lambda t:t['schedule_state'].get(cle))
                if ancien is not None and ancien['sha256']==digest:continue
                code=v.get('code');code=code if code in connus else 'SERVICE_IA_ALERTE'
                try:alerter(code,"Service IA : consulter le registre local et le guide d'exploitation.")
                except OSError:continue
                self.depot.transaction(lambda t:t['schedule_state'].__setitem__(cle,dict(sha256=digest)))

    def inferer(self):
        self._ouvert()
        if not self._infer_lock.acquire(blocking=False):raise ErreurService('INFERENCE_DEJA_EN_COURS')
        try:
            if self._inconnus:
                restant=self.depot.transaction(lambda t:tuple(a['job_id'] for a in t['api_attempts'].values()
                    if a['status']=='UNKNOWN' and a['job_id'] in self._inconnus))
                self._inconnus=restant
                if restant:return None
            return self.planificateur.executer_un()
        finally:self._infer_lock.release()

    def heartbeat(self):
        self._ouvert()
        with self._pub_lock:
            now=self.horloge.maintenant_ms()
            publication=self._writer.publier(now,self.planificateur.evenements(now))
            if not publication.publie:
                self.depot.transaction(lambda t:t['alerts'].setdefault('publication_snapshot',
                    dict(code='PUBLICATION_SNAPSHOT_INDISPONIBLE',instant_ms=now)))
            self._afficher_alertes()
            return publication

    def _boucle(self,nom,operation,intervalle):
        while not self._stop.is_set():
            try:operation()
            except Exception:
                try:
                    self.depot.transaction(lambda t:t['alerts'].setdefault('worker:'+nom,
                        dict(code='WORKER_INDISPONIBLE',worker=nom,instant_ms=self.horloge.maintenant_ms())))
                    self._afficher_alertes()
                except Exception:pass
            attendre=getattr(self.horloge,'attendre_arret',None)
            if callable(attendre):attendre(self._stop,intervalle)
            else:self._stop.wait(intervalle)

    def demarrer(self):
        self._ouvert()
        if self._threads:raise ErreurService('SERVICE_DEJA_DEMARRE')
        self._stop.clear()
        travaux=(('collecte',self.collecter,self.r.p['ea_snapshot_poll_seconds']),
                 ('inference',self.inferer,self.r.p['ea_snapshot_poll_seconds']),
                 ('heartbeat',self.heartbeat,self.r.p['snapshot_heartbeat_seconds']))
        for nom,op,intervalle in travaux:
            th=Thread(target=self._boucle,args=(nom,op,intervalle),name='xpbots-ia-'+nom)
            self._threads.append(th);th.start()

    def arreter(self):
        self._stop.set()
        for th in self._threads:th.join(self.r.p['job_deadline_seconds'])
        if any(th.is_alive() for th in self._threads):raise ErreurService('ARRET_SERVICE_EN_ATTENTE')
        self._threads=[]

    def etat(self):
        self._ouvert()
        return self.depot.transaction(lambda t:dict(mode=self.r.p['default_evaluation_mode'],
            en_marche=bool(self._threads),usages_inconnus=len(self._inconnus),
            fournisseurs={p['id']:dict(t['provider_state']['veto:'+p['id']]) for p in self.r.p['providers']}))

    def fermer(self):
        if self._ferme:return
        self.arreter();self.depot.fermer()
        for v in reversed(self._verrous):v.liberer()
        self._ferme=True
    def __enter__(self):return self
    def __exit__(self,*_):self.fermer()
