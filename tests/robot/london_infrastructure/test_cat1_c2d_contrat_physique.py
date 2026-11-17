"""Lecture seule du poste explicitement active en phase 13.1."""
from pathlib import Path
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from robot.outils.execution_partagee import configuration
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2a_specifications import SpecificationsMT5
from xpbots.infra.c2d_execution_mt5 import ExecutionMT5


class TestContratObservationPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_tickets_volume_et_protections_du_compte_demo_sans_envoi(self):
        r=registre_contrat();i=r['ingenierie'];h=HorlogeSysteme();table=TableHeureServeur.depuis_document(r['table_heure_serveur'])
        with sdk_contrat() as sdk:
            s=SessionMT5(sdk,'DEMO');transport=None
            try:
                s.attacher();t=h.utc_ms()
                specs=SpecificationsMT5(s,configuration().commun,table,r['qualification_mt5'],r['liaisons'],
                    seances_max_age_ms=i['seances_max_age_ms'],fermetures_max_age_ms=i['fermetures_max_age_ms'],
                    max_jours_horaires=i['max_jours_horaires'],ecart_horloges_max_ms=i['ecart_horloges_max_ms'])
                racine=Path(s.etat.common_files)/'XPBots'/'export'/'v1'
                specs.recevoir_exports(t,seances={b:(racine/('seances_'+b+'.json')).read_bytes() for b in r['liaisons'].values()},
                    fermetures=(racine/'fermetures_exceptionnelles.json').read_bytes())
                transport=ExecutionMT5(s,configuration().commun,table,r['liaisons'],h,profil=specs.instrument,preuve=specs.preuve,
                    qualification_compte=specs.compte,preuve_compte=specs.preuve_compte,longueur_empreinte=i['longueur_empreinte'],
                    max_taches_natives=i['max_taches_natives'],depuis_utc_ms=r['depuis_historique_compte_utc_ms'],
                    convention_ticks=specs.convention_ticks(t))
                rapport=transport.observer();self.assertIsNotNone(rapport.observation,rapport.alertes)
                native={str(p.ticket):p for p in sdk.positions_get()}
                self.assertEqual({p.ticket for p in rapport.observation.positions},set(native))
                for p in rapport.observation.positions:
                    self.assertEqual(float(p.volume),native[p.ticket].volume)
                    self.assertEqual(float(p.sl) if p.sl is not None else 0.,native[p.ticket].sl)
                    self.assertEqual(float(p.tp) if p.tp is not None else 0.,native[p.ticket].tp)
                    self.assertIsNone(transport.proprietaire(p.ticket))
            finally:
                if transport is not None:transport.fermer(i['attente_arret_native_ms'])
                s.fermer()
