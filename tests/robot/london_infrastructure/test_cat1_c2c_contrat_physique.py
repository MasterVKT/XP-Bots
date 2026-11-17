"""Confronter les calculs au SDK du poste, sans envoyer le moindre ordre."""
import unittest
from decimal import Decimal
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2c_calculs import CalculsMT5
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument
from xpbots.noyau.c1c_domaine import Sens
from pathlib import Path


class TestContratCalculPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_profit_marge_et_positions_en_lecture_seule(self):
        r=registre_contrat();i=r['ingenierie']
        with sdk_contrat() as sdk:
            s=SessionMT5(sdk,'DEMO')
            try:
                s.attacher();t=HorlogeSysteme().utc_ms()
                specs=SpecificationsMT5(s,configuration().commun,TableHeureServeur.depuis_document(r['table_heure_serveur']),
                    r['qualification_mt5'],r['liaisons'],seances_max_age_ms=i['seances_max_age_ms'],
                    fermetures_max_age_ms=i['fermetures_max_age_ms'],max_jours_horaires=i['max_jours_horaires'],ecart_horloges_max_ms=i['ecart_horloges_max_ms'])
                racine=Path(s.etat.common_files)/'XPBots'/'export'/'v1'
                specs.recevoir_exports(t,seances={b:(racine/('seances_'+b+'.json')).read_bytes() for b in r['liaisons'].values()},
                    fermetures=(racine/'fermetures_exceptionnelles.json').read_bytes())
                self.assertFalse(specs.erreurs_exports)
                port=CalculsMT5(s,configuration().commun,r['liaisons'],t,profil=specs.instrument,
                    qualification_compte=specs.compte,proprietaire=lambda ticket:None,flux_externe=lambda t,solde:True,
                    assiette_stop_out=r['qualification_mt5']['compte']['assiette_stop_out'])
                compte=port.etat_compte();n=sdk.account_info();self.assertIsNotNone(n)
                self.assertEqual(compte.fonds_propres,Decimal(str(n.equity)))
                self.assertEqual(len(compte.positions),len(sdk.positions_get()))
                for canonique,courtier in r['liaisons'].items():
                    p=specs.instrument(canonique,t);self.assertIsInstance(p,ProfilInstrument)
                    q=sdk.symbol_info_tick(courtier);self.assertIsNotNone(q)
                    entree=Decimal(str(q.ask));sortie=entree+p.tick_size
                    profit=sdk.order_calc_profit(sdk.ORDER_TYPE_BUY,courtier,float(p.volume_min),float(entree),float(sortie))
                    marge=sdk.order_calc_margin(sdk.ORDER_TYPE_BUY,courtier,float(p.volume_min),float(entree))
                    self.assertEqual(port.profit(p,Sens.ACHAT,p.volume_min,entree,sortie),Decimal(str(profit)))
                    self.assertEqual(port.marge(p,Sens.ACHAT,p.volume_min,entree),Decimal(str(marge)))
            finally:s.fermer()
