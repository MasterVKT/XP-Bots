"""Catégorie 1, couche 1 : taille, intégrité, schéma complet et temporalité A10."""
import unittest
from robot.outils.contexte_ia import T,evenement,octets,parametres,snapshot
from xpbots.contexte_ia.c0_types import ErreurContexte,empreinte
from xpbots.contexte_ia.c1_snapshot import ErreurSnapshot,decoder_snapshot


class TestSnapshot(unittest.TestCase):
    def setUp(self):self.p=parametres();self.t=T+120000

    def lire(self,s=None,**kwargs):return decoder_snapshot(octets(snapshot() if s is None else s),self.t,self.p,**kwargs)

    def test_snapshot_valide_conserve_octets_et_reception(self):
        b=octets(snapshot());s=decoder_snapshot(b,self.t+137,self.p)
        self.assertEqual((s.snapshot.sequence,s.snapshot.genere_ms,s.reception_ms),(1,self.t,self.t+137))
        self.assertEqual(s.snapshot.octets,b)
        self.assertEqual(s.snapshot.vetos[0].event_id,'evenement_1')

    def test_taille_inclusive_avant_analyse(self):
        b=octets(snapshot());b+=b' '*(self.p.max_octets-len(b))
        self.assertEqual(len(decoder_snapshot(b,self.t,self.p).snapshot.octets),self.p.max_octets)
        with self.assertRaises(ErreurSnapshot) as c:decoder_snapshot(b+b' ',self.t,self.p)
        self.assertEqual(c.exception.raison,'TAILLE')

    def test_absence_type_et_json_invalides(self):
        for b in (None,'{}',b'{}',b'[]',b'{',b'\xff',b'{"a":NaN}'):
            with self.subTest(b=b),self.assertRaises(ErreurSnapshot):decoder_snapshot(b,self.t,self.p)

    def test_cles_enveloppe_et_payload_exactes(self):
        for s in ({**snapshot(),'extra':0},{'payload':snapshot()['payload']},snapshot(extra=True)):
            with self.assertRaises(ErreurSnapshot) as c:self.lire(s)
            self.assertEqual(c.exception.raison,'SCHEMA')

    def test_sha_schema_et_empreinte_configuration(self):
        mauvais=snapshot();mauvais['sha256']='a'*64
        for s,raison in ((mauvais,'EMPREINTE'),(snapshot(schema='autre'),'SCHEMA'),
            (snapshot(integration_digest='a'*64),'CONFIGURATION')):
            with self.subTest(raison=raison),self.assertRaises(ErreurSnapshot) as c:self.lire(s)
            self.assertEqual(c.exception.raison,raison)

    def test_sequence_positive_recul_et_relecture(self):
        for seq in (0,-1,True,1.0,'1'):
            with self.assertRaises(ErreurSnapshot):self.lire(snapshot(sequence=seq))
        with self.assertRaises(ErreurSnapshot):self.lire(derniere_sequence=2)
        self.assertEqual(self.lire(derniere_sequence=1).snapshot.sequence,1)

    def test_futur_et_age_bornes(self):
        b=octets(snapshot())
        self.assertEqual(decoder_snapshot(b,self.t+self.p.age_max_ms,self.p).snapshot.genere_ms,self.t)
        for t,raison in ((self.t-1,'FUTUR'),(self.t+self.p.age_max_ms+1,'PERIME')):
            with self.assertRaises(ErreurSnapshot) as c:decoder_snapshot(b,t,self.p)
            self.assertEqual(c.exception.raison,raison)

    def test_toute_liste_est_validee_avant_acceptation(self):
        for e in (evenement(reason_code='DISCOURS'),evenement(provider_id='INCONNU'),
            evenement(canonical_symbols=['INCONNU']),evenement(event_id='non représentable'),
            {**evenement(),'extra':1},evenement(item_id='')):
            with self.subTest(e=e),self.assertRaises(ErreurSnapshot) as c:
                self.lire(snapshot(evenements=[evenement(),e]))
            self.assertEqual(c.exception.raison,'EVENEMENT')

    def test_types_liste_et_symboles(self):
        for e in (None,{},'events',True):
            with self.assertRaises(ErreurSnapshot):self.lire(snapshot(events=e))
        for symboles in ([],['EURUSD','EURUSD'],'EURUSD',None):
            with self.assertRaises(ErreurSnapshot):self.lire(snapshot(evenements=[evenement(canonical_symbols=symboles)]))

    def test_heures_evenement_futur_et_expire(self):
        for e in (evenement(debut=self.t+1),evenement(fin=T+60000),
            evenement(valid_from_utc='2026-11-09T08:00:00+01:00')):
            with self.assertRaises(ErreurSnapshot):self.lire(snapshot(evenements=[e]))
        expire=evenement(debut=T,fin=self.t)
        self.assertEqual(self.lire(snapshot(evenements=[expire])).snapshot.vetos[0].valid_until_ms,self.t)

    def test_doublons_json_et_identites_contradictoires(self):
        b=octets(snapshot()).replace(b'"sequence":1',b'"sequence":1,"sequence":1')
        with self.assertRaises(ErreurSnapshot):decoder_snapshot(b,self.t,self.p)
        s=snapshot(evenements=[evenement(),evenement(fin=T+900001)])
        with self.assertRaises(ErreurSnapshot):self.lire(s)
        self.assertEqual(len(self.lire(snapshot(evenements=[evenement(),evenement()])).snapshot.vetos),2)

    def test_utf8_et_appels_mal_types(self):
        s=snapshot(evenements=[evenement(item_id='document-é')])
        self.assertEqual(self.lire(s).snapshot.vetos[0].item_id,'document-é')
        for appel in (lambda:decoder_snapshot(octets(s),True,self.p),
            lambda:decoder_snapshot(octets(s),self.t,{}),lambda:self.lire(derniere_sequence=True)):
            with self.assertRaises(ErreurContexte):appel()
