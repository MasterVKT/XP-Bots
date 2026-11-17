"""Contrat du poste sans ordre : ressources temporaires et lecture native."""
from tempfile import TemporaryDirectory
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from robot.outils.configuration import configuration_figee
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c4_assemblage import InfrastructurePhysique


class TestContratAssemblagePoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_ressources_et_courtier_en_paper_sur_le_seul_compte_demo(self):
        r=registre_contrat();i=r['ingenierie'];cfg=configuration_figee()
        meta=dict(deploiement='CONTRAT_13_1',mode='PAPER',empreintes={
            'technique':cfg.technique.empreinte_canonique,'ia':cfg.ia.empreinte_canonique},commit=r['commit'])
        with TemporaryDirectory() as dossier,sdk_contrat() as sdk:
            infra=InfrastructurePhysique(cfg.technique.commun,meta,r['liaisons'],racine=dossier,
                max_octets_echange=i['max_octets_echange'],snapshot_max_octets=cfg.ia.parametres['snapshot_max_bytes'],sdk=sdk)
            try:
                options=dict(departs_ticks_utc_ms=r['departs_ticks_utc_ms'],depuis_historique_compte_utc_ms=r['depuis_historique_compte_utc_ms'],
                    seances_max_age_ms=i['seances_max_age_ms'],fermetures_max_age_ms=i['fermetures_max_age_ms'],max_jours_horaires=i['max_jours_horaires'],
                    ecart_horloges_max_ms=i['ecart_horloges_max_ms'],taille_lot=i['taille_lot_ticks'],max_ticks_lot=i['max_ticks_lot'],
                    longueur_empreinte=i['longueur_empreinte'],max_taches_natives=i['max_taches_natives'])
                c=infra.initialiser_courtier(TableHeureServeur.depuis_document(r['table_heure_serveur']),r['qualification_mt5'],options)
                fichiers=infra.lire_controles();t=max(v.instant_ms for v in fichiers)
                c.recevoir_exports(t,seances={r['liaisons'][v.symbole]:v.octets for v in fichiers if v.nature=='SEANCES'},
                    fermetures=next(v.octets for v in fichiers if v.nature=='FERMETURES'))
                self.assertFalse(c.specifications.erreurs_exports)
                self.assertIsNotNone(c.observer().observation)
                self.assertTrue(infra.fermer(i['attente_arret_native_ms']))
            finally:infra.fermer(i['attente_arret_native_ms'])
