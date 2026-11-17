"""Concordance au calcul natif composé, profil MT5 conservé sans altération."""
from decimal import Decimal as D
import unittest
from robot.london_infrastructure.test_cat1_c3_courtier import HarnaisCourtier
from robot.outils.orchestration import C
from robot.outils.qualification_mt5 import T,JOUR
from xpbots.noyau.c1c_domaine import Sens
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1b_simulateur import SimulateurExecution


class TestJonctionMargeForex(HarnaisCourtier,unittest.TestCase):
    def test_profil_reel_eurusd_et_marge_du_port_natif_achat_vente(self):
        self.exports();p=self.courtier.calculs.specifications('EURUSD')
        self.assertEqual((p.mode_calcul,p.devise_marge,p.devise_cotation),('FOREX','EUR','USD'))
        creation=T//JOUR*JOUR
        e=SimulateurExecution(C,(ConditionContrat(creation,T+JOUR,T,p,
            TarifCommission('PREUVE_C04_FIXTURE',D(0),D(0),D(0),D(0))),),creation,
            charger_protocole(C).scenario('REFERENCE'))
        e.avancer_au(T)
        for sens in (Sens.ACHAT,Sens.VENTE):
            self.assertAlmostEqual(e.marge(p,sens,D('.2'),D('1.1')),
                self.courtier.calculs.marge(p,sens,D('.2'),D('1.1')),places=9)
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))
