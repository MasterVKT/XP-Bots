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


from robot.points_entree.test_cat1_c1e_rapports import archive_incident,encoder,decoder


class TestJonctionRapports(unittest.TestCase):
    def test_deux_reprises_physiques_ab_reconstruites_par_c08(self):
        a=archive_incident(True,avec_reprises=True);d=decoder(a)
        self.assertEqual(len(d['session']['reprises']),2)
        self.assertEqual([m.numero_entrees for m in d['session']['reprises']],[1,2])
        r=rapporter_incident(C,a)
        self.assertEqual(r['statut'],'IDENTIQUE');self.assertEqual(r['entrees'],3)
        self.assertEqual(set(r['livres_verifies']),{'REFERENCE','IA'})

    def test_session_ab_reelle_reconstruite_et_deux_livres_verifies(self):
        d=decoder(archive_incident(True));r=rapporter_incident(C,encoder(d))
        self.assertEqual(r['statut'],'IDENTIQUE');self.assertEqual(r['entrees'],3)
        self.assertEqual(r['decisions'],len(d['decisions']))
        self.assertEqual(set(r['livres_verifies']),{'REFERENCE','IA'})
        self.assertEqual(len(r['empreinte_etat']),64)

    def test_archives_c10_produites_par_la_commande_reelle_rapport_conservateur(self):
        import gzip
        from robot.points_entree.test_cat1_c1c_rejeu import demande_fixture
        from xpbots.app.c1c_cli_rejeu import lancer_rejeu
        d,lignes=demande_fixture()
        with TemporaryDirectory() as r:
            f=Path(r)/'ticks.csv.gz';f.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0))
            a=lancer_rejeu(C,d,f);rapport=rapporter_archives(C,(a['archive'],))
        self.assertEqual(rapport,a['rapport'])
        self.assertEqual(rapport['statut'],'NON_VALIDE')
