"""Catégorie 1, couche 0d : C09 réel, écritures exactes et réparation après panne."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
from robot.outils.configuration import configuration_figee
from xpbots.noyau.c2_journal import Enveloppe, enregistrement, empreintes_regles, serialiser
from xpbots.infra.c0d_journal import JournalFichiers, ecrire_atomique, lire_json, lire_octets, ecrire_json


def evenement(n, t):
    e = Enveloppe('FIXTURE', 'REFERENCE', 'PAPER', n, t, empreintes_regles(configuration_figee()))
    decision = serialiser(enregistrement('ALERTE', e, {'code': 'FIXTURE'})).encode('utf-8')
    entree = json.dumps(dict(numero=n, instant_reception_utc_ms=t, type_evenement='MINUTERIE', contenu=None),
                        ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return n, t, (decision,), (entree,)


class TestJournalPhysique(unittest.TestCase):
    def test_jours_utc_et_octets_c09_exacts(self):
        with TemporaryDirectory() as d:
            j = JournalFichiers(d, 'FIXTURE'); e1, e2 = evenement(1, 0), evenement(2, 86_400_000)
            j.ajouter((e1, e2))
            p = Path(d)/'logs/FIXTURE'
            self.assertEqual((p/'decisions_1970-01-01.jsonl').read_bytes(), e1[2][0]+b'\n')
            self.assertEqual((p/'entrees_1970-01-02.jsonl').read_bytes(), e2[3][0]+b'\n')
            self.assertEqual(j.decisions((enregistrement('ALERTE', Enveloppe('FIXTURE', 'REFERENCE', 'PAPER', 1, 0,
                empreintes_regles(configuration_figee())), {'code': 'FIXTURE'}),)), e1[2])

    def test_repetition_et_reparation_sans_double_ligne(self):
        with TemporaryDirectory() as d:
            j = JournalFichiers(d, 'FIXTURE'); ev = (evenement(1, 0), evenement(2, 100))
            j.ajouter(ev); j.ajouter(ev)
            p = Path(d)/'logs/FIXTURE/decisions_1970-01-01.jsonl'; attendu = p.read_bytes()
            p.write_bytes(attendu+b'{partiel')
            r = JournalFichiers(d, 'FIXTURE'); r.publier(ev)
            self.assertEqual(p.read_bytes(), attendu)
            r.ajouter((evenement(3, 200),))
            self.assertEqual(len(p.read_bytes().splitlines()), 3)

    def test_echec_physique_impose_reparation_avant_nouvel_append(self):
        with TemporaryDirectory() as d:
            j = JournalFichiers(d, 'FIXTURE'); ev = (evenement(1, 0),)
            with patch('os.fsync', side_effect=OSError('disque factice')):
                with self.assertRaises(OSError): j.ajouter(ev)
            with self.assertRaises(ValueError): j.ajouter(ev)
            j.publier(ev); j.ajouter(ev)
            self.assertEqual(len((Path(d)/'logs/FIXTURE/decisions_1970-01-01.jsonl').read_bytes().splitlines()), 1)

    def test_remplacement_atomique_preserve_ancien_fichier_si_echec(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'cible'; p.write_bytes(b'ancienne')
            with patch('os.replace', side_effect=OSError('remplacement factice')):
                with self.assertRaises(OSError): ecrire_atomique(p, b'nouvelle')
            self.assertEqual(p.read_bytes(), b'ancienne')
            ecrire_atomique(p, b'nouvelle'); self.assertEqual(p.read_bytes(), b'nouvelle')

    def test_json_strict_plafond_et_pas_de_normalisation_silencieuse(self):
        with TemporaryDirectory() as d:
            p = Path(d)/'document'; ecrire_json(p, {'é': 1})
            self.assertEqual(lire_json(p, 20), {'é': 1})
            with self.assertRaises(ValueError): lire_octets(p, 1)
            for b in (b'{"x":1,"x":2}', b'{"x":NaN}'):
                p.write_bytes(b)
                with self.assertRaises(ValueError): lire_json(p, 100)
            with self.assertRaises(ValueError): JournalFichiers(d, 'FIXTURE').ajouter(((1, 0, (b'{}',), ()),))
            self.assertFalse((Path(d)/'logs').exists())

    def test_nom_sequence_et_entree_corrompus_refuses(self):
        with TemporaryDirectory() as d:
            for ident in ('../a', 'C:\\a', '..', 'a.'):
                with self.assertRaises(ValueError): JournalFichiers(d, ident)
            j = JournalFichiers(d, 'FIXTURE')
            with self.assertRaises(ValueError): j.ajouter((evenement(2, 100),))
            ev = evenement(1, 0)
            with self.assertRaises(ValueError): j.ajouter(((1, 0, ev[2], (b'{}',)),))
