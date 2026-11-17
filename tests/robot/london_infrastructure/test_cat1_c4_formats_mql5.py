"""Fixtures D12 synthetiques : consommateurs reels, sans pretendre compiler MQL5."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from robot.outils.qualification_mt5 import T,JOUR,frontiere,natif,octets
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.fondamental.c0_types import TableImportance
from xpbots.fondamental.c1b_annonces import GardeAnnonces

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures'/'mql5_exports'


class TestFormatsExportsMQL5(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        table=TableHeureServeur.depuis_document(self.document('heure_serveur.json'))
        self.sdk,self.session,self.specs=frontiere(self.temp.name,table=table)
        self.addCleanup(self.session.fermer)
        self.commun=configuration().commun
        self.importance=TableImportance('MQL5_FIXTURE','FIXTURE_V1',('CALENDAR_IMPORTANCE_HIGH',))

    def document(self,nom):return json.loads((FIXTURES/nom).read_text(encoding='utf-8'))
    def octets(self,nom):return (FIXTURES/nom).read_bytes()
    def garde(self):return GardeAnnonces(self.commun,self.specs.convertir_serveur)

    def test_seances_native_une_heure_davance_et_fermeture_reduite(self):
        r=self.specs.recevoir_exports(T,seances={'EURUSD.micro':self.octets('seances_EURUSD.micro.json')},
            fermetures=self.octets('fermetures_exceptionnelles.json'))
        self.assertEqual(len(r),2)
        h=self.specs.instrument('EURUSD',T).horaires
        self.assertTrue(h.ouvert_a(T));self.assertEqual(h.prochaine_fermeture_apres(T),T+1800000)
        self.assertFalse(h.ouvert_a(T+1800000));self.assertTrue(h.ouvert_a(T+3600000))
        self.assertEqual(self.specs.convertir_serveur('2026.11.10 10:00:00'),T)

    def test_horizon_complet_reste_valide_entre_exports_et_ne_renouvelle_pas_age(self):
        g=self.garde();b=self.octets('calendrier_v1.json')
        self.assertTrue(g.recevoir(b,T,self.importance).acceptee)
        self.assertTrue(g.evaluer('EURUSD',T+1000).admise)
        self.assertFalse(g.recevoir(b,T+1000,self.importance).acceptee)
        fin=T+int(self.commun.news_calendar_max_age_seconds*1000)+1
        self.assertEqual(g.evaluer('EURUSD',fin).detail,'CALENDRIER_PERIME')

    def test_horizon_minimal_a_l_export_seul_est_insuffisant_une_seconde_apres(self):
        cal=self.document('calendrier_v1.json')
        cal['fenetre_fin_serveur']=natif(T+int(self.commun.news_forward_coverage_seconds*1000)+3600000)
        g=self.garde();self.assertTrue(g.recevoir(octets(cal),T,self.importance).acceptee)
        self.assertTrue(g.evaluer('EURUSD',T).admise)
        self.assertEqual(g.evaluer('EURUSD',T+1000).detail,'COUVERTURE_INSUFFISANTE')

    def test_annonce_nouvelle_n_est_connue_qu_a_la_reception_et_fenetre_fin_exclusive(self):
        g=self.garde();self.assertTrue(g.recevoir(self.octets('calendrier_v1.json'),T,self.importance).acceptee)
        self.assertTrue(g.recevoir(self.octets('calendrier_v2.json'),T+1000,self.importance).acceptee)
        self.assertTrue(g.evaluer('EURUSD',T).admise)
        self.assertTrue(g.evaluer('EURUSD',T+1000).cloture_obligatoire)
        annonce=T+int(self.commun.news_before_seconds*1000)
        fin=annonce+int(self.commun.news_after_seconds*1000)
        self.assertFalse(g.evaluer('EURUSD',fin-1).admise)
        self.assertTrue(g.evaluer('EURUSD',fin).admise)
        # Le nom UTF8 de la fixture traverse la meme lecture que le terminal.
        self.assertIn('sans valeur',self.document('calendrier_v2.json')['evenements'][0]['nom'])
