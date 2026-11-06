"""Catégorie 1, couche 1a (constructeur_bougies) : tick de frontière, intervalles vides, anomalies, reprise."""
import copy
import json
import unittest

from xpbots.donnees.c0a_types import ErreurDonneesTemps
from xpbots.donnees.c1a_constructeur import BougieBrute, ConstructeurBougies
from xpbots.noyau.c1a_marche import Tick

D = 900_000


def tick(instant, bid, numero=0, reception=None, symbole='EURUSD'):
    return Tick(symbole, symbole, instant, instant if reception is None else reception, numero, bid, bid + 0.0001)


class TestConstructeur(unittest.TestCase):
    def test_tick_de_frontiere(self):
        c = ConstructeurBougies('EURUSD', D)
        self.assertEqual(c.ajouter(tick(10, 1.0)).bougies, ())
        c.ajouter(tick(D - 1, 1.2, 1))
        c.ajouter(tick(D // 2, 0.9, 2))
        sortie = c.ajouter(tick(D, 5.0, 3, reception=D + 40))
        self.assertEqual(sortie.bougies, (BougieBrute('EURUSD', 0, D, 1.0, 1.2, 0.9, 0.9, 3, D + 40),))
        self.assertEqual(c.derniere_fin_ms, D)
        suivante = c.ajouter(tick(2 * D, 1.0, 4)).bougies[0]
        self.assertEqual((suivante.ouverture, suivante.nombre_evenements), (5.0, 1), 'le tick de frontière ouvre la suivante')

    def test_disponibilite_jamais_avant_la_fin(self):
        c = ConstructeurBougies('EURUSD', D)
        c.ajouter(tick(0, 1.0))
        self.assertEqual(c.ajouter(tick(D, 1.0, 1, reception=D - 5)).bougies[0].instant_disponibilite_ms, D)

    def test_intervalles_vides_emis_sans_prix(self):
        c = ConstructeurBougies('EURUSD', D)
        c.ajouter(tick(0, 1.0))
        bougies = c.ajouter(tick(3 * D + 7, 1.1, 1)).bougies
        self.assertEqual([(b.debut_ms, b.vide) for b in bougies], [(0, False), (D, True), (2 * D, True)])
        self.assertTrue(all(b.ouverture is None and b.instant_disponibilite_ms == 3 * D + 7 for b in bougies[1:]))

    def test_tick_anterieur_ignore_et_signale(self):
        c = ConstructeurBougies('EURUSD', D)
        c.ajouter(tick(D + 5, 1.0))
        sortie = c.ajouter(tick(D - 1, 9.0, 1))
        self.assertEqual((sortie.bougies, sortie.anomalie.raison), ((), 'TICK_ANTERIEUR'))
        self.assertEqual(c.ajouter(tick(2 * D, 1.0, 2)).bougies[0].haut, 1.0, 'tick antérieur non agrégé')

    def test_reprise_depuis_une_borne(self):
        c = ConstructeurBougies('EURUSD', D, debut_ms=2 * D)
        self.assertEqual(c.derniere_fin_ms, 2 * D)
        self.assertEqual(c.ajouter(tick(2 * D - 1, 1.0)).anomalie.raison, 'TICK_ANTERIEUR')
        bougies = c.ajouter(tick(4 * D, 1.0, 1)).bougies
        self.assertEqual([(b.debut_ms, b.vide) for b in bougies], [(2 * D, True), (3 * D, True)])

    def test_export_import_identiques_a_un_traitement_continu(self):
        ticks = [tick(i * 97_003, 1.1 + 0.0001 * (i % 13), i) for i in range(60)]
        for coupure in (0, 1, 9, 10, 31):
            continu, coupe = ConstructeurBougies('EURUSD', D), ConstructeurBougies('EURUSD', D)
            for t in ticks[:coupure]:
                continu.ajouter(t)
                coupe.ajouter(t)
            export = json.loads(json.dumps(coupe.exporter(), allow_nan=False))
            reprise = ConstructeurBougies.importer(export)
            with self.subTest(coupure=coupure):
                self.assertEqual([reprise.ajouter(t) for t in ticks[coupure:]], [continu.ajouter(t) for t in ticks[coupure:]])
                self.assertEqual(reprise.exporter(), continu.exporter())

    def test_import_refuse(self):
        c = ConstructeurBougies('EURUSD', D)
        c.ajouter(tick(D, 1.1))
        c.ajouter(tick(2 * D + 3, 1.2, 1))
        export = c.exporter()
        self.assertIsNotNone(export['ouverte'])
        alterations = [('schema', 'autre'), ('duree_ms', 0), ('derniere_fin_ms', 5), ('derniere_fin_ms', 3 * D),
                       ('symbole', ''), ('ouverte', {'debut_ms': 2 * D})]
        alterations += [(('ouverte', cle), valeur) for cle, valeur in (('nombre', 0), ('haut', 1.0), ('bas', float('nan')),
                                                                      ('debut_ms', 2 * D + 1), ('debut_ms', -D),
                                                                      ('cloture', True))]
        for cle, valeur in alterations:
            altere = copy.deepcopy(export)
            if isinstance(cle, tuple):
                altere[cle[0]][cle[1]] = valeur
            else:
                altere[cle] = valeur
            with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ErreurDonneesTemps):
                ConstructeurBougies.importer(altere)
        incomplet = dict(export)
        del incomplet['ouverte']
        for donnees in (incomplet, 'etat', None):
            with self.subTest(donnees=donnees), self.assertRaises(ErreurDonneesTemps):
                ConstructeurBougies.importer(donnees)

    def test_refus(self):
        with self.assertRaises(ErreurDonneesTemps):
            ConstructeurBougies('EURUSD', D).ajouter(tick(0, 1.0, symbole='GBPUSD'))
        for arguments in (('EURUSD', 0), ('EURUSD', D, 5), ('', D)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                ConstructeurBougies(*arguments)
        for arguments in (('EURUSD', 1, D, 1.0, 1.0, 1.0, 1.0, 1, D), ('EURUSD', 0, D, 1.0, None, None, None, 0, D),
                          ('EURUSD', 0, D, 1.0, 0.9, 1.0, 1.0, 1, D), ('EURUSD', 0, D, None, None, None, None, 0, D - 1)):
            with self.subTest(arguments=arguments), self.assertRaises(ErreurDonneesTemps):
                BougieBrute(*arguments)


if __name__ == '__main__':
    unittest.main()
