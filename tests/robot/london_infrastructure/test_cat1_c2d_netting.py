"""Exclusivite native actuelle, jamais reconstruite par le seul magic."""
from pathlib import Path
import unittest
from robot.london_infrastructure.test_cat1_c2d_transport import HarnaisTransport
from robot.outils.qualification_mt5 import T,preuve_qualification
from robot.outils.faux_mt5 import FauxMT5
from xpbots.execution.c4_cycle import CommandeExecution,NatureCommande,StatutAccuse


class TestNettingNatif(HarnaisTransport,unittest.TestCase):
    def options_frontiere(self):
        sdk=FauxMT5(Path(self.temp.name).resolve(),instant_ms=T)
        sdk.compte=sdk.compte._replace(margin_mode=sdk.ACCOUNT_MARGIN_MODE_RETAIL_NETTING)
        q=preuve_qualification(sdk);q['compte'].update(mode_marge='NETTING',exclusivites_netting=['EURUSD'])
        return dict(mode='DEMO',sdk=sdk,qualification=q)

    def test_compte_netting_vide_conserve_l_exclusivite_qualifiee_pour_la_premiere_entree(self):
        r=self.transport.observer()
        self.assertIsNotNone(r.observation,r.alertes)
        self.assertEqual(r.observation.exclusivites,('EURUSD',))

    def test_contribution_etrangere_retire_la_propriete_meme_magic_de_position(self):
        self.autoriser();self.attendre();r=self.transport.observer()
        self.assertIsNotNone(r.observation,r.alertes);p=self.sdk.positions[0]
        self.assertTrue(r.observation.positions[0].origine_exclusive)
        self.sdk.transactions.append(self.sdk.transactions[0]._replace(ticket=999,order=999,magic=0,comment='tiers'))
        self.sdk.positions[0]=p._replace(volume=2*p.volume)
        r=self.transport.observer();self.assertIsNotNone(r.observation,r.alertes)
        self.assertFalse(r.observation.positions[0].origine_exclusive)
        self.assertIsNone(self.transport.proprietaire(str(p.ticket)))
        self.assertEqual(r.observation.exclusivites,())

    def test_reprise_exige_rapprochement_courant_avant_defense_netting(self):
        self.autoriser();self.attendre();r=self.transport.observer();p=r.observation.positions[0]
        reprise=self.nouveau(self.transport.exporter_etat());self.addCleanup(lambda:reprise.fermer(1000))
        defense=CommandeExecution(NatureCommande.TP,self.commande.cle,'tp-avant',T,dict(ticket=p.ticket,sl=p.sl,tp=p.tp))
        reprise.soumettre_defenses((defense,),T)
        for _ in range(2000):
            r=reprise.collecter()
            if r.reponses:break
            from threading import Event
            Event().wait(.001)
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.REFUSE)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),1)
        self.assertIsNotNone(reprise.observer().observation)
        from dataclasses import replace
        reprise.soumettre_defenses((replace(defense,reference='tp-apres'),),T)
        for _ in range(2000):
            r=reprise.collecter()
            if r.reponses:break
            from threading import Event
            Event().wait(.001)
        self.assertEqual(r.reponses[0].donnees['statut'],StatutAccuse.ACCEPTE)
        self.assertEqual(sum(a[0]=='order_send' for a in self.sdk.appels),2)
