"""Cadence, horodatage, stockage et gardes du cycle par ses ports publics."""
from pathlib import Path
from unittest.mock import patch
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.qualification_mt5 import T
from robot.outils.orchestration import C
from xpbots.app.c1e_cli_rapports import rapporter_incident
from xpbots.infra.c0a_types import ErreurInfra
from robot.outils.faux_mt5 import FauxMT5


class TestBoucleDirecte(HarnaisDirect,unittest.TestCase):
    def test_type_de_compte_reel_refuse_au_demarrage_demo(self):
        sdk=FauxMT5(self.commun,instant_ms=self.temps)
        sdk.compte=sdk.compte._replace(trade_mode=sdk.ACCOUNT_TRADE_MODE_REAL)
        with self.assertRaisesRegex(ErreurInfra,'type de compte incompatible'):
            self.nouveau('DEMO',sdk=sdk)
        self.assertFalse(sdk.attache)
        self.assertFalse(any(n=='order_send' for n,*_ in sdk.appels))

    def test_cadences_controles_snapshot_et_minuterie_sur_horloge_externe(self):
        b=self.nouveau('PAPER_AB');original=Path.open;lectures=[]
        def ouvrir(p,*a,**k):
            f=original(p,*a,**k)
            if 'r' in (a[0] if a else k.get('mode','r')):lectures.append((p.name,self.temps))
            return f
        # L'absence du snapshot doit rester NEUTRAL ; le lecteur ouvre deux fois.
        snapshot=self.commun/'Files/XPBots/ai/v1/context_latest.json'
        snapshot.parent.mkdir(parents=True);snapshot.write_bytes(b'{}')
        with patch.object(Path,'open',autospec=True,side_effect=ouvrir),patch('sys.stderr'):
            b.executer(max_iterations=11)
        for nom in ('permission_EURUSD.json','calendrier.json','context_latest.json'):
            self.assertEqual([t for n,t in lectures if n==nom],[T,T+1000])
        self.assertEqual(self.attentes,[.1]*10)
        # Les faits MARCHE progressent aussi à chaque lecture ; ils ne sont pas
        # des réveils de la minuterie des contrôles.
        self.assertEqual([j.entree.instant_ms for j in b.moteur.entrees
            if not any(r.nature=='MARCHE' for r in j.entree.receptions)],[T,T+1000])

    def test_demarrage_paper_compte_fictif_et_cadence_registre(self):
        b=self.nouveau();r=b.executer(max_iterations=3)
        self.assertEqual(r['iterations'],3)
        self.assertEqual(self.attentes,[.1,.1])
        self.assertEqual(b.livres['REFERENCE'].etat_compte().solde,C.technique.commun.initial_equity_usd)
        self.assertEqual(r['validation_financiere'],'NON_EVALUEE')
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_receptions_fichiers_et_ticks_datees_apres_io(self):
        b=self.nouveau();original=Path.open
        def ouvrir(p,*a,**k):
            f=original(p,*a,**k)
            if 'r' in (a[0] if a else k.get('mode','r')):self.avancer(1)
            return f
        self.sdk.ajouter_tick('EURUSD.micro',T,1.1003,1.1004)
        with patch.object(Path,'open',autospec=True,side_effect=ouvrir):sorties=b.iterer()
        self.assertTrue(sorties)
        self.assertGreater(b.moteur.entrees[0].entree.instant_ms,T)
        for j in b.moteur.entrees:
            for tick in j.entree.ticks:
                self.assertEqual(tick.instant_reception_ms,j.entree.instant_ms)
                self.assertLessEqual(tick.instant_fournisseur_ms,tick.instant_reception_ms)

    def test_reponse_sql_indisponible_n_autorise_pas_d_entree_et_se_repare(self):
        b=self.nouveau();self.infra.depot.connexion.execute('PRAGMA query_only=ON')
        with patch('sys.stderr'):
            b.iterer()
        self.assertEqual(self.infra.depot.dernier_numero,0)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
        self.infra.depot.connexion.execute('PRAGMA query_only=OFF');self.avancer(1000);b.iterer()
        self.assertGreater(self.infra.depot.dernier_numero,0)
        self.assertEqual(rapporter_incident(C,b.archive_incident())['statut'],'IDENTIQUE')
