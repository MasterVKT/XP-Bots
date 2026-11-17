"""Le coordinateur reel consomme les faits de capital sans acces prive."""
from decimal import Decimal as D
import unittest
from robot.outils.coordinateur_execution import bloc_coordinateur,traiter
from robot.outils.execution_partagee import T,signal,cotation
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c1b_gardes import MouvementCompte,reconstituer_base_utc
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.noyau.c1c_domaine import Motif


class TestFluxDansCoordinateur(unittest.TestCase):
    def test_apport_et_perte_declenchent_la_vraie_garde_dans_les_deux_chemins(self):
        for observation in (False,True):
            b=bloc_coordinateur();minuit=T//86400000*86400000
            m=MouvementCompte('depot',T+1,D(100),True)
            for t,eq,ms in ((T+1,D(200),(m,)),(T+2,D(196),(m,MouvementCompte('perte',T+2,D(-4))))):
                c=EtatCompte(t,eq,eq,D(0));b.port.compte=c
                base=reconstituer_base_utc(c,ms,Intervalle(minuit,t+1),aucune_position_minuit=True)
                options=dict(observation=ObservationNative(c,minuit,True)) if observation else {}
                lot=traiter(b,t,base_utc=base,signaux=(signal(cloture_ms=t),) if t==T+2 else (),
                    cotations=(cotation(instant_fournisseur_ms=t,instant_reception_ms=t),),**options)
                self.assertEqual(lot.etat.reprise.gardes.base_quotidienne,D(200))
            self.assertEqual(lot.issues[0].motif,Motif.DAILY_LOSS_LOCK)
            self.assertFalse(lot.preparations)
