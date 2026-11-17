"""COMMIT, deltas, projection et reprise avec les frontières physiques réelles."""
from pathlib import Path
from tempfile import TemporaryDirectory
from sqlite3 import OperationalError
import json,unittest
from dataclasses import replace
from xpbots.noyau.c2_journal import serialiser

from robot.outils.orchestration import C,composer_bras,ticks_courts
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1b_session_durable import SessionDurable
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0d_journal import JournalFichiers
from xpbots.orchestration.c0_contrats import MiseAJourBras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.contexte_ia.c0_types import charger_parametres,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte


def composition(ab=False):
    ia=LecteurContexte(charger_parametres(C),PolitiqueVeto(True)) if ab else None
    mode=C.ia.parametres['default_evaluation_mode'] if ab else 'REJEU'
    b,p,h,c=composer_bras(mode=mode)
    bras=[b];ports={'REFERENCE':p}
    if ab:
        b2,p2,_,_=composer_bras('IA',mode=mode,lecteur=ia)
        bras.append(b2);ports['IA']=p2
    m=MoteurDecision(C,bras,h,c,lecteur_ia=ia,scenario_fondamental='TECHNICAL_CONTROL_NEUTRAL')
    return m,ports


def tick_suivant(m,ports,tick):
    for p in ports.values():p.avancer_au(tick.instant_reception_ms)
    return m.traiter_ticks((tick,),mises_a_jour=tuple((n,MiseAJourBras(observation=p.observation(),base_utc=p.base_utc())) for n,p in ports.items()))


class TestSessionDurable(unittest.TestCase):
    def test_marqueur_reprise_sans_session_ou_hors_prefixe_refuse(self):
        m,p=composition();initial=m.exporter_checkpoint_journal()
        with self.assertRaisesRegex(ErreurApplication,'MARQUEUR_REPRISE_HORS_PREFIXE'):
            SessionDurable(self.db,self.j,self.ini,reprise=initial)
        s=tick_suivant(m,p,ticks_courts()[0]);self.s.persister(m,s)
        with self.assertRaisesRegex(ErreurApplication,'MARQUEUR_REPRISE_HORS_PREFIXE'):
            SessionDurable(self.db,self.j,self.ini,reprise=initial)

    def test_marqueur_reprise_retenu_pendant_echec_puis_archive_une_fois(self):
        m,p=composition();s=tick_suivant(m,p,ticks_courts()[0]);self.s.persister(m,s)
        marqueur=m.exporter_checkpoint_journal()
        reprise=SessionDurable(self.db,self.j,self.ini,reprise=marqueur)
        self.db.connexion.execute('PRAGMA query_only=ON')
        with self.assertRaises(OperationalError):reprise.persister(m)
        self.assertNotIn('reprises',reprise.charger())
        self.db.connexion.execute('PRAGMA query_only=OFF');reprise.persister(m)
        reprise.persister(m)
        r=SessionDurable(self.db,self.j,self.ini).charger()
        self.assertEqual(r['reprises'],(marqueur,))
        self.assertEqual(r['entrees'],m.entrees)
        self.assertEqual(sum(json.loads(b)['type_evenement']=='REPRISE_MOTEUR' for b in self.db.entrees()),1)

    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.db=DepotSQLite(self.root/'etat.sqlite',{'fixture':'session-durable'})
        self.addCleanup(self.db.fermer)
        self.j=JournalFichiers(self.root,'essai_orchestration')
        self.ini=serialiser_valeur({'fixture':'composition-figee'})
        self.s=SessionDurable(self.db,self.j,self.ini)

    def test_initialisation_unique_deltas_et_reprise_exacte(self):
        m,ports=composition()
        for tick in ticks_courts()[:2]:
            sortie=tick_suivant(m,ports,tick)
            r=self.s.persister(m,sortie,courtier={'curseur':tick.numero})
            self.assertTrue(r.projection_reussie)
        self.assertEqual(self.db.dernier_numero,2)
        e=[json.loads(b) for b in self.db.entrees()]
        self.assertEqual([d['numero'] for d in e],[1,2,3])
        self.assertEqual([d['type_evenement'] for d in e],['INITIALISATION','ENTREE_MOTEUR','ENTREE_MOTEUR'])
        reprise=SessionDurable(self.db,self.j,self.ini).charger()
        self.assertEqual(reprise['checkpoint'],m.exporter_checkpoint_journal())
        self.assertEqual(reprise['entrees'],m.entrees)
        self.assertEqual(reprise['courtier'],{'curseur':1})

    def test_second_commit_du_livre_natif_sans_dupliquer_decisions(self):
        m,ports=composition()
        for tick in ticks_courts()[:2]:
            sortie=tick_suivant(m,ports,tick);self.s.persister(m,sortie)
        avant=sum(len(d) for _,_,d,_ in self.db.evenements());n=len(self.db.entrees())
        self.s.persister(m,courtier={'phase':'PREPAREE_NON_AUTORISEE'})
        self.assertEqual(len(self.db.entrees()),n)
        self.assertEqual(sum(len(d) for _,_,d,_ in self.db.evenements()),avant)
        self.assertEqual(self.s.charger()['courtier'],{'phase':'PREPAREE_NON_AUTORISEE'})

    def test_echec_sql_aucune_preuve_et_reprise_de_la_transaction(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0])
        self.db.connexion.execute('PRAGMA query_only=ON')
        with self.assertRaises(OperationalError):self.s.persister(m,sortie)
        self.assertEqual(self.db.dernier_numero,0);self.assertIsNone(self.s.charger())
        self.db.connexion.execute('PRAGMA query_only=OFF')
        self.assertEqual(self.s.persister(m,sortie).numero,1)
        self.assertEqual(len(self.db.entrees()),2)

    def test_panne_projection_apres_commit_reparee_sans_reexecuter(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0])
        obstacle=self.root/'logs';obstacle.write_bytes(b'OBSTACLE_PHYSIQUE')
        r=self.s.persister(m,sortie)
        self.assertFalse(r.projection_reussie);self.assertEqual(self.db.dernier_numero,1)
        self.assertEqual(self.s.charger()['checkpoint'],m.exporter_checkpoint_journal())
        obstacle.unlink();self.j.publier(self.db.evenements())
        lignes=(self.j.dossier/'entrees_2026-11-09.jsonl').read_bytes().splitlines()
        self.assertEqual(lignes,list(self.db.entrees()))

    def test_identite_etrangere_et_troncature_refusees(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0]);self.s.persister(m,sortie)
        with self.assertRaises(ErreurApplication):SessionDurable(self.db,self.j,serialiser_valeur({'autre':True}))
        self.db.connexion.execute('DELETE FROM entrees WHERE numero=2')
        with self.assertRaisesRegex(ErreurApplication,'TRONQUE'):self.s.charger()

    def test_operations_opaques_archivees_en_delta_et_livres_stables(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0])
        livre={'REFERENCE':{'checkpoint':serialiser_valeur({'position':1}),
                            'operations':(serialiser_valeur({'operation':'TEST_FRONTIERE'}),)}}
        self.s.persister(m,sortie,livres=livre)
        livre['REFERENCE']['operations']=()
        self.s.persister(m,livres=livre)
        charge=self.s.charger()['livres']['REFERENCE']
        self.assertEqual(len(charge['operations']),1)
        self.assertEqual(deserialiser_valeur(charge['checkpoint']),{'position':1})
        with self.assertRaisesRegex(ErreurApplication,'LIVRES_DURABLES'):self.s.persister(m)

    def test_enveloppe_alteree_meme_sans_changement_de_compteur_refusee(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0]);self.s.persister(m,sortie)
        d=json.loads(self.db.entrees()[1]);d['instant_reception_utc_ms']-=1
        b=json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        self.db.connexion.execute('UPDATE entrees SET valeur=? WHERE numero=2',(b,))
        with self.assertRaisesRegex(ErreurApplication,'CHAINE_DURABLE'):self.s.charger()

    def test_schema_ancien_refuse_sans_conversion_ni_ecriture(self):
        m,ports=composition();sortie=tick_suivant(m,ports,ticks_courts()[0])
        self.s.persister(m,sortie)
        d=deserialiser_valeur(self.db.charger());d['schema']='xp-session-direct-v1'
        ancien=serialiser_valeur(d)
        self.db.connexion.execute("UPDATE etat SET valeur=? WHERE espace='session' AND cle='courant'",(ancien,))
        with self.assertRaisesRegex(ErreurApplication,'ETAT_DURABLE_INCOHERENT'):self.s.charger()
        self.assertEqual(self.db.charger(),ancien)

    def test_panne_puis_evenement_suivant_conserve_toutes_les_decisions_c09(self):
        m,ports=composition();attendus=[]
        s1=tick_suivant(m,ports,ticks_courts()[0]);attendus.extend(s1.enregistrements)
        self.db.connexion.execute('PRAGMA query_only=ON')
        with self.assertRaises(OperationalError):self.s.persister(m,s1)
        # Une reprise du même lot ne le duplique pas, même si SQLite échoue encore.
        with self.assertRaises(OperationalError):self.s.persister(m,s1)
        faux=replace(s1,ignoree=True,sorties=())
        with self.assertRaisesRegex(ErreurApplication,'CONTRADICTOIRE'):self.s.persister(m,faux)
        s2=tick_suivant(m,ports,ticks_courts()[1]);attendus.extend(s2.enregistrements)
        self.db.connexion.execute('PRAGMA query_only=OFF');self.s.persister(m,s2)
        recu=tuple(b for _,_,ds,_ in self.db.evenements() for b in ds)
        self.assertEqual(recu,tuple(serialiser(e).encode() for e in attendus))
        self.s.persister(m)
        self.assertEqual(tuple(b for _,_,ds,_ in self.db.evenements() for b in ds),recu)
