"""Segments minimaux du squelette : chacun respecte la spécification sur son périmètre réduit."""
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from robot.outils import FIXTURE_MANIFESTE, FIXTURE_TICKS, signal_valide
from xpbots.app.segments_minimaux import (SCENARIO_TECHNICAL_CONTROL_NEUTRAL, AgregateurM15Minimal,
                                          ContexteIANeutre, CoordinateurRefus, EcrivainJournalJSONL,
                                          ErreurDonneesFixture, ErreurJournal, ExecutionPapierMinimale,
                                          FondamentalAbsent, IssueInattendue, LecteurFixtureCSV, StrategieNeutre)
from xpbots.noyau.config import charger_bundle_technique
from xpbots.noyau.decisions import (CleIntention, EtatContexteIA, MotifRefus, Refuse, ResultatTechnique, Sens)
from xpbots.noyau.journal_schema import ConstructeurEnregistrements, EnregistrementInvalide, Mode
from xpbots.noyau.marche import Bougie, BougieEnrichie, StatutBougie, Tick
from xpbots.noyau.ports import ContexteIA, ControleFondamental, Journal, SourceTicksHistoriques, Strategie
from xpbots.noyau.temps import Instant

T = 1793779200000  # 08:00:00.000 UTC
M15 = 900_000
ENTETE = 'canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask\n'


def manifeste(**changements):
    m = {'schema': 'xp-fixture-manifeste-v1', 'origine': 'synthetique', 'fuseau': 'UTC', 'description': 'test',
         'fin_donnees_ms': T + 4 * M15,
         'symboles': {'EURUSD': {'symbole_courtier': 'EURUSDsynth', 'couverture': [[T, T + 4 * M15]]}}}
    m.update(changements)
    return m


class AvecDossier(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def lecteur(self, lignes, m=None):
        ticks, mani = self.dossier / 't.csv', self.dossier / 'm.json'
        ticks.write_text(ENTETE + ''.join(l + '\n' for l in lignes), encoding='utf-8')
        mani.write_text(m if isinstance(m, str) else json.dumps(m or manifeste()), encoding='utf-8')
        return LecteurFixtureCSV(ticks, mani)


class TestLecteurFixture(AvecDossier):
    def test_fixture_versionnee(self):
        lecteur = LecteurFixtureCSV(FIXTURE_TICKS, FIXTURE_MANIFESTE)
        self.assertIsInstance(lecteur, SourceTicksHistoriques)
        ticks = list(lecteur.ticks())
        self.assertEqual(len(ticks), 933)
        self.assertEqual(lecteur.symboles(), ('EURUSD', 'GBPUSD'))
        self.assertEqual(len(lecteur.couverture('GBPUSD')), 2)
        self.assertTrue(all(a.instant < b.instant for a, b in zip(ticks, ticks[1:])))
        self.assertEqual(set(lecteur.empreintes()), {'ticks', 'manifeste'})

    def test_ordre_strict_ms_puis_sequence(self):
        for lignes in (['EURUSD,EURUSDsynth,%d,2,1.10000,1.10008' % (T + 10),
                        'EURUSD,EURUSDsynth,%d,1,1.10000,1.10008' % (T + 10)],
                       ['EURUSD,EURUSDsynth,%d,1,1.10000,1.10008' % (T + 20),
                        'EURUSD,EURUSDsynth,%d,2,1.10000,1.10008' % (T + 10)]):
            with self.subTest(lignes=lignes), self.assertRaises(ErreurDonneesFixture):
                list(self.lecteur(lignes).ticks())

    def test_lignes_refusees(self):
        for ligne in ('GBPUSD,GBPUSDsynth,%d,1,1.30000,1.30010' % (T + 1),
                      'EURUSD,AUTRE,%d,1,1.10000,1.10008' % (T + 1),
                      'EURUSD,EURUSDsynth,%d,1,1.1e-3,1.10008' % (T + 1),
                      'EURUSD,EURUSDsynth,%d,1,1.10000' % (T + 1),
                      'EURUSD,EURUSDsynth,%d,1,1.10000,1.10008' % (T + 4 * M15)):
            with self.subTest(ligne=ligne), self.assertRaises(ErreurDonneesFixture):
                list(self.lecteur([ligne]).ticks())

    def test_en_tete_exact(self):
        ticks, mani = self.dossier / 't.csv', self.dossier / 'm.json'
        ticks.write_text('symbol,time,bid,ask\n', encoding='utf-8')
        mani.write_text(json.dumps(manifeste()), encoding='utf-8')
        with self.assertRaises(ErreurDonneesFixture):
            list(LecteurFixtureCSV(ticks, mani).ticks())

    def test_manifestes_refuses(self):
        for m in (manifeste(fuseau='Europe/London'), manifeste(schema='autre'), dict(manifeste(), extra=1),
                  manifeste(symboles={'EURUSD': {'symbole_courtier': 'X', 'couverture': [[T + 10, T]]}}),
                  manifeste(symboles={'EURUSD': {'symbole_courtier': 'X',
                                                 'couverture': [[T, T + M15], [T + 10, T + 2 * M15]]}}),
                  manifeste(symboles={'EURUSD': {'symbole_courtier': 'X', 'couverture': [[T, T + 9 * M15]]}}),
                  '{"schema":"xp-fixture-manifeste-v1","schema":"x"}'):
            with self.subTest(m=m), self.assertRaises(ErreurDonneesFixture):
                self.lecteur([], m)


def tick(t, bid='1.10000', symbole='EURUSD', sequence=0):
    return Tick(symbole, symbole + 'synth', Instant(t, sequence), Decimal(bid), Decimal(bid) + Decimal('0.00008'))


class TestAgregateur(unittest.TestCase):
    def agregateur(self, couverture=None):
        couverture = couverture or {'EURUSD': ((T, T + 8 * M15),), 'GBPUSD': ((T, T + 8 * M15),)}
        return AgregateurM15Minimal(['EURUSD', 'GBPUSD'], couverture, 900)

    def test_tick_de_frontiere_dans_la_bougie_suivante(self):
        ag = self.agregateur()
        for t, bid in ((T + 1, '1.10000'), (T + M15 - 1, '1.10020')):
            self.assertEqual(ag.avancer(t), [])
            ag.ajouter(tick(t, bid))
        closes = ag.avancer(T + M15)  # le tick à T+900 s clôt la précédente sans y entrer (C03 point 2)
        ag.ajouter(tick(T + M15, '1.10500'))
        self.assertEqual(len(closes), 1)
        b = closes[0].bougie
        self.assertEqual((b.ouverture_ms, b.cloture_ms, b.c, b.h, b.nb_ticks), (T, T + M15, Decimal('1.10020'),
                                                                              Decimal('1.10020'), 2))
        suivante = ag.terminer(T + 2 * M15)[0].bougie
        self.assertEqual((suivante.ouverture_ms, suivante.o, suivante.nb_ticks), (T + M15, Decimal('1.10500'), 1))

    def test_validite_par_couverture_declaree(self):
        ag = self.agregateur({'EURUSD': ((T, T + M15 // 2), (T + M15 // 2 + 1, T + 8 * M15)),
                              'GBPUSD': ((T, T + 8 * M15),)})
        ag.ajouter(tick(T + 1))
        be = ag.avancer(T + M15)[0]
        self.assertFalse(be.bougie.valide)
        self.assertIs(be.statut, StatutBougie.DATA_GAP)

    def test_ordre_des_clotures_simultanees_et_bougie_incomplete(self):
        ag = self.agregateur()
        ag.ajouter(tick(T + 5, '1.30000', 'GBPUSD', 1))
        ag.ajouter(tick(T + 6, '1.10000', 'EURUSD', 2))
        closes = ag.avancer(T + M15)
        self.assertEqual([be.bougie.symbole for be in closes], ['EURUSD', 'GBPUSD'])
        ag.ajouter(tick(T + M15 + 1))
        self.assertEqual(ag.terminer(T + M15 + 10), [])
        self.assertEqual(ag.bougies_incompletes, 1)

    def test_horloge_avancee_obligatoire(self):
        ag = self.agregateur()
        ag.ajouter(tick(T + 1))
        with self.assertRaises(RuntimeError):
            ag.ajouter(tick(T + M15 + 1))
        with self.assertRaises(ValueError):
            ag.ajouter(tick(T + 2, symbole='XAUUSD'))


def bougie_ok(valide=True):
    b = Bougie('EURUSD', 900, T, Decimal('1.1'), Decimal('1.1'), Decimal('1.1'), Decimal('1.1'), 1, valide)
    return BougieEnrichie(b, StatutBougie.OK if valide else StatutBougie.DATA_GAP)


class TestSegmentsDeControle(unittest.TestCase):
    def test_strategie_neutre(self):
        s = StrategieNeutre('EMA_V3')
        self.assertIsInstance(s, Strategie)
        self.assertIs(s.sur_cloture(bougie_ok()).motif, MotifRefus.NO_SETUP)
        self.assertIs(s.sur_cloture(bougie_ok(False)).motif, MotifRefus.DATA_GAP)
        self.assertIs(s.sur_cloture(BougieEnrichie(bougie_ok().bougie, StatutBougie.WARMUP)).motif,
                      MotifRefus.WARMUP)
        with self.assertRaises(IssueInattendue):
            s.appliquer_issue(CleIntention.du_signal('d', signal_valide()), Refuse(MotifRefus.NO_SETUP, 1))

    def test_fondamental_absent_bloque_par_defaut(self):
        f = FondamentalAbsent(Mode.PAPER)
        self.assertIsInstance(f, ControleFondamental)
        d = f.autoriser('EURUSD', Sens.ACHAT, T)
        self.assertEqual((d.autorise, d.motif, d.permission), (False, MotifRefus.FUNDAMENTAL_INVALID, None))

    def test_scenario_technique_seulement_nomme_et_hors_demo(self):
        d = FondamentalAbsent(Mode.PAPER, SCENARIO_TECHNICAL_CONTROL_NEUTRAL).autoriser('EURUSD', Sens.VENTE, T)
        self.assertTrue(d.autorise)
        self.assertEqual(dict(d.permission), {'direction': 'ANY', 'risk_state': 'ALLOW'})
        self.assertEqual(d.scenario, 'TECHNICAL_CONTROL_NEUTRAL')
        with self.assertRaises(ValueError):
            FondamentalAbsent(Mode.DEMO, SCENARIO_TECHNICAL_CONTROL_NEUTRAL)
        with self.assertRaises(ValueError):
            FondamentalAbsent(Mode.PAPER, 'ANY_ALLOW')

    def test_contexte_ia_neutre(self):
        c = ContexteIANeutre()
        self.assertIsInstance(c, ContexteIA)
        self.assertIs(c.decision('EURUSD', T).etat, EtatContexteIA.NEUTRAL)


class TestEcrivainJournal(AvecDossier):
    def test_lignes_canoniques_lf_et_refus(self):
        constructeur = ConstructeurEnregistrements('dep', Mode.PAPER, charger_bundle_technique())
        chemin = self.dossier / 'sous' / 'journal.jsonl'
        with EcrivainJournalJSONL(chemin) as journal:
            self.assertIsInstance(journal, Journal)
            journal.ajouter(constructeur.cloture_bougie('EMA_V3', bougie_ok(),
                                                        ResultatTechnique(None, MotifRefus.NO_SETUP)))
            with self.assertRaises(EnregistrementInvalide):
                journal.ajouter({'type': 'CLOTURE_BOUGIE'})
        octets = chemin.read_bytes()
        self.assertEqual(octets.count(b'\n'), 1)
        self.assertNotIn(b'\r', octets)
        self.assertEqual(json.loads(octets)['motif'], 'NO_SETUP')
        with self.assertRaises(ErreurJournal):
            EcrivainJournalJSONL(chemin)


class StrategieEmettrice:
    """Méthode de test : émet le signal S01.5 à la première bougie valide, puis enregistre l'issue reçue."""

    strategie_id = 'EMA_V3'

    def __init__(self):
        self.issues = []
        self._emis = False

    def sur_cloture(self, bougie):
        if bougie.statut is StatutBougie.OK and not self._emis:
            self._emis = True
            b = bougie.bougie
            return ResultatTechnique(signal_valide(symbole=b.symbole, cloture_ms=b.cloture_ms), None)
        return ResultatTechnique(None, MotifRefus.NO_SETUP)

    def appliquer_issue(self, cle, issue):
        self.issues.append((cle, issue))


class JournalMemoire:
    def __init__(self):
        self.lignes = []

    def ajouter(self, enregistrement):
        self.lignes.append(enregistrement)


class TestCoordinateurRefus(unittest.TestCase):
    def coordonner(self, scenario=None, contexte=None):
        strategie, journal = StrategieEmettrice(), JournalMemoire()
        constructeur = ConstructeurEnregistrements('dep', Mode.PAPER, charger_bundle_technique())
        coordinateur = CoordinateurRefus('dep', [strategie], FondamentalAbsent(Mode.PAPER, scenario),
                                         contexte or ContexteIANeutre(), ExecutionPapierMinimale(), journal,
                                         constructeur)
        coordinateur.sur_bougie(bougie_ok())
        return strategie, journal.lignes

    def test_fondamental_absent_refus_avant_le_contexte_ia(self):
        strategie, lignes = self.coordonner()
        self.assertEqual([l['type'] for l in lignes], ['CLOTURE_BOUGIE', 'INTENTION'])
        self.assertTrue(lignes[0]['signal_emis'])
        intention = lignes[1]
        self.assertEqual((intention['decision'], intention['motif'], intention['ordre_envoye']),
                         ('REFUS', 'FUNDAMENTAL_INVALID', False))
        self.assertIsNone(intention['contexte_ia'])
        (cle, issue), = strategie.issues
        self.assertEqual((issue.motif, issue.instant_ms), (MotifRefus.FUNDAMENTAL_INVALID, T + M15))
        self.assertEqual(cle.en_json(), intention['cle'])

    def test_scenario_nomme_puis_environnement_absent(self):
        strategie, lignes = self.coordonner(SCENARIO_TECHNICAL_CONTROL_NEUTRAL)
        intention = lignes[1]
        self.assertEqual(intention['motif'], 'ENVIRONMENT_NOT_READY')
        self.assertEqual(intention['contexte_ia']['etat'], 'NEUTRAL')
        self.assertEqual(intention['fondamental']['scenario'], 'TECHNICAL_CONTROL_NEUTRAL')

    def test_veto_ia_ajoute_seulement_un_refus(self):
        class ContexteBloquant:
            def decision(self, symbole, instant_ms):
                from xpbots.noyau.decisions import DecisionContexteIA
                return DecisionContexteIA(EtatContexteIA.BLOCK, 4, ('evt-1',))

        _, lignes = self.coordonner(SCENARIO_TECHNICAL_CONTROL_NEUTRAL, ContexteBloquant())
        self.assertEqual(lignes[1]['motif'], 'AI_CONTEXT_VETO')
        _, lignes = self.coordonner(None, ContexteBloquant())
        self.assertEqual(lignes[1]['motif'], 'FUNDAMENTAL_INVALID')  # le veto ne remplace jamais C05


if __name__ == '__main__':
    unittest.main()
