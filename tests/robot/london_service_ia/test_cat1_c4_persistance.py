"""SQLite réel : durabilité des ports, causalité SQL et réservation concurrente."""
from dataclasses import asdict
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from xpbots.service_ia.c0_types import ErreurService, iso
from xpbots.service_ia.c1d_budget import RegistreBudget, cout_maximal
from xpbots.service_ia.c1f_snapshot import EcrivainSnapshot
from xpbots.service_ia.c4_service import DepotServiceSQLite
from .support import ressources, document
from .support_budget import profil, demande


class Persistance(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)/'ia.db';self.r=ressources()
    def tearDown(self):self.tmp.cleanup()
    def test_modification_imbriquee_setdefault_retour_sans_alias_et_reprise(self):
        with DepotServiceSQLite(self.p,self.r) as d:
            def op(t):
                a=t['schedule_state'].setdefault('test',dict(n=0,nested=dict(x=0)))
                a['n']+=1;a['nested']['x']=2;return a
            retour=d.transaction(op);retour['nested']['x']=999
            self.assertEqual(d.transaction(lambda t:t['schedule_state']['test']),dict(n=1,nested=dict(x=2)))
            ident=d.identite
        with DepotServiceSQLite(self.p,self.r,creer=False) as d:
            self.assertEqual(d.identite,ident);self.assertEqual(d.transaction(lambda t:t['schedule_state']['test'])['n'],1)
    def test_exception_annule_tout_et_transaction_reste_utilisable(self):
        with DepotServiceSQLite(self.p,self.r) as d:
            def op(t):t['schedule_state']['test']=dict(n=1);raise RuntimeError('synthetic')
            with self.assertRaises(RuntimeError):d.transaction(op)
            self.assertFalse(d.transaction(lambda t:bool(t['schedule_state'])))
            with self.assertRaises(ErreurService):d.transaction(lambda t:d.transaction(lambda u:None))
            d.transaction(lambda t:t['schedule_state'].__setitem__('ok',dict(n=1)))
    def test_base_preexistante_non_qualifiee_et_absence_refusees(self):
        with self.assertRaises(ErreurService):DepotServiceSQLite(self.p,self.r,creer=False)
        self.p.write_bytes(b'')
        with self.assertRaises(ErreurService):DepotServiceSQLite(self.p,self.r)
    def test_schema_a10_reel_et_modes_durables(self):
        with DepotServiceSQLite(self.p,self.r):
            with closing(sqlite3.connect(self.p)) as c:
                self.assertEqual(c.execute('PRAGMA journal_mode').fetchone()[0],'wal')
                for table,col in (('source_items','text'),('llm_jobs','prompt_hash'),('llm_results','usage'),
                    ('policy_events','valid_until'),('context_snapshots','payload_hash'),('api_budget','reserved_usd'),
                    ('candidate_decisions','snapshot_id'),('experiment_metrics','equity_drawdown')):
                    self.assertIn(col,{r[1] for r in c.execute('PRAGMA table_info('+table+')')})
    def test_snapshot_sequence_restauree_sans_reinference(self):
        t=document().collecte_ms
        with DepotServiceSQLite(self.p,self.r) as d:self.assertEqual(EcrivainSnapshot(self.r,d,lambda b:None).publier(t,[]).sequence,1)
        with DepotServiceSQLite(self.p,self.r) as d:self.assertEqual(EcrivainSnapshot(self.r,d,lambda b:None).publier(t+1,[]).sequence,2)
    def test_reserve_payante_inconnue_persiste_et_empeche_repetition_apres_reouverture(self):
        t=document().collecte_ms;j=demande(t,'inconnu',kind='GOLDEN');p=profil(self.r,t,payant=True);mois=iso(t)[:7]
        with DepotServiceSQLite(self.p,self.r) as d:
            b=RegistreBudget(self.r,d);b.provisionner(mois,'0','0')
            a=b.reserver(j,p,self.r.p['max_input_tokens_upper_bound'],t,paiement_autorise=True)
            self.assertTrue(a.acceptee)
            b.rapprocher(a.reservation.tentative_id,None,None,None,t+1)
            reserve=b.consulter(mois)['reserved_usd'];self.assertGreater(Decimal(reserve),0)
        with DepotServiceSQLite(self.p,self.r) as d:
            b=RegistreBudget(self.r,d);self.assertEqual(b.consulter(mois)['reserved_usd'],reserve)
            self.assertEqual(b.reserver(j,p,self.r.p['max_input_tokens_upper_bound'],t+60000,paiement_autorise=True).raison,'DEJA_TENTEE')
    def test_selection_causale_et_fts_ne_retournent_pas_texte_futur(self):
        doc=document();ligne=dict(item_id=doc.item_id,url=doc.url,issuer=doc.issuer,published_at=iso(doc.publie_ms),
            first_seen=iso(doc.premiere_vue_ms),text_hash=doc.hash_texte,text=doc.texte,parser_version=doc.version_parseur,
            content_known_at=doc.collecte_ms,document=asdict(doc))
        with DepotServiceSQLite(self.p,self.r) as d:
            d.transaction(lambda t:t['source_items'].__setitem__(doc.item_id,ligne))
            self.assertFalse(d.chercher_textes('committee',known_at_ms=doc.collecte_ms-1))
            self.assertEqual(d.chercher_textes('committee',known_at_ms=doc.collecte_ms)[0]['item_id'],doc.item_id)
            self.assertFalse(d.selectionner_documents(dict(issuer='ECB',known_at_ms=doc.collecte_ms)))
            self.assertEqual(len(d.selectionner_documents(dict(issuer='FED',known_at_ms=doc.collecte_ms,urls=(doc.url,)))),1)
    def test_deux_connexions_attendent_commit_et_budget_refuse_seconde_reservation(self):
        t=document().collecte_ms;cout=cout_maximal(self.r);mois=iso(t)[:7]
        with DepotServiceSQLite(self.p,self.r) as a,DepotServiceSQLite(self.p,self.r) as b:
            budget=RegistreBudget(self.r,a);budget.provisionner(mois,'0','0')
            a.transaction(lambda x:x['api_budget'][mois].update(spent_usd=str(Decimal(self.r.p['monthly_paid_api_subcap_usd'])-cout)))
            premiere=threading.Event();seconde=threading.Event();liberer=threading.Event();fini=threading.Event();resultats={};erreurs=[]
            class Port:
                def __init__(self,d,ident):self.d=d;self.ident=ident
                def transaction(self,op):
                    if self.ident=='B':seconde.set()
                    def controle(tables):
                        r=op(tables)
                        if self.ident=='A':premiere.set();liberer.wait(5)
                        return r
                    return self.d.transaction(controle)
            def reserver(d,ident,instant_ms):
                try:resultats[ident]=RegistreBudget(self.r,Port(d,ident)).reserver(demande(instant_ms,ident,kind='GOLDEN'),
                    profil(self.r,t,payant=True),self.r.p['max_input_tokens_upper_bound'],instant_ms,paiement_autorise=True)
                except BaseException as ex:erreurs.append(type(ex).__name__)
                finally:
                    if ident=='B':fini.set()
            x=threading.Thread(target=reserver,args=(a,'A',t));y=threading.Thread(target=reserver,args=(b,'B',t+60000))
            x.start()
            try:
                self.assertTrue(premiere.wait(3));y.start();self.assertTrue(seconde.wait(3));self.assertFalse(fini.wait(.05))
            finally:
                liberer.set();x.join(5)
                if y.ident is not None:y.join(5)
            self.assertFalse(erreurs);self.assertTrue(resultats['A'].acceptee)
            self.assertEqual(resultats['B'].raison,'BUDGET_EPUISE')
            self.assertEqual(Decimal(budget.consulter(mois)['reserved_usd']),cout)
