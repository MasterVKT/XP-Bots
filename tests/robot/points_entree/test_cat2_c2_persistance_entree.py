"""C08 et le transport réel, observés aux frontières SQLite et faux SDK."""
from threading import Event
from unittest.mock import patch
import unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.scenario_london_direct import ScenarioLondonDirect
from robot.outils.orchestration import C
from robot.outils.faux_mt5 import OrderSendResult
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.orchestration.c3_codec import deserialiser_valeur
from xpbots.app.c1e_cli_rapports import rapporter_incident
from xpbots.app.c1a_livre_papier import TYPES_PAPIER
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.orchestration.c3_codec import serialiser_valeur


class TestPersistanceAvantEntree(HarnaisDirect,unittest.TestCase):
    def test_double_commit_natif_et_reprise_accuse_inconnu_sans_renvoi(self):
        s=ScenarioLondonDirect(self,'DEMO');commits=[];constats=[];appele=Event()
        original=DepotSQLite.persister
        def persister(db,n,t,etat,**k):
            r=original(db,n,t,etat,**k)
            d=deserialiser_valeur(etat)
            commits.append((n,tuple(k['intentions']),d['courtier']['execution']['registre']))
            return r
        def timeout(requete):
            # Le worker est une frontière externe : il observe le dernier COMMIT
            # déjà effectué, puis rend un accusé ambigu explicite.
            constats.append(tuple(commits));appele.set()
            return OrderSendResult(retcode=self.sdk.TRADE_RETCODE_TIMEOUT,order=0)
        self.sdk.scenarios['order_send'].append(timeout)
        with patch.object(DepotSQLite,'persister',autospec=True,side_effect=persister):
            s.jusqua(s.debut+15*60000)
        self.assertTrue(appele.wait(2),'aucune vraie commande London transmise au faux SDK')
        observations=constats[0];dernier=observations[-1]
        preparees=[r for r in dernier[2] if r['statut']=='PREPAREE']
        self.assertEqual(len(preparees),1)
        self.assertTrue(dernier[1])
        self.assertTrue(any(ints and not registre for _,ints,registre in observations[:-1]))
        s.iterer();self.assertTrue(self.infra.fermer(1000))
        b=self.nouveau(sdk=self.sdk,document=s.registre,qualification=s.q,table=s.table)
        self.assertEqual(self.infra.courtier.execution.exporter_etat()['registre'][0]['statut'],'INCONNUE')
        b.iterer()
        self.assertEqual(sum(n=='order_send' for n,*_ in self.sdk.appels),1)
        self.assertEqual(rapporter_incident(C,b.archive_incident())['statut'],'IDENTIQUE')
        d=deserialiser_valeur(b.archive_incident(),types_supplementaires=TYPES_PAPIER)
        self.assertEqual(len(d['session']['reprises']),1)
        del d['session']['reprises']
        sans=serialiser_valeur(d,types_supplementaires=TYPES_PAPIER)
        with self.assertRaisesRegex(ErreurApplication,'REJEU_INCIDENT_DIVERGENT'):
            rapporter_incident(C,sans)

    def test_second_commit_en_echec_n_autorise_pas_le_worker_et_reprise_prudente(self):
        s=ScenarioLondonDirect(self,'DEMO');original=DepotSQLite.persister;refus=[]
        def persister(db,n,t,etat,**k):
            d=deserialiser_valeur(etat)
            if not refus and any(r['statut']=='PREPAREE' for r in d['courtier']['execution']['registre']):
                refus.append(n);db.connexion.execute('PRAGMA query_only=ON')
            return original(db,n,t,etat,**k)
        with patch.object(DepotSQLite,'persister',autospec=True,side_effect=persister),patch('sys.stderr'):
            s.jusqua(s.debut+15*60000)
        self.assertTrue(refus)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
        self.infra.depot.connexion.execute('PRAGMA query_only=OFF')
        self.avancer(1);s.iterer()
        self.assertTrue(self.infra.fermer(1000))
        b=self.nouveau(sdk=self.sdk,document=s.registre,qualification=s.q,table=s.table)
        self.assertEqual(self.infra.courtier.execution.exporter_etat()['registre'][0]['statut'],'INCONNUE')
        b.iterer()
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_delai_reel_du_commit_expire_le_signal_avant_confirmation(self):
        s=ScenarioLondonDirect(self);original=DepotSQLite.persister;retards=[]
        def persister(db,n,t,etat,**k):
            r=original(db,n,t,etat,**k)
            if not retards and k['reservations']:
                retards.append(n);self.avancer(int(C.technique.commun.entry_signal_ttl_seconds*1000))
            return r
        with patch.object(DepotSQLite,'persister',autospec=True,side_effect=persister):
            s.jusqua(s.debut+15*60000)
        self.assertTrue(retards)
        self.assertFalse(s.boucle.livres['REFERENCE'].premiers_remplissages)
        commandes=[c for sortie in s.sorties for _,b in sortie.sorties for c in b.commandes]
        self.assertFalse(any(c.nature.value=='ENTREE' for c in commandes))
        self.assertEqual(rapporter_incident(C,s.boucle.archive_incident())['statut'],'IDENTIQUE')
