"""Vrai writer atomique 4, lecteur 0d et inventaire du gel sans manifeste de données."""
from hashlib import sha256
import unittest
from robot.london_infrastructure.test_cat1_c4_fichiers_gel import HarnaisGel
from xpbots.infra.c4_assemblage import ecrire_fichier,lire_fichier,empreinte_robot


class TestJonctionFichiersGel(HarnaisGel,unittest.TestCase):
    def test_archives_physiques_empreinte_des_octets_et_non_du_json_reencode(self):
        p=self.r/'archive.json';b=b'{ "schema" : "fixture" }\n'
        ecrire_fichier(p,b)
        self.assertEqual(lire_fichier(p,len(b),racine=self.r),b)
        self.assertEqual(sha256(lire_fichier(p,len(b))).hexdigest(),sha256(b).hexdigest())
        self.assertNotEqual(sha256(b).hexdigest(),sha256(b'{"schema":"fixture"}').hexdigest())

    def test_inventaire_stable_ajout_retrait_modification_et_nom_lies_au_gel(self):
        avant=empreinte_robot(self.r,1000)
        self.assertEqual(avant,empreinte_robot(self.r,1000))
        ecrire_fichier(self.r/'gel.json',b'{"fichiers":[]}')
        self.assertEqual(avant,empreinte_robot(self.r,1000),'Le manifeste fourni ne remplace pas l inventaire réel')
        p=self.r/'src/xpbots/ajout.py';ecrire_fichier(p,b'')
        ajout=empreinte_robot(self.r,1000);self.assertNotEqual(ajout['sha256'],avant['sha256'])
        self.assertEqual(ajout['octets'],avant['octets'])
        ecrire_fichier(p,b'x=1\n',ecraser=True)
        modifie=empreinte_robot(self.r,1000);self.assertNotEqual(modifie['sha256'],ajout['sha256'])
        p.rename(p.with_name('autre.py'))
        self.assertNotEqual(empreinte_robot(self.r,1000)['sha256'],modifie['sha256'])
        p.with_name('autre.py').unlink()
        self.assertEqual(empreinte_robot(self.r,1000),avant)
