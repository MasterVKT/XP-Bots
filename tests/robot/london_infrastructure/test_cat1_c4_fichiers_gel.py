"""Octets physiques bornés et gel recomputé, sans import du SDK."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from xpbots.infra.c0a_types import ErreurInfra
from xpbots.infra.c4_assemblage import lire_fichier,empreinte_robot


class HarnaisGel:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.r=Path(self.temp.name)/'robot';self.r.mkdir()
        self.fichiers=('src/xpbots/main.py','mql5/Services/Export.mq5','config/fixe.json',
                       'schemas/contrat.json','prompts/prompts.json')
        for n in self.fichiers:
            p=self.r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{}\n')


class TestFichiersEtGel(HarnaisGel,unittest.TestCase):
    def test_octets_exacts_et_borne_incluse(self):
        p=self.r/'config/fixe.json'
        self.assertEqual(lire_fichier(p,3),b'{}\n')
        with self.assertRaisesRegex(ErreurInfra,'LECTURE_FICHIER'):lire_fichier(p,2)

    def test_env_et_sortie_de_racine_refuses_avant_le_lecteur(self):
        with patch('xpbots.infra.c4_assemblage._fichiers.lire_octets',side_effect=AssertionError('LECTURE_INTERDITE')) as lire:
            for nom in ('.env','.env.local','.ENV.JSON'):
                with self.assertRaisesRegex(ErreurInfra,'ENV_INTERDIT'):lire_fichier(self.r/nom,100)
            with self.assertRaisesRegex(ErreurInfra,'HORS_RACINE'):
                lire_fichier(self.r/'..'/'hors.json',100,racine=self.r)
            lire.assert_not_called()

    def test_plafond_total_et_racine_complete_exiges(self):
        with self.assertRaises(ErreurInfra):empreinte_robot(self.r,14)
        with self.assertRaises(ErreurInfra):empreinte_robot(self.r,True)
        (self.r/'prompts/prompts.json').unlink()
        with self.assertRaisesRegex(ErreurInfra,'INCOMPLETE'):empreinte_robot(self.r,100)

    def test_source_env_json_n_est_jamais_lue(self):
        p=self.r/'config/.env.json';p.write_bytes(b'SENTINELLE_SYNTHETIQUE_JAMAIS_LUE')
        with self.assertRaisesRegex(ErreurInfra,'ENV_INTERDIT'):empreinte_robot(self.r,1000)
