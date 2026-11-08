"""S5 parle les commandes C08 réelles ; prochains ticks et prix exécutables."""
from decimal import Decimal as D
from dataclasses import replace
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.cycle_execution import bloc_cycle
from xpbots.execution.c4_cycle import CommandeExecution,NatureCommande,NatureReponse,StatutAccuse
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1c_domaine import CauseCloture,Sens
from xpbots.rejeu.squelette import ExecutionPapierMinimale

def preparer(sens=Sens.ACHAT):
    from robot.outils.execution_partagee import signal
    b=bloc_cycle(signal_=signal(sens=sens))
    t=b.signal.cloture_ms
    e=ExecutionPapierMinimale(configuration_figee(),{b.signal.symbole:b.profil},t//86400000*86400000)
    e.avancer_au(t)
    c=b.cycle.preparer_envoi(t).commandes[0]
    return b,e,c
def tick(b,t,bid='1.1',ask='1.1001'):
    return Tick(b.signal.symbole,b.profil.symbole_courtier,t,t,t,float(bid),float(ask))
class TestExecutionPapier(unittest.TestCase):
    def test_entree_au_tick_suivant_achat_ask_vente_bid(self):
        for sens,prix in ((Sens.ACHAT,D('1.1001')),(Sens.VENTE,D('1.1'))):
            b,e,c=preparer(sens);t=b.signal.cloture_ms
            ack=e.soumettre((c,))[0]
            self.assertEqual(ack.donnees['statut'],StatutAccuse.ACCEPTE)
            self.assertFalse(e.positions_ouvertes)
            fill=e.sur_tick(tick(b,t+1))[0]
            self.assertIs(fill.nature,NatureReponse.REMPLISSAGE)
            self.assertEqual(fill.donnees['prix_moyen'],prix)
            self.assertEqual(fill.donnees['sl'],c.donnees['sl'])
    def test_protections_sur_bid_pour_achat_et_ask_pour_vente(self):
        for sens,bid,ask,cause,prix in ((Sens.ACHAT,'1.09','1.1',CauseCloture.STOP_LOSS,'1.09'),
                (Sens.VENTE,'1.1','1.11',CauseCloture.STOP_LOSS,'1.11'),
                (Sens.ACHAT,'1.2','1.21',CauseCloture.TAKE_PROFIT,'1.2'),
                (Sens.VENTE,'1.0','1.01',CauseCloture.TAKE_PROFIT,'1.01')):
            b,e,c=preparer(sens);t=b.signal.cloture_ms;e.soumettre((c,));e.sur_tick(tick(b,t+1))
            r=e.sur_tick(tick(b,t+2,bid,ask))[0]
            self.assertEqual((r.donnees['cause'],r.donnees['prix']),(cause,D(prix)))
            self.assertFalse(e.positions_ouvertes)
    def test_deduplication_commandes_et_reponses_natives(self):
        b,e,c=preparer();t=b.signal.cloture_ms
        self.assertEqual(len(e.soumettre((c,c))),1)
        self.assertEqual(len(e.sur_tick(tick(b,t+1))),1)
        self.assertEqual(e.soumettre((c,)),())
        self.assertEqual(len(e.observation().positions),1)
        self.assertEqual(len(e.observation().reponses),2)
    def test_cloture_native_et_solde(self):
        b,e,c=preparer();t=b.signal.cloture_ms;e.soumettre((c,));fill=e.sur_tick(tick(b,t+1))[0]
        b.cycle.sur_reponse(fill)
        close=b.cycle.demander_cloture(t+2,CauseCloture.DUREE_MAXIMALE,peut_envoyer=True).commandes[0]
        e.avancer_au(t+2);e.soumettre((close,))
        self.assertTrue(e.positions_ouvertes)
        r=e.sur_tick(tick(b,t+3,'1.101','1.1011'))[0]
        self.assertIs(r.nature,NatureReponse.CLOTURE)
        self.assertEqual(r.donnees['prix'],D('1.101'))
        self.assertGreater(e.etat_compte().solde,D(100))
        self.assertFalse(e.positions_ouvertes)
    def test_sl_natif_prioritaire_sur_cloture_en_attente(self):
        b,e,c=preparer();t=b.signal.cloture_ms;e.soumettre((c,));fill=e.sur_tick(tick(b,t+1))[0]
        b.cycle.sur_reponse(fill)
        close=b.cycle.demander_cloture(t+2,CauseCloture.DUREE_MAXIMALE,peut_envoyer=True).commandes[0]
        e.avancer_au(t+2);e.soumettre((close,))
        reponses=e.sur_tick(tick(b,t+3,'1.09','1.0901'))
        self.assertEqual(len(reponses),1)
        self.assertEqual(reponses[0].donnees['cause'],CauseCloture.STOP_LOSS)
        self.assertFalse(e.observation().ordres)
    def test_horloge_et_type_refuses(self):
        b,e,c=preparer()
        with self.assertRaises(TypeError): e.soumettre(('ordre',))
        with self.assertRaises(ValueError): e.avancer_au(b.signal.cloture_ms-1)
        e.sur_tick(tick(b,b.signal.cloture_ms+1))
        with self.assertRaises(ValueError): e.sur_tick(tick(b,b.signal.cloture_ms+1))
