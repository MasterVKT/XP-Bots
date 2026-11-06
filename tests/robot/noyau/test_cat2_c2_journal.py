"""Catégorie 2, couche 2 (journal) : jonction sur le bloc réel du noyau {0 → 2}, par chemins représentatifs."""
from decimal import Decimal
import json
import unittest

from robot.outils.configuration import octets_exports
from robot.outils.profils import champs_instrument
from xpbots.noyau.c0a_temps import aligner, instant_depuis_iso
from xpbots.noyau.c0b_nombres import Arrondi, arrondir_sur_grille
from xpbots.noyau.c0c_configuration import charger_configuration_figee
from xpbots.noyau.c1a_marche import Bougie, Tick, cotation_depuis_tick
from xpbots.noyau.c1b_instrument import construire_profil_instrument
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, CleIntention, Issue, Sens
from xpbots.noyau.c2_journal import Enveloppe, empreintes_regles, enregistrement_cloture, enregistrement_intention, serialiser


class TestJonctionJournal(unittest.TestCase):
    def setUp(self):
        self.configuration = charger_configuration_figee(*octets_exports())
        self.commun = self.configuration.technique.commun
        self.duree = self.commun.timeframe_seconds * 1000

    def enveloppe(self, numero, instant):
        return Enveloppe('dep-1', 'REFERENCE', 'REJEU', numero, instant, empreintes_regles(self.configuration))

    def test_cloture_canonique_de_bout_en_bout_du_noyau(self):
        frontiere = instant_depuis_iso('2026-07-15T08:15:00Z')
        debut = aligner(frontiere - 1, self.duree)
        bougie = Bougie('EURUSD', debut, self.duree, 1.1, 1.1004, 1.0996, 1.1002, 4, True, None, frontiere)
        profil = construire_profil_instrument(champs_instrument(), self.commun).profil
        absence = AbsenceDeSignal(self.configuration.technique.london['strategy_id'], 'EURUSD', bougie.fin_ms,
                                  'OUTSIDE_SESSION', 'HORS_FENETRE')
        ligne = serialiser(enregistrement_cloture(self.enveloppe(1, frontiere), bougie=bougie, resultat=absence,
                                                  profil=profil, indicateurs={}, etat_strategie={}, permission=None,
                                                  version_calendrier=None, snapshot_ia=None))
        objet = json.loads(ligne)
        self.assertEqual(serialiser(enregistrement_cloture(self.enveloppe(1, frontiere), bougie=bougie, resultat=absence,
                                                           profil=profil, indicateurs={}, etat_strategie={},
                                                           permission=None, version_calendrier=None,
                                                           snapshot_ia=None)), ligne, 'sérialisation déterministe')
        self.assertEqual(objet['empreinte_regles']['technique'], self.configuration.technique.empreinte_canonique)
        self.assertEqual((objet['instrument']['tick_size'], objet['strategie']), ('0.00001', 'LONDON_V3'))

    def test_intention_avec_cotation_sur_grille(self):
        instant = instant_depuis_iso('2026-07-15T08:15:00.120Z')
        profil = construire_profil_instrument(champs_instrument(), self.commun).profil
        cotation = cotation_depuis_tick(Tick('EURUSD', 'EURUSDmicro', instant, instant, 1, 1.1002, 1.10032),
                                        profil.tick_size)
        stop = arrondir_sur_grille(1.09951, profil.tick_size, Arrondi.BAS)
        cle = CleIntention('dep-1', 'LONDON_V3', 'EURUSD', instant_depuis_iso('2026-07-15T08:15:00Z'), Sens.ACHAT)
        ligne = serialiser(enregistrement_intention(
            self.enveloppe(2, instant), cle=cle, longueur_empreinte=12,
            tentatives=[{'bid': cotation.bid, 'ask': cotation.ask, 'spread': cotation.spread, 'stop': stop}],
            issue=Issue(cle, 'REFUSEE', instant, 'SPREAD_CAP'), cout_ia_usd=None))
        tentative = json.loads(ligne)['tentatives'][0]
        self.assertEqual((tentative['spread'], tentative['stop']), ('0.00012', '1.09951'))
        self.assertEqual(Decimal(tentative['ask']) - Decimal(tentative['bid']), Decimal('0.00012'))


if __name__ == '__main__':
    unittest.main()
