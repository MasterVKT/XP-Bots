"""Marge Forex en devise de base, sans conversion implicite des frais."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import cas_simulateur
from robot.outils.orchestration import C
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission,ErreurRejeu
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1b_simulateur import SimulateurExecution
from xpbots.noyau.c1c_domaine import Sens


class TestMargeForex(unittest.TestCase):
    def construire(self,profil):
        _,e,_=cas_simulateur()
        c=ConditionContrat(e.creation_ms,e.creation_ms+86400000,e.creation_ms,profil,
                           TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0)))
        return SimulateurExecution(C,(c,),e.creation_ms,charger_protocole(C).scenario('REFERENCE'))

    def test_devise_de_base_convertie_au_prix_sans_modifier_le_profil(self):
        b,_,_=cas_simulateur();p=replace(b.profil,devise_marge=b.profil.devise_base)
        e=self.construire(p);e.avancer_au(b.signal.cloture_ms)
        self.assertEqual(e.specifications(p.symbole),p)
        for sens in (Sens.ACHAT,Sens.VENTE):
            self.assertEqual(e.marge(p,sens,D('.2'),D('1.1')),D('2.2'))

    def test_autre_devise_ou_mode_et_frais_non_usd_refuses(self):
        b,_,_=cas_simulateur()
        profils=(replace(b.profil,devise_marge='JPY'),
                 replace(b.profil,devise_marge=b.profil.devise_base,mode_calcul='FUTURES'),
                 replace(b.profil,devise_frais=b.profil.devise_base))
        for p in profils:
            with self.subTest(p=p),self.assertRaises(ErreurRejeu):self.construire(p)
