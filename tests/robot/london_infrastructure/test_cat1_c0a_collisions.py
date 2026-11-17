"""Contrat 0a : un champ d'une ligne structuree prime son attribut homonyme."""
from collections import namedtuple
import unittest
import numpy as np
from xpbots.infra.c0a_types import champ_natif,entier_natif,ErreurInfra


class TestChampsStructures(unittest.TestCase):
    def test_flags_size_dtype_natifs_ne_sont_pas_les_attributs_numpy(self):
        ligne=np.array([(6,12,23)],dtype=[('flags','u4'),('size','i8'),('dtype','i8')])[0]
        self.assertEqual(entier_natif(champ_natif(ligne,'flags')),6)
        self.assertEqual(entier_natif(champ_natif(ligne,'size')),12)
        self.assertEqual(entier_natif(champ_natif(ligne,'dtype')),23)
        with self.assertRaises(ErreurInfra):champ_natif(ligne,'inexistant')
        native=namedtuple('TickNatif','flags bid')(6,1.1)
        self.assertEqual(champ_natif(native,'flags'),6)
