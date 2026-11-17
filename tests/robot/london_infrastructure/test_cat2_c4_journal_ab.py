"""Les deux livres sont réparés à la réouverture de l'assemblage physique."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.configuration import configuration_figee
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.qualification_mt5 import T
from xpbots.infra.c4_assemblage import InfrastructurePhysique
from xpbots.noyau.c2_journal import Enveloppe,enregistrement,empreintes_regles,serialiser
from xpbots.orchestration.c3_codec import serialiser_valeur


class TestAssemblageJournalAB(unittest.TestCase):
    def test_deux_bras_commit_et_reparation_du_meme_deploiement(self):
        c=configuration_figee()
        meta=dict(deploiement='FIXTURE_AB',mode=c.ia.parametres['default_evaluation_mode'],commit='a'*40,
                  empreintes=dict(technique=c.technique.empreinte_octets,ia=c.ia.empreinte_octets))
        with TemporaryDirectory() as temp:
            root=Path(temp).resolve();sdk=FauxMT5(root,instant_ms=T)
            options=dict(racine=root,max_octets_echange=1048576,snapshot_max_octets=c.ia.parametres['snapshot_max_bytes'],sdk=sdk)
            a=InfrastructurePhysique(c.technique.commun,meta,{'EURUSD':'EURUSD.micro'},**options)
            try:
                decisions=tuple(serialiser(enregistrement('ALERTE',Enveloppe('FIXTURE_AB:'+n,n,meta['mode'],1,T,
                    empreintes_regles(c)),{'code':'FIXTURE_AB'})).encode() for n in ('REFERENCE','IA'))
                a.depot.persister(1,T,serialiser_valeur({'fixture':'AB'}),decisions=decisions)
                a.journal.ajouter(a.depot.evenements())
                fichier=a.journal.dossier/'decisions_2026-11-10.jsonl'
                attendu=b''.join(b+b'\n' for b in decisions)
                self.assertEqual(fichier.read_bytes(),attendu)
            finally:a.fermer(0)
            fichier.write_bytes(b'COUPE_PHYSIQUE')
            b=InfrastructurePhysique(c.technique.commun,meta,{'EURUSD':'EURUSD.micro'},**options)
            try:self.assertEqual(fichier.read_bytes(),attendu)
            finally:b.fermer(0)
            self.assertFalse(any(n=='order_send' for n,*_ in sdk.appels))
