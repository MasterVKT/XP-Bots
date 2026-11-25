"""Ports physiques HTTP et publication : secrets fictifs et vrais fichiers."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xpbots.service_ia.c0_types import ErreurService, RequeteHTTP, canonique
from xpbots.service_ia.c1e_fournisseurs import construire_requete
from xpbots.service_ia.c1f_snapshot import fabriquer_snapshot
from xpbots.service_ia.c4_service import TransportHTTP, PublieurSnapshot
from .support import ressources, job, Horloge
from .support_ouvreur import OuvreurScenario, ReponseOuvree


class HTTPPublication(unittest.TestCase):
    def test_http_inactif_et_cles_absentes_sans_ouverture(self):
        r=ressources();h=Horloge();q=construire_requete(r,job(),r.p['providers'][0]['id'])
        with self.assertRaises(OSError):TransportHTTP(r,h)(q)
        o=OuvreurScenario()
        with self.assertRaises(OSError):TransportHTTP(r,h,ouvreur=o)(q)
        self.assertFalse(o.requetes)
    def test_auth_separee_headers_publics_borne_et_fermeture_trois_formats(self):
        r=ressources();h=Horloge()
        for p in r.p['providers']:
            secret='FAUSSE_CLE_'+p['id'];q=construire_requete(r,job(),p['id'])
            o=OuvreurScenario(lambda req,t:ReponseOuvree(req.full_url,b'{}',entetes=(('Set-Cookie','private'),('Retry-After','600'))))
            v=TransportHTTP(r,h,ouvreur=o,cles={p['id']:secret})(q);req,t=o.requetes[0]
            self.assertNotIn(secret,q.corps.decode());self.assertNotIn(secret,q.url)
            self.assertIn(secret,str(dict(req.header_items())))
            self.assertEqual(v.entete('Retry-After'),'600');self.assertIsNone(v.entete('Set-Cookie'))
            self.assertTrue(o.reponses[0].fermee);self.assertEqual(o.reponses[0].plafonds,[q.max_octets+1])
    def test_statut_et_retry_after_preserves_sur_corps_trop_grand(self):
        r=ressources();h=Horloge();pid=r.p['providers'][0]['id'];q=construire_requete(r,job(),pid)
        o=OuvreurScenario(lambda req,t:ReponseOuvree(req.full_url,b'x'*(q.max_octets+99),429,(('Retry-After','900'),)))
        v=TransportHTTP(r,h,ouvreur=o,cles={pid:'SYNTHETIQUE'})(q)
        self.assertEqual(len(v.corps),q.max_octets+1);self.assertEqual(v.statut,429);self.assertEqual(v.entete('Retry-After'),'900')
    def test_reflet_cle_et_header_ambigu_refuses_sans_fuite_exception(self):
        r=ressources();h=Horloge();pid=r.p['providers'][0]['id'];q=construire_requete(r,job(),pid);secret='SYNTHETIQUE_NE_PAS_ARCHIVER'
        for body,headers in ((secret.encode(),()),(b'{}',(('Retry-After','1'),('Retry-After','2')))):
            o=OuvreurScenario(lambda req,t:ReponseOuvree(req.full_url,body,entetes=headers))
            with self.assertRaises(OSError) as ex:TransportHTTP(r,h,ouvreur=o,cles={pid:secret})(q)
            self.assertNotIn(secret,str(ex.exception));self.assertTrue(o.reponses[0].fermee)
    def test_endpoint_forge_redirection_implicite_et_header_interdit_refuses(self):
        r=ressources();h=Horloge();pid=r.p['providers'][0]['id'];q=construire_requete(r,job(),pid);o=OuvreurScenario()
        tr=TransportHTTP(r,h,ouvreur=o,cles={pid:'TEST'})
        for mauvais in (replace(q,url='https://evil.test/'),replace(q,entetes=(('Proxy-Authorization','opaque'),))):
            with self.assertRaises(ErreurService):tr(mauvais)
        self.assertFalse(o.requetes)
        o.action=lambda req,t:ReponseOuvree('https://evil.test/',b'{}')
        with self.assertRaises(OSError):tr(q)
        self.assertTrue(o.reponses[0].fermee)
    def test_publication_reelle_retry_et_ancien_fichier_conserve_a_echec(self):
        r=ressources();h=Horloge();ancien=fabriquer_snapshot(r,1,h.t,[]);nouveau=fabriquer_snapshot(r,2,h.t,[])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'context.json';p.write_bytes(ancien);w=PublieurSnapshot(r,p,h)
            with patch('os.replace',side_effect=PermissionError('partage synthétique')):
                with self.assertRaises(OSError):w(nouveau)
            self.assertEqual(p.read_bytes(),ancien);self.assertEqual(h.attentes,list(r.p['snapshot_write_retry_seconds']))
            w(nouveau);self.assertEqual(p.read_bytes(),nouveau)
