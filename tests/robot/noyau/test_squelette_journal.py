"""Schéma fermé des enregistrements C09 et construction numérotée."""
import copy
import unittest
from datetime import date
from decimal import Decimal

from robot.outils import signal_valide
from xpbots.noyau.config import charger_bundle_technique
from xpbots.noyau.decisions import (CleIntention, DecisionContexteIA, DecisionFondamentale, EtatContexteIA,
                                    MotifRefus, ResultatTechnique, Sens)
from xpbots.noyau.journal_schema import (ConstructeurEnregistrements, Decision, EnregistrementInvalide, Mode,
                                         en_json, valider_enregistrement)
from xpbots.noyau.marche import Bougie, BougieEnrichie, StatutBougie

T = 1793779200000


def bougie_enrichie():
    b = Bougie('EURUSD', 900, T, Decimal('1.10000'), Decimal('1.10020'), Decimal('1.09990'), Decimal('1.10010'),
               12, True)
    return BougieEnrichie(b, StatutBougie.OK, jour_londres=date(2026, 11, 4))


class TestConstruction(unittest.TestCase):
    def setUp(self):
        self.bundle = charger_bundle_technique()
        self.constructeur = ConstructeurEnregistrements('dep-test', Mode.PAPER, self.bundle)

    def enregistrements(self):
        c = self.constructeur
        init = c.initialisation(T, ['EURUSD'], {'fichier': 'x.csv', 'sha256': '0' * 64}, ['strategie_neutre'], None)
        cloture = c.cloture_bougie('EMA_V3', bougie_enrichie(), ResultatTechnique(None, MotifRefus.NO_SETUP))
        signal = signal_valide()
        intention = c.intention(signal.cloture_ms, CleIntention.du_signal('dep-test', signal), signal,
                                DecisionFondamentale(False, MotifRefus.FUNDAMENTAL_INVALID), None, Decision.REFUS,
                                MotifRefus.FUNDAMENTAL_INVALID, False)
        return init, cloture, intention

    def test_numerotation_sans_trou_et_conformite(self):
        enregistrements = self.enregistrements()
        self.assertEqual([e['sequence'] for e in enregistrements], [1, 2, 3])
        for enr in enregistrements:
            self.assertEqual(valider_enregistrement(enr), [])
            self.assertEqual(enr['regles'], {'version_technique': self.bundle.valeur('common', 'version'),
                                             'empreinte': self.bundle.empreinte})
        self.assertEqual(self.constructeur.derniere_sequence, 3)

    def test_valeurs_journalisees_exactes(self):
        _, cloture, intention = self.enregistrements()
        self.assertEqual(cloture['ohlc'], {'o': '1.10000', 'h': '1.10020', 'l': '1.09990', 'c': '1.10010'})
        self.assertEqual(cloture['jour_londres'], '2026-11-04')
        self.assertEqual(cloture['cloture_utc'], '2026-11-04T08:15:00.000Z')
        self.assertEqual(intention['signal']['cloture_bid'], '1.10000')
        self.assertEqual(intention['signal']['sens'], 1)
        self.assertEqual(intention['cle']['cloture_utc'], '2026-11-04T08:15:00.000Z')

    def test_echec_sans_consommer_de_numero(self):
        with self.assertRaises(EnregistrementInvalide):
            self.constructeur.initialisation(T, [], {}, [], None)
        self.assertEqual(self.constructeur.derniere_sequence, 0)

    def test_contexte_ia_et_admission(self):
        signal = signal_valide(sens=Sens.VENTE, b_sl=1.10055)
        enr = self.constructeur.intention(
            signal.cloture_ms, CleIntention.du_signal('dep-test', signal), signal,
            DecisionFondamentale(True, None, {'direction': 'ANY'}, 'TECHNICAL_CONTROL_NEUTRAL'),
            DecisionContexteIA(EtatContexteIA.BLOCK, 3, ('evt',)), Decision.REFUS, MotifRefus.AI_CONTEXT_VETO, False)
        self.assertEqual(enr['contexte_ia'], {'etat': 'BLOCK', 'sequence_snapshot': 3, 'evenements': ['evt']})


class TestValidation(unittest.TestCase):
    def setUp(self):
        constructeur = ConstructeurEnregistrements('dep-test', Mode.PAPER, charger_bundle_technique())
        self.cloture = constructeur.cloture_bougie('EMA_V3', bougie_enrichie(),
                                                   ResultatTechnique(None, MotifRefus.NO_SETUP))
        signal = signal_valide()
        self.intention = constructeur.intention(
            signal.cloture_ms, CleIntention.du_signal('dep-test', signal), signal, None, None, Decision.REFUS,
            MotifRefus.DAILY_LOSS_LOCK, False)

    def invalide(self, base, **changements):
        enr = copy.deepcopy(base)
        enr.update(changements)
        return valider_enregistrement(enr)

    def test_cles_exactes(self):
        enr = copy.deepcopy(self.cloture)
        del enr['motif']
        self.assertTrue(valider_enregistrement(enr))
        self.assertTrue(self.invalide(self.cloture, inattendue=1))
        self.assertTrue(self.invalide(self.cloture, type='ORDRE_INCONNU'))

    def test_valeurs_hors_contrat(self):
        for changements in ({'motif': 'MOTIF_INVENTE'}, {'sequence': 0}, {'sequence': True},
                            {'instant_utc': '2026-11-04T08:15:00Z'}, {'mode': 'REEL'}, {'deployment_id': ' '},
                            {'signal_emis': True}, {'statut': 'INCONNU'}, {'regles': {'version_technique': 'x'}},
                            {'a_t': float('nan')}):
            with self.subTest(changements=changements):
                self.assertTrue(self.invalide(self.cloture, **changements))

    def test_refus_sans_ordre_et_admission_sans_motif(self):
        self.assertTrue(self.invalide(self.intention, ordre_envoye=True))
        self.assertTrue(self.invalide(self.intention, decision='ADMISSION'))
        self.assertTrue(self.invalide(self.intention, motif=None))
        self.assertEqual(self.invalide(self.intention, decision='ADMISSION', motif=None), [])

    def test_conversion_json_explicite(self):
        self.assertEqual(en_json({'d': Decimal('1.10'), 'm': MotifRefus.WARMUP, 's': Sens.VENTE,
                                  'j': date(2026, 3, 29), 't': (1, 2)}),
                         {'d': '1.10', 'm': 'WARMUP', 's': -1, 'j': '2026-03-29', 't': [1, 2]})
        for valeur in (object(), Decimal('NaN'), {1: 'x'}):
            with self.subTest(valeur=valeur), self.assertRaises(EnregistrementInvalide):
                en_json(valeur)


if __name__ == '__main__':
    unittest.main()
