"""Catégorie 1, couche 2 (journal) : enveloppe, champs obligatoires, motifs, sérialisation canonique."""
from decimal import Decimal
import json
import re
import unittest

from robot.outils.chemins import DOCUMENT_CONTRATS
from robot.outils.configuration import configuration_figee
from robot.outils.profils import champs_instrument
from xpbots.noyau.c1a_marche import Bougie
from xpbots.noyau.c1b_instrument import construire_profil_instrument
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, CleIntention, Issue, Sens, SignalTechnique
from xpbots.noyau.c2_journal import (CHAMPS_OBLIGATOIRES, VERSION_SCHEMA, Enveloppe, ErreurJournal, TypeEnregistrement,
                                     empreintes_regles, enregistrement, enregistrement_cloture, enregistrement_intention,
                                     serialiser)

CONFIGURATION = configuration_figee()
EMPREINTES = empreintes_regles(CONFIGURATION)
BOUGIE = Bougie('EURUSD', 900_000, 900_000, 1.1, 1.2, 1.0, 1.15, 4, True, None, 1_800_000)
PROFIL = construire_profil_instrument(champs_instrument(), CONFIGURATION.technique.commun).profil


def enveloppe(numero=1, **changements):
    champs = dict(deploiement='dep-1', bras='REFERENCE', mode='REJEU', numero=numero, instant_utc_ms=1_800_000,
                  empreinte_regles=EMPREINTES)
    champs.update(changements)
    return Enveloppe(**champs)


def cloture(resultat, profil=PROFIL):
    return enregistrement_cloture(enveloppe(), bougie=BOUGIE, resultat=resultat, profil=profil,
                                  indicateurs={'tr': 0.2, 'atr': 0.15}, etat_strategie={'fenetre': False},
                                  permission=None, version_calendrier=None, snapshot_ia=None)


class TestEnveloppe(unittest.TestCase):
    def test_empreintes(self):
        self.assertEqual(dict(EMPREINTES), {'technique': CONFIGURATION.technique.empreinte_canonique,
                                            'ia': CONFIGURATION.ia.empreinte_canonique})

    def test_refus(self):
        for changement in ({'deploiement': ''}, {'bras': 'B'}, {'mode': 'LIVE'}, {'numero': 0}, {'numero': True},
                           {'instant_utc_ms': -1}, {'empreinte_regles': {'technique': 'x', 'ia': 'y'}},
                           {'empreinte_regles': {'technique': EMPREINTES['technique']}}):
            with self.subTest(changement=changement), self.assertRaises(ErreurJournal):
                enveloppe(**changement)

    def test_types_du_document_08(self):
        texte = DOCUMENT_CONTRATS.read_text(encoding='utf-8')
        puce = next(l for l in texte.splitlines() if l.startswith('- **Types et champs propres**'))
        suite = texte[texte.index(puce):texte.index('- **Journal d', texte.index(puce))]
        self.assertEqual({t.value for t in TypeEnregistrement}, set(re.findall(r'`([A-Z_]+)`', suite)))


class TestEnregistrements(unittest.TestCase):
    def test_cloture_sans_signal(self):
        e = cloture(AbsenceDeSignal('LONDON_V3', 'EURUSD', 1_800_000, 'NO_SETUP', 'PAS_DE_CASSURE', {'h': 1.2}))
        d = e.vers_dict()
        self.assertEqual((d['type'], d['version_schema'], d['motif'], d['signal'], d['numero']),
                         (TypeEnregistrement.CLOTURE, VERSION_SCHEMA, 'NO_SETUP', None, 1))
        self.assertEqual(d['bougie']['fin_utc_ms'], 1_800_000)
        self.assertEqual(d['instrument']['tick_size'], Decimal('0.00001'))
        self.assertTrue(CHAMPS_OBLIGATOIRES[TypeEnregistrement.CLOTURE] <= set(d))

    def test_cloture_avec_signal(self):
        e = cloture(SignalTechnique('LONDON_V3', 'EURUSD', 1_800_000, 'ACHAT', 1.15, 0.001, 1.14, 2.0), profil=None)
        d = e.vers_dict()
        self.assertEqual((d['motif'], d['signal']['sens'], d['instrument']), (None, Sens.ACHAT, None))

    def test_incoherences(self):
        for resultat in (AbsenceDeSignal('LONDON_V3', 'GBPUSD', 1_800_000, 'NO_SETUP', 'PAS_DE_CASSURE'),
                         AbsenceDeSignal('LONDON_V3', 'EURUSD', 900_000, 'NO_SETUP', 'PAS_DE_CASSURE')):
            with self.subTest(resultat=resultat), self.assertRaises(ErreurJournal):
                cloture(resultat)
        gbp = construire_profil_instrument(champs_instrument(symbole='GBPUSD'), CONFIGURATION.technique.commun).profil
        with self.assertRaises(ErreurJournal):
            cloture(AbsenceDeSignal('LONDON_V3', 'EURUSD', 1_800_000, 'NO_SETUP', 'PAS_DE_CASSURE'), profil=gbp)

    def test_intention(self):
        cle = CleIntention('dep-1', 'LONDON_V3', 'EURUSD', 1_800_000, Sens.VENTE)
        issue = Issue(cle, 'REFUSEE', 1_801_000, 'MIN_VOLUME_OR_RISK_REJECT')
        e = enregistrement_intention(enveloppe(), cle=cle, longueur_empreinte=10, tentatives=[{'spread': Decimal('0.00012')}],
                                     issue=issue, cout_ia_usd=Decimal('0.0010'))
        d = e.vers_dict()
        self.assertEqual((d['empreinte_cle'], d['motif'], d['issue']['nature']), (cle.empreinte(10), 'MIN_VOLUME_OR_RISK_REJECT', 'REFUSEE'))
        autre = CleIntention('dep-1', 'LONDON_V3', 'EURUSD', 1_800_000, Sens.ACHAT)
        for arguments in ({'issue': Issue(autre, 'REMPLIE', 1)}, {'cout_ia_usd': -1}, {'cout_ia_usd': Decimal('-0.01')},
                          {'longueur_empreinte': 0}):
            champs = dict(cle=cle, longueur_empreinte=10, tentatives=[], issue=issue, cout_ia_usd=None)
            champs.update(arguments)
            with self.subTest(arguments=list(arguments)), self.assertRaises(ErreurJournal):
                enregistrement_intention(enveloppe(), **champs)

    def test_champs_obligatoires_exacts_du_contrat(self):
        attendus = {
            TypeEnregistrement.CLOTURE: {'strategie', 'symbole', 'instrument', 'bougie', 'indicateurs', 'etat_strategie',
                                         'signal', 'motif', 'detail', 'permission', 'version_calendrier', 'snapshot_ia'},
            TypeEnregistrement.INTENTION: {'cle', 'empreinte_cle', 'strategie', 'symbole', 'sens', 'tentatives', 'issue',
                                           'motif', 'detail', 'cout_ia_usd'}}
        self.assertEqual({t: set(c) for t, c in CHAMPS_OBLIGATOIRES.items() if c}, attendus)
        self.assertEqual(set(CHAMPS_OBLIGATOIRES), set(TypeEnregistrement))
        complet = dict(cloture(AbsenceDeSignal('LONDON_V3', 'EURUSD', 1_800_000, 'NO_SETUP', 'PAS_DE_CASSURE')).contenu)
        for champ in sorted(attendus[TypeEnregistrement.CLOTURE]):
            with self.subTest(champ=champ), self.assertRaises(ErreurJournal):
                enregistrement('CLOTURE', enveloppe(), {k: v for k, v in complet.items() if k != champ})

    def test_generique_et_refus(self):
        self.assertEqual(enregistrement('ALERTE', enveloppe(), {'code': 'X'}).type, TypeEnregistrement.ALERTE)
        for type_, contenu in (('INCONNU', {}), ('CLOTURE', {'symbole': 'EURUSD'}), ('ALERTE', {'numero': 3}),
                               ('ALERTE', {'motif': 'NO_SETUP', 'detail': 'TROU_ACTIF'}), ('ALERTE', {1: 'x'}),
                               ('ALERTE', {'x': float('nan')}), ('ALERTE', {'x': Decimal('Infinity')}),
                               ('ALERTE', {'x': object()}), ('ALERTE', ['x'])):
            with self.subTest(type_=type_, contenu=contenu), self.assertRaises(ErreurJournal):
                enregistrement(type_, enveloppe(), contenu)


class TestSerialisation(unittest.TestCase):
    def test_forme_canonique(self):
        e = enregistrement('COMPTE', enveloppe(), {'fonds': Decimal('100.00'), 'z': (1, 2), 'é': 'été', 'r': Decimal('1E-8')})
        ligne = serialiser(e)
        self.assertNotIn(' ', ligne)
        self.assertIn('"fonds":"100.00"', ligne)
        self.assertIn('"r":"0.00000001"', ligne)
        self.assertIn('"é":"été"', ligne)
        self.assertIn('"z":[1,2]', ligne)
        objet = json.loads(ligne)
        self.assertEqual(list(objet), sorted(objet))
        self.assertEqual(json.dumps(objet, ensure_ascii=False, sort_keys=True, separators=(',', ':')), ligne)

    def test_refus(self):
        with self.assertRaises(ErreurJournal):
            serialiser({'type': 'ALERTE'})


if __name__ == '__main__':
    unittest.main()
