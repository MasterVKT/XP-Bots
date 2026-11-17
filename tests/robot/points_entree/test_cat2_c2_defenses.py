"""La vraie boucle poursuit FLATTEN quand le stockage et le flux échouent."""
from unittest.mock import patch
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.scenario_london_direct import ScenarioLondonDirect
from robot.outils.orchestration import C
from xpbots.app.c1e_cli_rapports import rapporter_incident


class TestDefensesPhysiques(HarnaisDirect,unittest.TestCase):
    def test_flatten_position_paper_pendant_panne_sql_et_reseau_puis_c09_complet(self):
        s=ScenarioLondonDirect(self);s.jusqua(s.debut+15*60000+250)
        p=s.boucle.livres['REFERENCE'];self.assertTrue(p.positions_ouvertes)
        self.infra.depot.connexion.execute('PRAGMA query_only=ON')
        avant=self.infra.depot.dernier_numero
        self.avancer(1000);s.publier('FLATTEN',force=True)
        self.sdk.scenarios['copy_ticks_from'].append(None)
        with patch('sys.stderr') as alerte:
            sorties=s.iterer()
            self.assertTrue(any(c.nature.value=='CLOTURE' for sortie in sorties for _,b in sortie.sorties for c in b.commandes))
            self.assertEqual(self.infra.depot.dernier_numero,avant)
            self.avancer(250)
            _,bid,ask,_=self.sdk.ticks['EURUSD.micro'][-1]
            self.sdk.ajouter_tick('EURUSD.micro',self.temps,bid,ask)
            s.iterer()
            self.assertFalse(p.positions_ouvertes);self.assertTrue(p.trades)
            self.assertIn('STOCKAGE_INDISPONIBLE',str(alerte.write.call_args_list))
        self.infra.depot.connexion.execute('PRAGMA query_only=OFF')
        self.avancer(1000);s.iterer()
        rapport=rapporter_incident(C,s.boucle.archive_incident())
        self.assertEqual(rapport['statut'],'IDENTIQUE')
        self.assertEqual(rapport['decisions'],sum(len(x.enregistrements) for x in s.sorties))
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
