"""Enveloppes des comptes indépendants, dans le seul dossier racine sûr."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.configuration import configuration_figee
from xpbots.noyau.c2_journal import Enveloppe,enregistrement,empreintes_regles,serialiser
from xpbots.infra.c0d_journal import JournalFichiers


def decision(identifiant,bras,mode='PAPER_AB'):
    return serialiser(enregistrement('ALERTE',
        Enveloppe(identifiant,bras,mode,1,0,empreintes_regles(configuration_figee())),
        {'code':'FIXTURE_AB'})).encode()


class TestJournalAB(unittest.TestCase):
    def test_bras_exacts_publies_et_repares_sans_modifier_c09(self):
        with TemporaryDirectory() as root:
            ds=tuple(decision('FIXTURE:'+n,n) for n in ('REFERENCE','IA'))
            evenement=(1,0,ds,())
            j=JournalFichiers(root,'FIXTURE');j.ajouter((evenement,))
            fichier=Path(root)/'logs/FIXTURE/decisions_1970-01-01.jsonl'
            self.assertEqual(fichier.read_bytes(),b''.join(b+b'\n' for b in ds))
            fichier.write_bytes(b'CORROMPU')
            JournalFichiers(root,'FIXTURE').publier((evenement,))
            self.assertEqual(fichier.read_bytes(),b''.join(b+b'\n' for b in ds))

    def test_deploiement_etranger_suffixe_croise_et_mode_simple_refuses(self):
        with TemporaryDirectory() as root:
            for b in (decision('AUTRE:REFERENCE','REFERENCE'),decision('FIXTURE:IA','REFERENCE'),
                      decision('FIXTURE:REFERENCE','REFERENCE','PAPER')):
                with self.assertRaises(ValueError):JournalFichiers(root,'FIXTURE').ajouter(((1,0,(b,),()),))
            self.assertFalse((Path(root)/'logs').exists())
