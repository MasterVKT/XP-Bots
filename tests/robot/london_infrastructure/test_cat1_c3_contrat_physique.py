"""Assemblage des adaptateurs en lecture seule, opt-in 13.1."""
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c0g_controles import SourcesControles
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c3_courtier import CourtierMT5


class TestContratCompositionPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_composition_qualifiee_et_releve_courant_sans_emission(self):
        r=registre_contrat();i=r['ingenierie'];h=HorlogeSysteme()
        with sdk_contrat() as sdk:
            s=SessionMT5(sdk,'DEMO');c=None
            try:
                s.attacher();t=h.utc_ms()
                c=CourtierMT5(s,configuration().commun,TableHeureServeur.depuis_document(r['table_heure_serveur']),r['liaisons'],h,t,
                    qualification=r['qualification_mt5'],departs_ticks_utc_ms=r['departs_ticks_utc_ms'],
                    depuis_historique_compte_utc_ms=r['depuis_historique_compte_utc_ms'],seances_max_age_ms=i['seances_max_age_ms'],
                    fermetures_max_age_ms=i['fermetures_max_age_ms'],max_jours_horaires=i['max_jours_horaires'],
                    ecart_horloges_max_ms=i['ecart_horloges_max_ms'],taille_lot=i['taille_lot_ticks'],max_ticks_lot=i['max_ticks_lot'],
                    longueur_empreinte=i['longueur_empreinte'],max_taches_natives=i['max_taches_natives'])
                fichiers=SourcesControles(s.etat.common_files,r['liaisons'],i['max_octets_echange']).lire(h.utc_ms());connu=h.utc_ms()
                c.recevoir_exports(connu,seances={r['liaisons'][v.symbole]:v.octets for v in fichiers if v.nature=='SEANCES'},
                    fermetures=next(v.octets for v in fichiers if v.nature=='FERMETURES'))
                self.assertFalse(c.specifications.erreurs_exports)
                observation=c.observer();self.assertIsNotNone(observation.observation,observation.alertes)
                self.assertIsNotNone(c.profil_compte(observation.instant_ms))
                self.assertEqual(len(observation.observation.positions),len(sdk.positions_get()))
                marche=c.lire_marche();self.assertFalse(marche.erreurs)
            finally:
                if c is not None:c.fermer(i['attente_arret_native_ms'])
                s.fermer()
