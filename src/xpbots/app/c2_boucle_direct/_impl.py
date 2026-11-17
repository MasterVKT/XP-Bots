"""Cycle physique London ; décisions et calculs délégués aux blocs réels gelés."""
from collections.abc import Mapping
from ._autorisations import verifier_autorisations
from decimal import Decimal
import json

from xpbots.app.c0_configuration import ConfigurationApplication,ErreurApplication,analyser_registre
from xpbots.app.c1a_livre_papier import LivrePapier,TYPES_PAPIER
from xpbots.app.c1b_session_durable import SessionDurable
from xpbots.app.c1f_composition_moteur import PortCompte,composer_moteur,rejouer_incident
from xpbots.execution.c4_cycle import NatureCommande,PreuvePersistance
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0d_journal import alerter
from xpbots.infra.c4_assemblage import InfrastructurePhysique
from xpbots.fondamental.c0_types import TableImportance
from xpbots.noyau.c0a_temps import instant_vers_iso,verifier_instant
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument
from xpbots.orchestration.c0_contrats import EntreeMoteur,ReceptionExterne,MiseAJourBras
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission


def _encoder(v):return serialiser_valeur(v,types_supplementaires=TYPES_PAPIER)
def _decoder(b):return deserialiser_valeur(b,types_supplementaires=TYPES_PAPIER)
def _json(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def _document_table(table):
    return dict(schema='xp-heure-serveur-v1',serveur=table.serveur,version=table.version,
        date_releve=table.date_releve,mesures=list(table.mesures),segments=[dict(
            debut_utc=instant_vers_iso(s.debut_utc_ms),fin_utc=instant_vers_iso(s.fin_utc_ms),
            decalage_secondes=s.decalage_secondes) for s in table.segments])


def _tarif(profil):
    return TarifCommission('QUALIFICATION_C04',profil.commission_par_lot_par_cote,
        profil.commission_minimum_par_ordre,profil.commission_par_lot_par_cote,
        profil.commission_minimum_par_ordre)


def _options(a):
    h=a.registre['historique'];e=a.ingenierie
    return dict(departs_ticks_utc_ms=dict(h['departs_ticks_utc_ms']),
        depuis_historique_compte_utc_ms=h['depuis_compte_utc_ms'],seances_max_age_ms=e['seances_max_age_ms'],
        fermetures_max_age_ms=e['fermetures_max_age_ms'],max_jours_horaires=e['max_jours_horaires'],
        ecart_horloges_max_ms=e['ecart_horloges_max_ms'],taille_lot=e['taille_lot_ticks'],
        max_ticks_lot=e['max_ticks_lot'],longueur_empreinte=e['longueur_empreinte'],max_taches_natives=e['max_taches_natives'])


class BoucleDirect:
    def __init__(self,application,infrastructure,table,qualification):
        if (not isinstance(application,ConfigurationApplication) or not isinstance(infrastructure,InfrastructurePhysique)
                or not isinstance(table,TableHeureServeur) or application.meta!=infrastructure.meta):
            raise ErreurApplication('COMPOSITION_DIRECTE_INCOHERENTE')
        self.application=application;self.infrastructure=infrastructure;self.table=table
        self._horloge=infrastructure.horloge;self._e=application.ingenierie
        analyser_registre(application.registre,application.configuration,self._horloge.utc_ms())
        verifier_autorisations(application)
        self._papier=application.mode in ('PAPER','PAPER_AB');self._livres={};self._ports={}
        self._ops={};self._contextes=set();self._vus={};self._disponibles={s:False for s in application.liaisons}
        self._profils={};self._profils_prets={s:False for s in application.liaisons};self._versions={s:0 for s in application.liaisons};self._sorties=[]
        self._numero=0;self._stockage_pret=True;self._alertes=set();self._dernier_cycle_ns=None
        self._ack={};self._marche_publie={};self._disponibilite_publie={}
        self._prochain_controle_ns=0;self._prochain_snapshot_ns=0;self._prochaine_minuterie_ns=0
        existante=infrastructure.depot.charger() is not None
        if not existante:
            if infrastructure.depot.dernier_numero:raise ErreurApplication('ETAT_PERSISTANT_ABSENT')
            self._courtier=infrastructure.initialiser_courtier(table,qualification,_options(application))
            fichiers=infrastructure.lire_controles();self._exports(fichiers)
            self._creer()
        else:self._reprendre(qualification)
        self._session=SessionDurable(infrastructure.depot,infrastructure.journal,self._initialisation,
            reprise=self._moteur.exporter_checkpoint_journal() if existante else None)

    @property
    def moteur(self):return self._moteur
    @property
    def livres(self):return dict(self._livres)
    @property
    def session(self):return self._session

    def _alerter(self,code):
        if code not in self._alertes:
            self._alertes.add(code);alerter(code,'CONSULTER_LE_JOURNAL_ET_LA_PROCEDURE_EXPLOITATION')

    def _exports(self,fichiers):
        seances={self.application.liaisons[r.symbole]:r.octets for r in fichiers if r.nature=='SEANCES'}
        fermeture=next((r.octets for r in fichiers if r.nature=='FERMETURES'),None)
        t=self._horloge.utc_ms();self._courtier.recevoir_exports(t,seances=seances,fermetures=fermeture)

    def _creer(self):
        a=self.application;c=self._courtier;t=self._horloge.utc_ms();c.actualiser_instant(t)
        profils={s:c.specifications.instrument(s,t) for s in a.liaisons};compte=c.profil_compte(t)
        if not isinstance(compte,ProfilCompte) or any(not isinstance(p,ProfilInstrument) for p in profils.values()):
            raise ErreurApplication('ENVIRONMENT_NOT_READY_PROFILS_INITIAUX')
        r=c.observer();t=r.instant_ms
        if not self._papier and r.observation is None:raise ErreurApplication('RAPPROCHEMENT_INITIAL_ABSENT')
        noms=('REFERENCE','IA') if a.mode=='PAPER_AB' else ('IA',) if a.registre['activation_veto'] and not self._papier else ('REFERENCE',)
        for nom in noms:
            if self._papier:
                creation=t//86400000*86400000
                conditions=tuple(ConditionContrat(creation,p.horaires.fin_validite_ms,t,p,_tarif(p)) for p in profils.values())
                p=LivrePapier(a.configuration,conditions,creation);p.avancer_au(t)
                self._livres[nom]=p;self._ports[nom]=p;self._ops[nom]=0
            else:self._ports[nom]=PortCompte(c.calculs,compte)
        initiales={n:dict(profil_compte=p.profil_compte,instant_ms=t,
            observation=p.observation() if self._papier else r.observation,
            base_utc=p.base_utc() if self._papier else r.base_utc) for n,p in self._ports.items()}
        self._composition=dict(schema='xp-composition-direct-v1',configuration=a.configuration,
            deploiement=a.deploiement,mode=a.mode,longueur_empreinte=a.ingenierie['longueur_empreinte'],
            profils=profils,horaires={s:p.horaires for s,p in profils.items()},periodes_couvertes={s:() for s in profils},
            initiales=initiales,scenario_fondamental=a.registre['scenario_fondamental'],table_heure=_document_table(self.table),
            politique_ia=dict(bras_ia='IA' in noms,execution_reelle=not self._papier,
                             validation_financiere=not self._papier and a.registre['activation_veto']))
        self._moteur=composer_moteur(a.configuration,self._composition,self._ports);self._profils=profils
        self._initialisation=_encoder(dict(schema='xp-initialisation-direct-v1',composition=self._composition,
            appels_initialisation=self._moteur.initialisation_calculs,
            livres={n:p.initialisation for n,p in self._livres.items()}))

    def _reprendre(self,qualification):
        depot=self.infrastructure.depot;entrees=depot.entrees()
        if not entrees:raise ErreurApplication('INITIALISATION_DIRECTE_ABSENTE')
        e=json.loads(entrees[0].decode('utf-8'))
        if e.get('type_evenement')!='INITIALISATION':raise ErreurApplication('INITIALISATION_DIRECTE_ABSENTE')
        self._initialisation=_json(e['contenu']);ini=_decoder(self._initialisation)
        if (not isinstance(ini,Mapping) or set(ini)!={'schema','composition','appels_initialisation','livres'}
                or ini['schema']!='xp-initialisation-direct-v1'):
            raise ErreurApplication('INITIALISATION_DIRECTE_INCOMPATIBLE')
        self._composition=ini['composition'];i=self._composition;a=self.application
        if (i['deploiement']!=a.deploiement or i['mode']!=a.mode
                or {s:p.symbole_courtier for s,p in i['profils'].items()}!=dict(a.liaisons)):
            raise ErreurApplication('REPRISE_DEPLOIEMENT_ETRANGERE')
        recu=SessionDurable(depot,self.infrastructure.journal,self._initialisation).charger()
        m,_=rejouer_incident(a.configuration,i,dict(ini['appels_initialisation']),recu['entrees'],recu['checkpoint'],
            reprises=recu.get('reprises',()))
        self._courtier=self.infrastructure.initialiser_courtier(self.table,qualification,_options(a),etat=recu['courtier'])
        if set(ini['livres'])!=set(recu['livres']):raise ErreurApplication('REPRISE_LIVRES_INCOMPATIBLES')
        for nom,v in ini['livres'].items():
            d=recu['livres'][nom]
            p=LivrePapier(a.configuration,v['conditions'],v['creation_ms'],v['scenario'],
                checkpoint=deserialiser_valeur(d['checkpoint']),operations=d['operations'])
            self._livres[nom]=p;self._ports[nom]=p;self._ops[nom]=len(d['operations'])
            for b in d['operations']:
                op=_decoder(b)
                if op['nature']=='enregistrer_contexte':self._contextes.add((nom,_decoder(op['arguments'])[0]))
        if not self._papier:
            self._ports={n:PortCompte(self._courtier.calculs,v['profil_compte']) for n,v in i['initiales'].items()}
        self._moteur=composer_moteur(a.configuration,i,self._ports,checkpoint=m.exporter_checkpoint(),entrees=m.entrees)
        self._numero=recu['checkpoint'].numero_entrees;self._profils=dict(i['profils'])
        for s,document in recu['checkpoint'].flux:
            d=json.loads(document)
            if d.get('schema')=='xp-flux-moteur-v2':self._versions[s]=d['marche']['version']

    def _avancer(self,t):
        self._courtier.actualiser_instant(t)
        for p in self._livres.values():p.avancer_au(t)

    def _persister(self,sortie=None):
        livres={n:dict(checkpoint=serialiser_valeur(p.checkpoint),operations=p.operations_depuis(self._ops[n]))
                for n,p in self._livres.items()}
        try:r=self._session.persister(self._moteur,sortie,courtier=self._courtier.exporter_etat(),livres=livres)
        except (ValueError,TypeError,AssertionError):raise
        except Exception:
            self._stockage_pret=False;self._alerter('STOCKAGE_INDISPONIBLE');return None
        self._stockage_pret=True
        for n,p in self._livres.items():self._ops[n]=p.checkpoint['nombre_operations']
        if not r.projection_reussie:self._alerter('PROJECTION_C09_A_REPARER')
        return r

    def _defenses(self,sortie):
        for n,s in sortie.sorties:
            cs=tuple(c for c in s.commandes if c.nature is not NatureCommande.ENTREE)
            if not cs:continue
            if self._papier:
                t=sortie.instant_ms;self._avancer(t)
                ack=self._livres[n].soumettre(cs)
                self._ajouter_ack(n,ack)
            else:self._courtier.soumettre_defenses(cs,self._horloge.utc_ms())

    def _emettre(self,t,*,ticks=(),maj=(),receptions=(),confirmation=True):
        self._avancer(t)
        e=EntreeMoteur(t,self._numero+1,'TICKS' if ticks else 'MINUTERIE',tuple(ticks),tuple(maj),tuple(receptions))
        s=self._moteur.traiter(e);self._numero=s.numero;self._sorties.append(s)
        self._defenses(s);r=self._persister(s)
        if confirmation and r is not None and r.preuves:self._confirmer(r.preuves)
        return s

    def _confirmer(self,preuves):
        t=self._horloge.utc_ms();self._avancer(t)
        s=self._moteur.confirmer_persistance(dict(preuves),t);self._numero=s.numero;self._sorties.append(s)
        self._defenses(s)
        entrees={n:tuple(c for c in b.commandes if c.nature is NatureCommande.ENTREE) for n,b in s.sorties}
        if self._papier:
            # Les preuves sont déjà COMMITées. Les réponses papier sont de nouvelles entrées.
            for n,cs in entrees.items():
                if not cs:continue
                dossiers={d.cle:d for d in self._moteur.bras[n].coordinateur.etat.intentions}
                for c in cs:
                    if (n,c.cle) not in self._contextes:
                        self._livres[n].enregistrer_contexte(c.cle,dossiers[c.cle].signal.contexte);self._contextes.add((n,c.cle))
                ack=self._livres[n].soumettre(cs)
                self._persister(s)
                self._ajouter_ack(n,ack)
            if not any(entrees.values()):self._persister(s)
        else:
            cs=tuple(c for valeurs in entrees.values() for c in valeurs)
            p=self._courtier.preparer_entrees(cs,self._horloge.utc_ms()) if cs else None
            r=self._persister(s)
            if r is not None and p is not None:
                self._courtier.autoriser_entrees(PreuvePersistance(p.revision,p.references))

    def _controles(self,fichiers):
        receptions=[]
        for r in fichiers:
            if r.nature not in ('PERMISSION','CALENDRIER'):continue
            if self.application.registre['scenario_fondamental'] is not None:continue
            cle=(r.nature,r.symbole);valeur=(r.octets,r.erreur)
            if self._vus.get(cle)==valeur:continue
            self._vus[cle]=valeur
            if r.erreur is not None:
                self._alerter('LECTURE_C05_INDISPONIBLE')
                if r.nature=='PERMISSION':receptions.append(ReceptionExterne('INTERRUPTION',b'',r.symbole))
            elif r.nature=='PERMISSION':receptions.append(ReceptionExterne('PERMISSION',r.octets,r.symbole))
            else:receptions.append(ReceptionExterne('CALENDRIER',r.octets,
                table=TableImportance('MQL5','IMPORTANCE_NATIVE_V1',('CALENDAR_IMPORTANCE_HIGH',))))
        return tuple(receptions)

    def _actualiser_profils(self,t):
        for s in self.application.liaisons:
            p=self._courtier.specifications.instrument(s,t)
            val=isinstance(p,ProfilInstrument);self._profils_prets[s]=val
            if val:
                self._profils[s]=p
                for livre in self._livres.values():livre.actualiser_profil(p,_tarif(p),t)
            else:self._alerter('PROFIL_C04_COURANT_INDISPONIBLE')
        self._fixer_disponibilite(t)

    def _fixer_disponibilite(self,t):
        disponibles={s:self._disponibles[s] and self._profils_prets[s] and self._stockage_pret for s in self.application.liaisons}
        for p in self._ports.values():
            if self._papier:
                for s,b in disponibles.items():
                    if self._disponibilite_publie.get((id(p),s))!=b:
                        p.fixer_disponibilite(s,b,t);self._disponibilite_publie[id(p),s]=b
            else:p.fixer_disponibilite(tuple(s for s,b in disponibles.items() if b))

    def _ajouter_ack(self,nom,retours):
        for r in retours:
            u=(MiseAJourBras(observation=r,base_utc=self._livres[nom].base_utc())
               if isinstance(r,ObservationNative) else MiseAJourBras(reponses=(r,)))
            self._ack.setdefault(nom,[]).append(u)

    def _drainer_ack(self):
        while self._ack:
            ack=self._ack;self._ack={}
            for n,mises in ack.items():
                for u in mises:self._emettre(self._horloge.utc_ms(),maj=((n,u),))

    def iterer(self):
        self._sorties=[];self._dernier_cycle_ns=self._horloge.monotone_ns()
        # Collecte/observation avant les bougies ; leur temps est celui du retour réel.
        if not self._papier:
            r=self._courtier.collecter()
            for code in r.alertes:self._alerter(code)
            if r.reponses:self._emettre(r.instant_ms,maj=tuple((n,MiseAJourBras(reponses=r.reponses)) for n in self._ports))
        ns=self._horloge.monotone_ns();receptions=()
        if ns>=self._prochain_controle_ns:
            fichiers=self.infrastructure.lire_controles();self._exports(fichiers)
            receptions=self._controles(fichiers);t=self._horloge.utc_ms();self._avancer(t);self._actualiser_profils(t)
            self._prochain_controle_ns=self._horloge.monotone_ns()+self._e['controles_ms']*1000000
        if 'IA' in self._ports and ns>=self._prochain_snapshot_ns:
            b,t,erreur=self.infrastructure.lire_snapshot()
            if erreur:self._alerter('LECTURE_SNAPSHOT_INDISPONIBLE')
            receptions+= (ReceptionExterne('SNAPSHOT',b),)
            self._prochain_snapshot_ns=self._horloge.monotone_ns()+self._e['snapshot_ms']*1000000
        t=self._horloge.utc_ms();self._avancer(t);maj=[]
        echeance=self._moteur.prochaine_echeance_ms
        minuterie=ns>=self._prochaine_minuterie_ns or echeance is not None and echeance<=t
        if self._papier:
            for n,p in self._livres.items():maj.append((n,MiseAJourBras(reponses=p.extraire_reponses(t),observation=p.observation(),base_utc=p.base_utc())))
        elif minuterie:
            r=self._courtier.observer(depuis_flux_ms=self.application.registre['historique']['depuis_compte_utc_ms'])
            t=r.instant_ms
            for code in r.alertes:self._alerter(code)
            maj=tuple((n,MiseAJourBras(observation=r.observation,base_utc=r.base_utc)) for n in self._ports)
        # Un premier passage rend et transmet les défenses avant lire_marche et son rattrapage.
        if minuterie or receptions or any(u.reponses for _,u in maj):
            self._emettre(t,maj=tuple(maj),receptions=receptions);self._drainer_ack()
            if minuterie:self._prochaine_minuterie_ns=self._horloge.monotone_ns()+self._e['minuterie_ms']*1000000
        lot=self._courtier.lire_marche();t=lot.instant_ms;self._avancer(t)
        for _,code in lot.erreurs:self._alerter(code)
        self._disponibles={s:bool(dict(lot.a_jour).get(s,False)) for s in self.application.liaisons}
        self._fixer_disponibilite(t)
        faits=[]
        for s,couverture in lot.couvertures:
            p=self._profils[s];h=p.horaires
            contenu=dict(horaires=dict(seances=[[i.debut_ms,i.fin_ms] for i in h.seances],fermetures=[[i.debut_ms,i.fin_ms] for i in h.fermetures],
                    debut_validite_ms=h.debut_validite_ms,fin_validite_ms=h.fin_validite_ms),
                periodes_couvertes=[[i.debut_ms,i.fin_ms] for i in couverture])
            if self._marche_publie.get(s)!=contenu:
                self._versions[s]+=1;self._marche_publie[s]=contenu
                faits.append(ReceptionExterne('MARCHE',_json(dict(schema='xp-etat-marche-v1',version=self._versions[s],**contenu)),s))
        maj=[]
        if self._papier:
            for n,p in self._livres.items():
                reponses=tuple(r for tick in lot.ticks for r in p.sur_tick(tick))
                maj.append((n,MiseAJourBras(reponses=reponses,observation=p.observation(),base_utc=p.base_utc())))
        if lot.ticks or faits:self._emettre(t,ticks=lot.ticks,maj=tuple(maj),receptions=tuple(faits));self._drainer_ack()
        return tuple(self._sorties)

    def attendre(self):
        debut=self._dernier_cycle_ns if self._dernier_cycle_ns is not None else self._horloge.monotone_ns()
        fin=debut+self._e['boucle_ms']*1000000
        prochaine=self._moteur.prochaine_echeance_ms
        if prochaine is not None:
            fin=min(fin,self._horloge.monotone_ns()+max(0,prochaine-self._horloge.utc_ms())*1000000)
        self._horloge.attendre_ms(max(0,(fin-self._horloge.monotone_ns())/1000000))

    def executer(self,jusqua_ms=None,max_iterations=None):
        if jusqua_ms is not None:verifier_instant(jusqua_ms)
        if max_iterations is not None and (type(max_iterations) is not int or max_iterations<=0):
            raise ErreurApplication('LIMITE_ITERATIONS_INVALIDE')
        n=0
        while (jusqua_ms is None or self._horloge.utc_ms()<jusqua_ms) and (max_iterations is None or n<max_iterations):
            self.iterer();n+=1
            if (max_iterations is None or n<max_iterations) and (jusqua_ms is None or self._horloge.utc_ms()<jusqua_ms):self.attendre()
        return dict(schema='xp-rapport-direct-v1',iterations=n,entrees=self._numero,
            validation_financiere='NON_EVALUEE',alertes=tuple(sorted(self._alertes)))

    def archive_incident(self):
        s=self._session.charger()
        if s is None:raise ErreurApplication('AUCUN_COMMIT_A_ARCHIVER')
        decisions=tuple(b for _,_,ds,_ in self.infrastructure.depot.evenements() for b in ds)
        return _encoder(dict(schema='xp-archive-incident-v1',session=s,decisions=decisions))
