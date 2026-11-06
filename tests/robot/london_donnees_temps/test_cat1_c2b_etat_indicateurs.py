"""Catégorie 1, couche 2b (etat_indicateurs) : P-03, rangs P-10, identité du préchargement, export et import."""
import copy
import hashlib
import json
import unittest

from robot.outils.configuration import configuration_figee
from xpbots.donnees.c0a_types import ErreurDonneesTemps
from xpbots.donnees.c2b_etat_indicateurs import ChaineIndicateurs
from xpbots.noyau.c1a_marche import Bougie

D = 900_000
EMPREINTE = configuration_figee().technique.empreinte_canonique


def bougie(i, valide=True, haut=None):
    h = 1.1 + 0.001 * (i % 7) if haut is None else haut
    if not valide:
        return Bougie('EURUSD', i * D, D, None, None, None, None, 0, False, 'AUCUN_BID', (i + 1) * D)
    return Bougie('EURUSD', i * D, D, h - 0.0005, h, h - 0.001, h - 0.0002, 4, True, None, (i + 1) * D)


class TestChaine(unittest.TestCase):
    def test_p03_bougie_invalide_hors_de_la_chaine(self):
        chaine = ChaineIndicateurs(3)
        premiere = chaine.ajouter(bougie(0))
        self.assertIsNone(chaine.ajouter(bougie(1, valide=False)))
        suivante = chaine.ajouter(bougie(2, haut=1.2))
        self.assertEqual((premiere.rang, suivante.rang, chaine.nombre_valides), (0, 1, 2))
        precedente = bougie(0).cloture
        self.assertEqual(suivante.tr, max(1.2 - (1.2 - 0.001), abs(1.2 - precedente), abs(1.2 - 0.001 - precedente)),
                         'TR avec la dernière clôture valide')

    def test_rangs_p10(self):
        chaine = ChaineIndicateurs(14)
        rangs = [chaine.ajouter(bougie(i)).rang for i in range(1000)]
        self.assertEqual(rangs[-1], 999, 'au moins 1 000 M15 valides, t comprise : rang ≥ 999')

    def test_identite_du_prechargement(self):
        a, b = ChaineIndicateurs(14), ChaineIndicateurs(14)
        self.assertEqual(a.identite.empreinte, '0' * 64)
        for i in range(20):
            a.ajouter(bougie(i))
        for i in range(1, 21):
            b.ajouter(bougie(i))
        self.assertEqual((a.identite.premiere_ms, a.identite.nombre), (0, 20))
        self.assertNotEqual(a.identite, b.identite, 'préchargement différent : initialisation différente')
        c = ChaineIndicateurs(14)
        for i in range(20):
            c.ajouter(bougie(i))
        self.assertEqual(a.identite, c.identite)

    def test_empreinte_chainee_exacte_c03_7(self):
        chaine, attendu = ChaineIndicateurs(14), '0' * 64
        for i in (0, 1, 3):
            b = bougie(i)
            chaine.ajouter(b)
            texte = f'{attendu}|{b.debut_ms}|{b.duree_ms}|{b.ouverture!r}|{b.haut!r}|{b.bas!r}|{b.cloture!r}'
            attendu = hashlib.sha256(texte.encode('utf-8')).hexdigest()
        chaine.ajouter(bougie(4, valide=False))
        self.assertEqual(chaine.identite.empreinte, attendu, 'bougie invalide hors de l\'empreinte')
        for champ in range(4):
            prix = [1.1, 1.102, 1.098, 1.1]
            prix[champ] += 0.0005 if champ != 2 else -0.0005
            autre = ChaineIndicateurs(14)
            autre.ajouter(Bougie('EURUSD', 0, D, *prix, 4, True, None, D))
            temoin = ChaineIndicateurs(14)
            temoin.ajouter(Bougie('EURUSD', 0, D, 1.1, 1.102, 1.098, 1.1, 4, True, None, D))
            with self.subTest(champ=champ):
                self.assertNotEqual(autre.identite.empreinte, temoin.identite.empreinte)

    def test_export_import_identiques_a_un_traitement_continu(self):
        continue_, coupee = ChaineIndicateurs(14), ChaineIndicateurs(14)
        for i in range(30):
            continue_.ajouter(bougie(i))
            coupee.ajouter(bougie(i))
        export = json.loads(json.dumps(coupee.exporter(EMPREINTE), allow_nan=False))
        reprise = ChaineIndicateurs.importer(export, EMPREINTE)
        for i in range(30, 60):
            self.assertEqual(reprise.ajouter(bougie(i)), continue_.ajouter(bougie(i)))
        self.assertEqual(reprise.identite, continue_.identite)

    def test_import_refuse(self):
        chaine = ChaineIndicateurs(14)
        for i in range(20):
            chaine.ajouter(bougie(i))
        export = chaine.exporter(EMPREINTE)
        with self.assertRaises(ErreurDonneesTemps):
            ChaineIndicateurs.importer(export, 'f' * 64)
        for cle, valeur in (('schema', 'autre'), ('atr', float('nan')), ('nombre_valides', -1), ('empreinte_chaine', 'x'),
                            ('tr_initiaux', 'abc'), ('periode', 0), ('atr', None), ('nombre_valides', 5),
                            ('cloture_precedente', None), ('premiere_ms', None), ('empreinte_chaine', '0' * 64),
                            ('dernier_debut_ms', None), ('premiere_ms', 10 ** 12)):
            altere = copy.deepcopy(export)
            altere[cle] = valeur
            with self.subTest(cle=cle, valeur=valeur), self.assertRaises(ErreurDonneesTemps):
                ChaineIndicateurs.importer(altere, EMPREINTE)
        incomplet = dict(export)
        del incomplet['atr']
        with self.assertRaises(ErreurDonneesTemps):
            ChaineIndicateurs.importer(incomplet, EMPREINTE)

    def test_export_import_d_une_chaine_vide_ou_sans_bougie_valide(self):
        for invalides in (0, 3):
            chaine = ChaineIndicateurs(14)
            for i in range(invalides):
                chaine.ajouter(bougie(i, valide=False))
            reprise = ChaineIndicateurs.importer(chaine.exporter(EMPREINTE), EMPREINTE)
            self.assertEqual((reprise.identite, reprise.ajouter(bougie(invalides))),
                             (chaine.identite, chaine.ajouter(bougie(invalides))))

    def test_ordre_et_duree(self):
        chaine = ChaineIndicateurs(14)
        chaine.ajouter(bougie(5))
        with self.assertRaises(ErreurDonneesTemps):
            chaine.ajouter(bougie(5))
        with self.assertRaises(ErreurDonneesTemps):
            chaine.ajouter(Bougie('EURUSD', 3_600_000 * 10, 3_600_000, 1.1, 1.1, 1.1, 1.1, 1, True, None, 3_600_000 * 11))
        with self.assertRaises(ErreurDonneesTemps):
            chaine.ajouter('bougie')
        with self.assertRaises(ErreurDonneesTemps):
            chaine.exporter('abc')


if __name__ == '__main__':
    unittest.main()
