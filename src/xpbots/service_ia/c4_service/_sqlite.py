"""Persistance A10 distincte du journal de compte C08 ; aucune opération réseau."""
from collections.abc import MutableMapping
from copy import deepcopy
from pathlib import Path
from threading import RLock
from uuid import uuid4
import sqlite3
from xpbots.service_ia.c0_types import (ErreurService, RessourcesIA, TABLES_IA,
    JobIA, canonique, decoder, empreinte, texte, instant, utc)

_COLONNES={
    'source_items':dict(item_id='TEXT',url='TEXT',issuer='TEXT',published_at='TEXT',first_seen='TEXT',text_hash='TEXT',text='TEXT',parser_version='TEXT',published_ms='INTEGER',known_ms='INTEGER'),
    'llm_jobs':dict(job_id='TEXT',item_id='TEXT',prompt_hash='TEXT',model_id='TEXT',provider='TEXT',created_at='INTEGER',status='TEXT'),
    'llm_results':dict(job_id='TEXT',sent_at='INTEGER',received_at='INTEGER',raw_response='TEXT',validated_json='TEXT',usage='TEXT',error='TEXT'),
    'policy_events':dict(event_id='TEXT',item_id='TEXT',valid_from='TEXT',valid_until='TEXT',provider_id='TEXT',reason='TEXT',from_ms='INTEGER',until_ms='INTEGER'),
    'context_snapshots':dict(sequence='INTEGER',generated_at='TEXT',payload_hash='TEXT',payload='TEXT'),
    'api_budget':dict(month='TEXT',spent_usd='TEXT',reserved_usd='TEXT',other_costs_usd='TEXT',tax_fx_reserve_usd='TEXT'),
    'candidate_decisions':dict(strategy='TEXT',symbol='TEXT',bar_close='INTEGER',baseline_reasons='TEXT',ai_reason='TEXT',snapshot_id='TEXT',arm='TEXT'),
    'experiment_metrics':dict(period='TEXT',strategy='TEXT',symbol='TEXT',arm='TEXT',net_pnl='TEXT',trade_count='INTEGER',equity_drawdown='TEXT'),
}


class _Table(MutableMapping):
    def __init__(self,depot,nom):self.d=depot;self.nom=nom;self.cache={};self.originaux={};self.supprimes=set();self.actif=True
    def _verifier(self):
        if not self.actif:raise ErreurService('TRANSACTION_TERMINEE')
    def __getitem__(self,k):
        self._verifier();texte(k)
        if k in self.supprimes:raise KeyError(k)
        if k not in self.cache:
            row=self.d._c.execute(f'SELECT document FROM {self.nom} WHERE cle=?',(k,)).fetchone()
            if row is None:raise KeyError(k)
            self.originaux[k]=bytes(row[0]);self.cache[k]=decoder(bytes(row[0]))
        return self.cache[k]
    def __setitem__(self,k,v):
        self._verifier();texte(k)
        if type(v) is not dict:raise ErreurService('LIGNE_IA_OBJET_REQUISE')
        self.cache[k]=decoder(canonique(v));self.supprimes.discard(k)
    def __delitem__(self,k):self[k];self.supprimes.add(k)
    def setdefault(self,k,default=None):
        try:return self[k]
        except KeyError:self[k]=default;return self[k]
    def __iter__(self):
        self._verifier()
        ks={x[0] for x in self.d._c.execute(f'SELECT cle FROM {self.nom}')}
        return iter(sorted((ks|set(self.cache))-self.supprimes))
    def __len__(self):return sum(1 for _ in self)
    def __bool__(self):
        self._verifier()
        if any(k not in self.supprimes for k in self.cache):return True
        return any(k not in self.supprimes for (k,) in self.d._c.execute(f'SELECT cle FROM {self.nom}'))
    def vider_vers_sql(self):
        for k in self.supprimes:
            self.d._c.execute(f'DELETE FROM {self.nom} WHERE cle=?',(k,))
            if self.nom=='source_items':self.d._c.execute('DELETE FROM source_text WHERE item_id=?',(k,))
        for k,v in self.cache.items():
            if k in self.supprimes:continue
            b=canonique(v)
            if b==self.originaux.get(k):continue
            self.d._ecrire(self.nom,k,v,b)


class DepotServiceSQLite:
    def __init__(self,chemin,ressources,*,creer=True):
        if not isinstance(ressources,RessourcesIA) or type(creer) is not bool:raise ErreurService('PARAMETRES_BASE_INVALIDES')
        self.chemin=Path(chemin).resolve();self.r=ressources;self._lock=RLock();self._ferme=False
        existe=self.chemin.exists()
        if not existe and not creer:raise ErreurService('BASE_ABSENTE')
        self.chemin.parent.mkdir(parents=True,exist_ok=True)
        self._c=sqlite3.connect(self.chemin,timeout=1,isolation_level=None,check_same_thread=False)
        try:
            self._c.execute('PRAGMA journal_mode=WAL');self._c.execute('PRAGMA synchronous=FULL')
            self._c.execute('BEGIN IMMEDIATE')
            self._c.execute('CREATE TABLE IF NOT EXISTS meta(cle TEXT PRIMARY KEY,document BLOB NOT NULL)')
            row=self._c.execute("SELECT document FROM meta WHERE cle='identity'").fetchone()
            if row is None:
                if existe:raise ErreurService('BASE_EXISTANTE_NON_QUALIFIEE')
                ident=dict(schema='xp-service-ia-sqlite-v1',integration_digest=ressources.digest,instance_id=uuid4().hex)
                self._c.execute("INSERT INTO meta VALUES('identity',?)",(canonique(ident),))
            else:ident=decoder(bytes(row[0]))
            if ident.get('schema')!='xp-service-ia-sqlite-v1' or ident.get('integration_digest')!=ressources.digest:
                raise ErreurService('IDENTITE_BASE_INCOMPATIBLE')
            texte(ident['instance_id']);self.identite=deepcopy(ident)
            for nom in TABLES_IA:
                colonnes=''.join(','+k+' '+v for k,v in _COLONNES.get(nom,{}).items())
                self._c.execute(f'CREATE TABLE IF NOT EXISTS {nom}(cle TEXT PRIMARY KEY,document BLOB NOT NULL{colonnes})')
            self._c.execute('CREATE INDEX IF NOT EXISTS source_causal ON source_items(issuer,published_ms,known_ms)')
            self._c.execute('CREATE INDEX IF NOT EXISTS source_hash ON source_items(issuer,text_hash)')
            self._c.execute('CREATE INDEX IF NOT EXISTS source_url ON source_items(issuer,url)')
            self._c.execute('CREATE INDEX IF NOT EXISTS jobs_pending ON llm_jobs(status,created_at)')
            self._c.execute('CREATE INDEX IF NOT EXISTS events_active ON policy_events(until_ms,from_ms)')
            self._c.execute('CREATE VIRTUAL TABLE IF NOT EXISTS source_text USING fts5(item_id UNINDEXED,text)')
            self._c.execute('COMMIT')
        except BaseException:
            if self._c.in_transaction:self._c.execute('ROLLBACK')
            self._c.close();self._ferme=True;raise

    def _ouvert(self):
        if self._ferme:raise ErreurService('BASE_FERMEE')

    def _projection(self,nom,v):
        d={k:v.get(k) for k in _COLONNES.get(nom,{})}
        if nom=='source_items':d.update(published_ms=v.get('document',{}).get('publie_ms'),known_ms=v.get('content_known_at'))
        elif nom=='llm_jobs':
            j=v['job'];pid=(v.get('result') or {}).get('fournisseur') or j['fournisseur']
            d.update(job_id=j['job_id'],item_id=j['item_id'],provider=pid,
                model_id=self.r.fournisseur(pid)['model'] if pid else None,
                prompt_hash=empreinte(self.r.prompt(j['kind'])),created_at=j['cree_ms'])
        elif nom=='policy_events':d.update(from_ms=utc(v['valid_from']),until_ms=utc(v['valid_until']))
        for k,val in tuple(d.items()):
            if isinstance(val,(dict,list,tuple)):d[k]=canonique(val).decode('utf-8')
        return d

    def _ecrire(self,nom,k,v,b):
        d=self._projection(nom,v);noms=['cle','document',*d]
        self._c.execute(f"INSERT OR REPLACE INTO {nom}({','.join(noms)}) VALUES({','.join('?' for _ in noms)})",(k,b,*d.values()))
        if nom=='source_items':
            self._c.execute('DELETE FROM source_text WHERE item_id=?',(k,))
            self._c.execute('INSERT INTO source_text(item_id,text) VALUES(?,?)',(k,v['text']))

    def transaction(self,operation):
        if not callable(operation):raise ErreurService('OPERATION_REQUISE')
        with self._lock:
            self._ouvert()
            if self._c.in_transaction:raise ErreurService('TRANSACTION_IMBRIQUEE_INTERDITE')
            tables={nom:_Table(self,nom) for nom in TABLES_IA}
            self._c.execute('BEGIN IMMEDIATE')
            try:
                resultat=deepcopy(operation(tables))
                for table in tables.values():table.vider_vers_sql()
                self._c.execute('COMMIT');return resultat
            except BaseException:
                if self._c.in_transaction:self._c.execute('ROLLBACK')
                raise
            finally:
                for table in tables.values():table.actif=False

    def _lignes(self,sql,args=()):
        with self._lock:
            self._ouvert();return tuple(decoder(bytes(row[0])) for row in self._c.execute(sql,args))

    def selectionner_documents(self,f):
        instant(f['known_at_ms']);clauses=['known_ms<=?'];args=[f['known_at_ms']]
        for cle,col,op in (('issuer','issuer','='),('debut_ms','published_ms','>='),('fin_ms','published_ms','<')):
            if f.get(cle) is not None:clauses.append(col+op+'?');args.append(f[cle])
        alternatives=[]
        for cle,col in (('urls','url'),('hashes','text_hash')):
            valeurs=tuple(f.get(cle,()))
            if valeurs:alternatives.append(col+' IN ('+','.join('?' for _ in valeurs)+')');args.extend(valeurs)
        if alternatives:clauses.append('('+' OR '.join(alternatives)+')')
        return self._lignes('SELECT document FROM source_items WHERE '+' AND '.join(clauses)+' ORDER BY published_ms,cle',args)

    def selectionner_jobs(self):
        lignes=self._lignes("SELECT document FROM llm_jobs WHERE status='QUEUED' ORDER BY created_at,cle")
        return tuple(JobIA(v['job_id'],v['kind'],v['item_id'],v['cree_ms'],v['utile_jusqua_ms'],
            canonique(v['dossier']),tuple(v['evidence_ids']),v['fournisseur']) for v in (a['job'] for a in lignes))

    def selectionner_evenements(self,t):
        instant(t)
        return tuple(a['event'] for a in self._lignes('SELECT document FROM policy_events WHERE from_ms<=? AND until_ms>? ORDER BY cle',(t,t)))

    def chercher_textes(self,requete,*,issuer=None,known_at_ms):
        texte(requete);instant(known_at_ms);sql='SELECT s.document FROM source_items s JOIN source_text f ON f.item_id=s.cle WHERE source_text MATCH ? AND s.known_ms<=?'
        args=[requete,known_at_ms]
        if issuer is not None:texte(issuer);sql+=' AND s.issuer=?';args.append(issuer)
        try:return self._lignes(sql+' ORDER BY s.published_ms,s.cle',args)
        except sqlite3.OperationalError:raise ErreurService('RECHERCHE_TEXTE_INVALIDE') from None

    def fermer(self):
        with self._lock:
            if not self._ferme:self._c.close();self._ferme=True
    def __enter__(self):return self
    def __exit__(self,*_):self.fermer()
