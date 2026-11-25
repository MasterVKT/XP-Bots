"""Catégorie 1, couche 1f : snapshot, archive préparée et séquence persistée."""
from copy import deepcopy
import unittest
from robot.outils.contexte_ia import evenement
from xpbots.service_ia.c0_types import ErreurService, canonique, decoder, empreinte
from xpbots.service_ia.c1f_snapshot import fabriquer_snapshot, EcrivainSnapshot
from .support import ressources, document, Memoire


class PublicationMemoire:
    def __init__(self):self.octets=None;self.echec=False
    def __call__(self,b):
        if self.echec:raise OSError('synthetic publication failure')
        self.octets=b


class SnapshotService(unittest.TestCase):
    def setUp(self):
        self.r=ressources();self.t=document().collecte_ms;self.m=Memoire();self.p=PublicationMemoire()
        self.e=evenement(debut=self.t,fin=self.t+self.r.p['unscheduled_policy_veto_seconds_from_publication']*1000)

    def test_enveloppe_canonique_et_configuration_exactes(self):
        b=fabriquer_snapshot(self.r,1,self.t,[self.e]);v=decoder(b)
        self.assertEqual(set(v),{'payload','sha256'});self.assertEqual(b,canonique(v))
        self.assertEqual(v['sha256'],empreinte(v['payload']))
        self.assertEqual(v['payload']['integration_digest'],self.r.digest)
        self.assertEqual(v['payload']['events'],[self.e])

    def test_tous_evenements_valides_avant_publication(self):
        mauvais=[dict(self.e,extra='x'),dict(self.e,provider_id='LOCAL'),dict(self.e,canonical_symbols=['UNKNOWN']),
                 dict(self.e,reason_code='ORDER'),dict(self.e,valid_from_utc='2099-01-01T00:00:00Z')]
        for e in mauvais:
            with self.subTest(e=e),self.assertRaises(ErreurService):EcrivainSnapshot(self.r,self.m,self.p).publier(self.t,[self.e,e])
        self.assertIsNone(self.p.octets);self.assertFalse(self.m.tables['context_snapshots'])

    def test_seq_positive_et_taille_bornee(self):
        for seq in (0,True,-1):
            with self.subTest(seq=seq),self.assertRaises(ErreurService):fabriquer_snapshot(self.r,seq,self.t,[])
        grand=dict(self.e,item_id='x'*self.r.p['snapshot_max_bytes'])
        with self.assertRaises(ErreurService):fabriquer_snapshot(self.r,1,self.t,[grand])

    def test_archive_commit_avant_port(self):
        def publier(b):
            v=decoder(b);s=str(v['payload']['sequence']);a=self.m.tables['context_snapshots'][s]
            self.assertEqual((a['payload_hash'],a['payload'],a['publication_status']),
                             (v['sha256'],v['payload'],'PREPARED'))
        v=EcrivainSnapshot(self.r,self.m,publier).publier(self.t,[self.e])
        self.assertTrue(v.publie);self.assertFalse(self.m.tables['api_attempts'])

    def test_reprise_sequence_et_heartbeat_sans_prolongation(self):
        a=EcrivainSnapshot(self.r,self.m,self.p).publier(self.t,[self.e])
        suivant=self.t+self.r.p['snapshot_heartbeat_seconds']*1000
        b=EcrivainSnapshot(self.r,self.m,self.p).publier(suivant,[self.e])
        self.assertEqual((a.sequence,b.sequence),(1,2))
        self.assertEqual(decoder(a.octets)['payload']['events'],decoder(b.octets)['payload']['events'])
        self.assertEqual(self.m.tables['schedule_state']['snapshot_sequence']['sequence'],2)

    def test_echec_garde_ancien_contenu_et_laisse_un_trou_de_sequence(self):
        e=EcrivainSnapshot(self.r,self.m,self.p);a=e.publier(self.t,[self.e]);ancien=self.p.octets
        self.p.echec=True;b=e.publier(self.t+1,[self.e])
        self.assertFalse(b.publie);self.assertEqual(b.erreur,'PUBLICATION_ECHOUEE')
        self.assertEqual(self.p.octets,ancien)
        self.p.echec=False;c=EcrivainSnapshot(self.r,self.m,self.p).publier(self.t+2,[self.e])
        self.assertEqual((a.sequence,b.sequence,c.sequence),(1,2,3));self.assertTrue(c.publie)

    def test_compteur_perdu_ou_corrompu_et_configuration_differente_refuses(self):
        for defaut in ('perdu','bool','configuration','archive'):
            m=Memoire();p=PublicationMemoire();e=EcrivainSnapshot(self.r,m,p);e.publier(self.t,[])
            if defaut=='perdu':del m.tables['schedule_state']['snapshot_sequence']
            elif defaut=='bool':m.tables['schedule_state']['snapshot_sequence']['sequence']=True
            elif defaut=='configuration':m.tables['schedule_state']['snapshot_sequence']['integration_digest']='changed'
            else:m.tables['schedule_state']['snapshot_sequence']['sequence']=0
            ancien=p.octets
            with self.subTest(defaut=defaut),self.assertRaises(ErreurService):e.publier(self.t+1,[])
            self.assertEqual(p.octets,ancien)

    def test_generation_en_recul_refusee(self):
        e=EcrivainSnapshot(self.r,self.m,self.p);e.publier(self.t,[])
        with self.assertRaises(ErreurService):e.publier(self.t-1,[])
        self.assertEqual(len(self.m.tables['context_snapshots']),1)

    def test_retour_de_port_hors_contrat_signale(self):
        v=EcrivainSnapshot(self.r,self.m,lambda b:True).publier(self.t,[])
        self.assertFalse(v.publie);self.assertEqual(v.erreur,'CONTRAT_PUBLICATION_INVALIDE')
