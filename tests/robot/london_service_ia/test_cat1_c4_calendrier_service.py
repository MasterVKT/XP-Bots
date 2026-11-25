"""D12 physique, disponibilité historique et ownership du service."""
from pathlib import Path
import tempfile
import unittest
from xpbots.service_ia.c0_types import ErreurService
from xpbots.service_ia.c4_service import DepotServiceSQLite, CalendrierService, ServiceIA
from robot.outils.fondamental import calendrier, octets, ConversionServeurScenario, table_importance
from .support import ressources, document, Horloge
from .support_calendrier import mapping


class CalendrierEtPropriete(unittest.TestCase):
    def test_calendrier_manquant_invalide_ou_retabli_ne_perd_pas_ordre_a_timestamp_egal(self):
        r=ressources();h=Horloge();doc=document(t=h.t)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);f=p/'calendrier.json';base=p/'ia.db'
            def creer(d):return CalendrierService(r,d,f,ConversionServeurScenario(),table_importance(),mapping(doc),h,max_octets=r.p['rss_max_download_bytes'])
            with DepotServiceSQLite(base,r) as d:
                c=creer(d);self.assertFalse(c.actualiser())
                f.write_bytes(octets(calendrier(export_ms=h.t)));self.assertTrue(c.actualiser())
                f.write_bytes(b'invalid');self.assertFalse(c.actualiser());self.assertFalse(c(h.t)[-1])
            with DepotServiceSQLite(base,r) as d:
                c=creer(d);self.assertFalse(c(h.t)[-1]);self.assertIsNotNone(c(h.t)[0].version_connue(h.t))
                h.t+=1000;f.write_bytes(octets(calendrier(export_ms=doc.collecte_ms)))
                self.assertTrue(c.actualiser());self.assertTrue(c(h.t)[-1]);self.assertFalse(c(h.t-1)[-1])
    def test_calendrier_future_version_et_disponibilite_non_anticipees(self):
        r=ressources();h=Horloge();doc=document(t=h.t)
        with tempfile.TemporaryDirectory() as tmp,DepotServiceSQLite(Path(tmp)/'ia.db',r) as d:
            f=Path(tmp)/'cal.json';c=CalendrierService(r,d,f,ConversionServeurScenario(),table_importance(),mapping(doc),h,max_octets=r.p['rss_max_download_bytes'])
            f.write_bytes(octets(calendrier(export_ms=h.t)));self.assertTrue(c.actualiser());t=h.t
            h.t+=1000;f.write_bytes(octets(calendrier(version=2,export_ms=h.t)));c.actualiser()
            self.assertEqual(c(t)[0].version_connue(t).version,1)
            f.unlink();h.t+=1000;self.assertFalse(c.actualiser());self.assertFalse(c(h.t)[-1]);self.assertTrue(c(t)[-1])
    def test_deux_producteurs_refuses_et_verrou_libere_apres_echec(self):
        r=ressources();h=Horloge()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=p/'ia.db';snapshot=p/'context.json'
            with ServiceIA(r,base,snapshot,horloge=h) as s:
                self.assertTrue(s.heartbeat().publie)
                with self.assertRaises((ErreurService,ValueError)):ServiceIA(r,base,snapshot,horloge=h)
                with self.assertRaises((ErreurService,ValueError)):ServiceIA(r,p/'autre.db',snapshot,horloge=h)
            with ServiceIA(r,base,snapshot,horloge=h) as s:self.assertEqual(s.heartbeat().sequence,2)
    def test_perte_de_base_avec_manifeste_ne_reinitialise_pas_budget(self):
        r=ressources();h=Horloge()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=p/'ia.db';snapshot=p/'context.json'
            with ServiceIA(r,base,snapshot,horloge=h) as s:s.heartbeat()
            base.unlink()
            with self.assertRaises(ErreurService):ServiceIA(r,base,snapshot,horloge=h)
            self.assertFalse(base.exists())
    def test_compteur_de_calendrier_perdu_ne_reecrit_pas_historique(self):
        r=ressources();h=Horloge();doc=document(t=h.t)
        with tempfile.TemporaryDirectory() as tmp,DepotServiceSQLite(Path(tmp)/'ia.db',r) as d:
            f=Path(tmp)/'cal.json';f.write_bytes(octets(calendrier(export_ms=h.t)))
            args=(r,d,f,ConversionServeurScenario(),table_importance(),mapping(doc),h)
            CalendrierService(*args,max_octets=r.p['rss_max_download_bytes']).actualiser()
            d.transaction(lambda t:t['schedule_state'].__delitem__('calendar_sequence'))
            with self.assertRaises(ErreurService):CalendrierService(*args,max_octets=r.p['rss_max_download_bytes'])
