"""Rejeu de bout en bout avec le moteur EMA réel (phase 3) : signaux émis puis refusés, cooldown, journal C09.

Longue série synthétique à tendances écrite en dossier temporaire (format du cahier de données, manifeste v3) ;
aucun prix réel, aucun ordre.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from robot.fixtures import generateur_ticks
from robot.fixtures.series import M15, bougies_tendances, ticks_depuis_bougies
from robot.moteur_ema.reference_ema import REFERENCE_DISPONIBLE, cadre_reference, setups_reference
from xpbots.app.rejeu import executer_rejeu
from xpbots.noyau.journal_schema import valider_enregistrement
from xpbots.noyau.temps import ms_depuis_iso

DEBUT = int(datetime(2026, 11, 2, tzinfo=timezone.utc).timestamp() * 1000)  # lundi
NB = 2600


def lire(chemin):
    return [json.loads(l) for l in Path(chemin).read_text(encoding='utf-8').splitlines()]


class TestRejeuMoteurEMA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        dossier = Path(cls._tmp.name)
        cls.bougies = bougies_tendances('EURUSD', DEBUT, NB, graine=2)
        fin = DEBUT + NB * M15
        profil = generateur_ticks.ProfilSynthetique('EURUSD', 'EURUSDsynth', Decimal('1.10000'), Decimal('0.00008'),
                                                    ((DEBUT, fin),), ((DEBUT, fin),))
        cls.ticks, cls.manifeste = dossier / 'longue.csv', dossier / 'longue.json'
        generateur_ticks.ecrire_ticks(cls.ticks, cls.manifeste, ticks_depuis_bougies(cls.bougies),
                                      generateur_ticks.manifeste_v3('Série synthétique à tendances.', fin, (profil,)))
        cls.resume, cls.lignes = {}, {}
        for nom, scenario in (('defaut', None), ('controle', 'TECHNICAL_CONTROL_NEUTRAL')):
            chemin = dossier / f'{nom}.jsonl'
            cls.resume[nom] = executer_rejeu(cls.ticks, cls.manifeste, chemin, scenario_fondamental=scenario)
            cls.lignes[nom] = lire(chemin)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_signaux_emis_puis_refuses(self):
        for nom, motif in (('defaut', 'FUNDAMENTAL_INVALID'), ('controle', 'ENVIRONMENT_NOT_READY')):
            resume, lignes = self.resume[nom], self.lignes[nom]
            emis = [l for l in lignes if l['type'] == 'CLOTURE_BOUGIE' and l['signal_emis']]
            intentions = [l for l in lignes if l['type'] == 'INTENTION']
            with self.subTest(scenario=nom):
                self.assertGreater(len(emis), 5)
                self.assertEqual(resume['intentions'], {motif: len(emis)})
                self.assertTrue(all(i['decision'] == 'REFUS' and not i['ordre_envoye'] for i in intentions))
                self.assertEqual([i['cle']['cloture_utc'] for i in intentions], [l['cloture_utc'] for l in emis])
                self.assertTrue(all(valider_enregistrement(l) == [] for l in lignes))

    def test_motifs_du_moteur(self):
        clotures = self.resume['defaut']['clotures']
        self.assertEqual(sum(clotures.values()), NB)
        self.assertEqual(clotures['SIGNAL'], self.resume['defaut']['intentions']['FUNDAMENTAL_INVALID'])
        self.assertTrue({'WARMUP', 'OUTSIDE_SESSION', 'NO_SETUP'} <= set(clotures))
        self.assertEqual(clotures['WARMUP'], 999)  # la 1 000ᵉ bougie est la première décidable

    def test_cooldown_apres_chaque_refus(self):
        clotures = [l for l in self.lignes['defaut'] if l['type'] == 'CLOTURE_BOUGIE']
        for i, ligne in enumerate(clotures):
            if ligne['signal_emis']:
                suivante = clotures[i + 1]['etat_detecteur']['transition']
                self.assertIn(suivante, ('IGNOREE', 'HORS_FENETRE'))
                self.assertEqual(ligne['etat_detecteur']['etat'], 'ATTENTE_ISSUE')

    def test_etat_du_detecteur_et_niveaux_journalises(self):
        intention = next(l for l in self.lignes['defaut'] if l['type'] == 'INTENTION')
        signal = intention['signal']
        self.assertEqual(signal['multiple_objectif'], 1.5)
        self.assertTrue({'b_sl', 'tampon', 'extreme_repli', 'age_repli', 'entrees_jour'} <= set(signal['etat_detecteur']))
        self.assertGreater(signal['sens'] * (float(signal['cloture_bid']) - signal['b_sl']), 0)

    @unittest.skipUnless(REFERENCE_DISPONIBLE, 'numpy et pandas requis par reference.technical')
    def test_concordance_avec_la_reference(self):
        attendus = setups_reference(cadre_reference(self.bougies), Decimal('0.00001'))
        emis = [l for l in self.lignes['defaut'] if l['type'] == 'CLOTURE_BOUGIE' and l['signal_emis']]
        self.assertEqual([ms_depuis_iso(l['cloture_utc']) for l in emis], [a['cloture_ms'] for a in attendus])


if __name__ == '__main__':
    unittest.main()
