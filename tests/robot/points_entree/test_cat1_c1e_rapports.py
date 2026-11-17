"""Rapports à partir des vrais journaux et archives, jamais une attestation déclarative."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1a_livre_papier import TYPES_PAPIER
from xpbots.app.c1b_session_durable import SessionDurable
from xpbots.app.c1e_cli_rapports import rapporter_archives,rapporter_incident
from xpbots.app.c1f_composition_moteur import composer_moteur
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0d_journal import JournalFichiers
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from robot.outils.orchestration import C
from robot.points_entree.test_cat1_c1f_composition import composition,evenement


def encoder(v):return serialiser_valeur(v,types_supplementaires=TYPES_PAPIER)
def decoder(b):return deserialiser_valeur(b,types_supplementaires=TYPES_PAPIER)


def archive_incident(ab=False,avec_reprises=False):
    i,p=composition(ab);m=composer_moteur(C,i,p)
    initial=encoder(dict(schema='xp-initialisation-direct-v1',composition=i,
        appels_initialisation=m.initialisation_calculs,livres={n:q.initialisation for n,q in p.items()}))
    with TemporaryDirectory() as r:
        with DepotSQLite(Path(r)/'etat.sqlite',{'fixture':'RAPPORT_INCIDENT'}) as db:
            j=JournalFichiers(r,i['deploiement']);s=SessionDurable(db,j,initial);curseurs={n:0 for n in p}
            for n in range(3):
                if avec_reprises and n:
                    m=composer_moteur(C,i,p,checkpoint=m.exporter_checkpoint(),entrees=m.entrees)
                    s=SessionDurable(db,j,initial,reprise=m.exporter_checkpoint_journal())
                sortie=evenement(m,p,n)
                livres={k:dict(checkpoint=serialiser_valeur(q.checkpoint),operations=q.operations_depuis(curseurs[k])) for k,q in p.items()}
                s.persister(m,sortie,livres=livres)
                curseurs={k:q.checkpoint['nombre_operations'] for k,q in p.items()}
            return encoder(dict(schema='xp-archive-incident-v1',session=s.charger(),
                decisions=tuple(b for _,_,bs,_ in db.evenements() for b in bs)))


class TestContratRapports(unittest.TestCase):
    def test_cle_reprises_fermee_et_type_tuple_requis(self):
        d=decoder(archive_incident());d['session']['reprises']=[]
        with self.assertRaisesRegex(ErreurApplication,'SESSION_INCIDENT_INVALIDE'):
            rapporter_incident(C,encoder(d))

    def test_schema_ferme_et_octets_c09_alteres_refuses(self):
        b=archive_incident();d=decoder(b)
        with self.assertRaisesRegex(ErreurApplication,'ARCHIVE_INCIDENT'):rapporter_incident(C,encoder(dict(d,extra=True)))
        d['decisions']=(d['decisions'][0]+b' ',)+d['decisions'][1:]
        with self.assertRaisesRegex(ErreurApplication,'C09_INCIDENT_DIVERGENT'):rapporter_incident(C,encoder(d))

    def test_entrees_et_operations_tronquees_refusees(self):
        b=archive_incident();d=decoder(b);s=d['session'];s['entrees']=s['entrees'][:-1]
        with self.assertRaisesRegex(ErreurApplication,'REJEU_INCIDENT_DIVERGENT'):rapporter_incident(C,encoder(d))
        d=decoder(b);livre=d['session']['livres']['REFERENCE'];livre['operations']=livre['operations'][:-1]
        with self.assertRaises(ValueError):rapporter_incident(C,encoder(d))

    def test_aucune_archive_n_est_un_rapport_financier(self):
        with self.assertRaisesRegex(ErreurApplication,'ARCHIVES_C10_REQUISES'):rapporter_archives(C,())
        r=rapporter_incident(C,archive_incident())
        self.assertEqual(r['validation_financiere'],'NON_EVALUEE')
        self.assertNotIn('autorisation_execution',r)
