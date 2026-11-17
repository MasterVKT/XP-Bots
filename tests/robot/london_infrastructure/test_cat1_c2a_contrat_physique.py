"""Confrontation C04 au poste qualifié ; jamais un envoi d'ordre."""
from pathlib import Path
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument


class TestContratSpecificationsPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_profils_du_compte_et_symboles_lies_concordent_aux_preuves(self):
        r=registre_contrat();i=r['ingenierie']
        with sdk_contrat() as sdk:
            session=SessionMT5(sdk,'DEMO',common_files_attendu=r['common_files'])
            try:
                session.attacher()
                specs=SpecificationsMT5(session,configuration().commun,TableHeureServeur.depuis_document(r['table_heure_serveur']),
                    r['qualification_mt5'],r['liaisons'],seances_max_age_ms=i['seances_max_age_ms'],
                    fermetures_max_age_ms=i['fermetures_max_age_ms'],max_jours_horaires=i['max_jours_horaires'],
                    ecart_horloges_max_ms=i['ecart_horloges_max_ms'])
                racine=Path(session.etat.common_files)/'XPBots'/'export'/'v1'
                seances={b:(racine/('seances_'+b+'.json')).read_bytes() for b in r['liaisons'].values()}
                fermetures=(racine/'fermetures_exceptionnelles.json').read_bytes()
                t=HorlogeSysteme().utc_ms()
                specs.recevoir_exports(t,seances=seances,fermetures=fermetures)
                self.assertFalse(specs.erreurs_exports)
                compte=specs.compte(t);self.assertIsInstance(compte,ProfilCompte)
                self.assertEqual(compte.serveur,r['qualification_mt5']['compte']['serveur'])
                for symbole,courtier in r['liaisons'].items():
                    profil=specs.instrument(symbole,t);self.assertIsInstance(profil,ProfilInstrument)
                    self.assertEqual(profil.symbole_courtier,courtier)
                    self.assertGreater(profil.volume_min,0);self.assertGreater(profil.tick_size,0)
                    self.assertEqual(profil.volume_min%profil.volume_pas,0)
            finally:session.fermer()
