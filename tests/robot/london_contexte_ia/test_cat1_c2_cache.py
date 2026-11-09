"""Catégorie 1, couche 2 : mémoire causale, identités immuables, expiration et reprise."""
from dataclasses import FrozenInstanceError,replace
import unittest
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from xpbots.contexte_ia.c0_types import ErreurContexte,SnapshotRecu,VetoConnu
from xpbots.contexte_ia.c1_snapshot import decoder_snapshot
from xpbots.contexte_ia.c2_cache import CacheVetos,EtatCache


class TestCache(unittest.TestCase):
    def setUp(self):self.c=CacheVetos(parametres());self.t=T+120000;self.fin=T+900000
    def recevoir(self,s=None,t=None):return self.c.recevoir(octets(snapshot() if s is None else s),self.t if t is None else t)

    def test_vide_et_reception_initiale(self):
        self.assertEqual(self.c.derniere_sequence,0)
        self.assertEqual(self.c.consulter('EURUSD',T),())
        r=self.recevoir(t=self.t+137)
        self.assertTrue(r.acceptee);self.assertEqual(r.ajoutes,('evenement_1',))
        v,=self.c.consulter('EURUSD',self.t+137)
        self.assertEqual(v.connu_ms,self.t+137)
        self.assertEqual(v.preuve.snapshot.genere_ms,self.t)
        self.assertEqual(self.c.consulter('EURUSD',self.t+136),())

    def test_relecture_ignoree_sans_changer_premiere_reception(self):
        self.recevoir();avant=self.c.dernier_snapshot
        r=self.recevoir(t=self.t+1)
        self.assertTrue(r.ignoree);self.assertEqual(self.c.dernier_snapshot,avant)
        self.assertEqual(self.c.consulter('EURUSD',self.t+1)[0].connu_ms,self.t)

    def test_snapshot_perime_ne_revoque_pas_cache(self):
        self.recevoir();t=self.t+parametres().age_max_ms+1
        self.assertEqual(self.recevoir(t=t).raison,'PERIME')
        self.assertTrue(self.c.consulter('EURUSD',t))

    def test_sequence_recul_et_reecriture(self):
        self.recevoir(snapshot(sequence=2))
        self.assertEqual(self.recevoir(snapshot()).raison,'SEQUENCE')
        self.assertEqual(self.recevoir(snapshot(sequence=2,evenements=[])).raison,'SEQUENCE_REECRITE')
        self.assertEqual(self.c.derniere_sequence,2)
        self.assertTrue(self.c.consulter('EURUSD',self.t))

    def test_absence_et_corruption_n_effacent_pas_veto(self):
        self.recevoir();dernier=self.c.dernier_snapshot
        for b in (None,b'{}',b'{"a":NaN}'):
            self.assertFalse(self.c.recevoir(b,self.t+1).acceptee)
            self.assertEqual(self.c.dernier_snapshot,dernier)
            self.assertTrue(self.c.consulter('EURUSD',self.t+1))

    def test_heartbeat_vide_conserve_cache(self):
        self.recevoir();r=self.recevoir(snapshot(sequence=2,genere=self.t+30000,evenements=[]),self.t+30000)
        self.assertTrue(r.acceptee);self.assertEqual(r.ajoutes,())
        self.assertTrue(self.c.consulter('EURUSD',self.t+30000))
        self.assertEqual(self.c.prochaine_echeance_ms(self.t+30000),self.fin)

    def test_heartbeat_meme_veto_ne_renouvelle_pas_connaissance(self):
        self.recevoir();v=self.c.consulter('EURUSD',self.t)[0]
        r=self.recevoir(snapshot(sequence=2,genere=self.t+30000),self.t+30000)
        self.assertTrue(r.acceptee)
        self.assertEqual(self.c.consulter('EURUSD',self.t+30000)[0],v)
        self.assertEqual(self.c.prochaine_echeance_ms(self.t+30000),self.fin)

    def test_modification_id_rejetee_atomiquement(self):
        self.recevoir()
        s=snapshot(sequence=2,evenements=[evenement(event_id='nouveau'),evenement(fin=self.fin+1)])
        self.assertEqual(self.recevoir(s).raison,'EVENEMENT_REECRIT')
        self.assertEqual([v.veto.event_id for v in self.c.consulter('EURUSD',self.t)],['evenement_1'])
        self.assertEqual(self.c.derniere_sequence,1)

    def test_id_expire_ne_peut_pas_ressusciter(self):
        self.recevoir();self.c.avancer(self.fin)
        s=snapshot(sequence=2,genere=self.fin,evenements=[evenement(fin=self.fin+900000)])
        self.assertEqual(self.recevoir(s,self.fin).raison,'EVENEMENT_REECRIT')
        self.assertEqual(self.c.consulter('EURUSD',self.fin),())
        self.assertEqual(len(self.c.etat.scelles),1)

    def test_expiration_exclusive_et_histoire_consultee(self):
        self.recevoir()
        self.assertTrue(self.c.consulter('EURUSD',self.fin-1))
        self.c.avancer(self.fin)
        self.assertEqual(self.c.consulter('EURUSD',self.fin),())
        self.assertIsNone(self.c.prochaine_echeance_ms(self.fin))
        self.assertTrue(self.c.consulter('EURUSD',self.fin-1))

    def test_reprise_revalide_octets_a_reception_originale(self):
        self.recevoir();self.c.avancer(self.fin-1)
        e=self.c.etat;r=CacheVetos(parametres(),e)
        self.assertEqual(r.etat,e);self.assertTrue(r.consulter('EURUSD',self.fin-1))
        self.assertEqual(r.consulter('EURUSD',self.fin),())
        with self.assertRaises(FrozenInstanceError):e.dernier_ms=0

    def test_reprise_refuse_octets_et_identites_forges(self):
        self.recevoir();e=self.c.etat;r=e.dernier_snapshot
        faux=SnapshotRecu(replace(r.snapshot,sequence=2),r.reception_ms)
        for etat in (replace(e,dernier_snapshot=faux),replace(e,scelles=e.scelles*2),
            replace(e,scelles=()),replace(e,dernier_ms=T),replace(e,dernier_snapshot=None)):
            with self.subTest(etat=etat),self.assertRaises(ErreurContexte):CacheVetos(parametres(),etat)

    def test_temps_et_types_invalides(self):
        self.recevoir()
        for appel in (lambda:self.c.avancer(self.t-1),lambda:self.recevoir(t=self.t-1),
            lambda:self.c.consulter('AUTRE',self.t),lambda:self.c.consulter('EURUSD',True),
            lambda:EtatCache(scelles=None),lambda:CacheVetos({},self.c.etat)):
            with self.assertRaises(ErreurContexte):appel()

    def test_reprise_refuse_preuves_individuellement_valides_mais_contradictoires(self):
        self.recevoir();premier=self.c.etat.scelles[0]
        dernier=decoder_snapshot(octets(snapshot(sequence=3,genere=T+180000,evenements=[])),T+180000,parametres())
        variantes=((2,T+150000,T+150000,[evenement(fin=self.fin+1),evenement(event_id='e2')]),
            (1,T+150000,T+150000,[evenement(event_id='e2')]),
            (2,T+100000,T+110000,[evenement(event_id='e2')]))
        for seq,genere,reception,events in variantes:
            preuve=decoder_snapshot(octets(snapshot(sequence=seq,genere=genere,evenements=events)),reception,parametres())
            ajoute=VetoConnu(preuve.snapshot.vetos[-1],reception,preuve)
            e=EtatCache(dernier,(premier,ajoute),T+180000)
            with self.subTest(seq=seq,reception=reception),self.assertRaises(ErreurContexte):CacheVetos(parametres(),e)

    def test_doublon_identique_et_choix_de_preuve_stable(self):
        r=self.recevoir(snapshot(evenements=[evenement(event_id='z'),evenement(event_id='a'),evenement(event_id='a')]))
        self.assertEqual(r.ajoutes,('z','a'))
        self.assertEqual([v.veto.event_id for v in self.c.consulter('EURUSD',self.t)],['a','z'])
