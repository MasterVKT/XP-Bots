"""Segment S5 : exécution papier minimale, et ordre de la boucle de rejeu (exécutions avant décisions)."""
from decimal import Decimal
import unittest

from xpbots.execution.squelette import CommandeCloture, CommandeEntree
from xpbots.noyau.squelette import Tick
from xpbots.orchestration.squelette import SortieMoteur
from xpbots.rejeu.squelette import (ClotureExecutee, ExecutionPapierMinimale, RefusCommande, Remplissage,
                                    SortieProtection, rejouer)

VOLUME = Decimal('0.01')


def tick(instant, bid, ask, symbole='EURUSD'):
    return Tick(symbole, symbole, instant, instant, bid, ask)


class TestExecutionPapier(unittest.TestCase):
    def test_entree_au_tick_suivant_achat_ask_vente_bid(self):
        execution = ExecutionPapierMinimale()
        execution.soumettre([CommandeEntree('a', 'EURUSD', 'ACHAT', VOLUME, 1.0, 2.0),
                             CommandeEntree('v', 'EURUSD', 'VENTE', VOLUME, 2.0, 1.0)])
        self.assertEqual(execution.sur_tick(tick(1, 1.5, 1.6)),
                         (Remplissage('a', 'EURUSD', 'ACHAT', VOLUME, 1.6, 1),
                          Remplissage('v', 'EURUSD', 'VENTE', VOLUME, 1.5, 1)))
        self.assertEqual(execution.positions_ouvertes, ('a', 'v'))

    def test_protections_sur_bid_pour_achat_et_ask_pour_vente(self):
        cas = [('ACHAT', 1.0, 2.0, tick(2, 0.9, 1.6), 'SL', 0.9), ('ACHAT', 1.0, 2.0, tick(2, 2.1, 2.2), 'TP', 2.1),
               ('VENTE', 2.0, 1.0, tick(2, 1.5, 2.05), 'SL', 2.05), ('VENTE', 2.0, 1.0, tick(2, 0.8, 0.9), 'TP', 0.9),
               ('ACHAT', 1.0, 2.0, tick(2, 1.95, 2.05), None, None)]
        for sens, sl, tp, declencheur, cause, prix in cas:
            with self.subTest(sens=sens, cause=cause):
                execution = ExecutionPapierMinimale()
                execution.soumettre([CommandeEntree('k', 'EURUSD', sens, VOLUME, sl, tp)])
                execution.sur_tick(tick(1, 1.5, 1.6))
                attendu = (SortieProtection('k', cause, prix, 2),) if cause else ()
                self.assertEqual(execution.sur_tick(declencheur), attendu)

    def test_protections_actives_a_partir_du_tick_suivant_le_remplissage(self):
        execution = ExecutionPapierMinimale()
        execution.soumettre([CommandeEntree('k', 'EURUSD', 'ACHAT', VOLUME, 1.55, 2.0)])
        self.assertEqual(len(execution.sur_tick(tick(1, 1.5, 1.6))), 1)
        self.assertEqual(execution.sur_tick(tick(2, 1.5, 1.6)), (SortieProtection('k', 'SL', 1.5, 2),))

    def test_cloture_et_refus(self):
        execution = ExecutionPapierMinimale()
        execution.soumettre([CommandeEntree('k', 'EURUSD', 'ACHAT', VOLUME, 1.0, 2.0)])
        execution.sur_tick(tick(1, 1.5, 1.6))
        execution.soumettre([CommandeCloture('k', 'TEST'), CommandeCloture('inconnue', 'TEST')])
        self.assertEqual(execution.sur_tick(tick(2, 1.4, 1.5)),
                         (ClotureExecutee('k', 1.4, 2), RefusCommande('inconnue', 'POSITION_INCONNUE')))
        execution.soumettre([CommandeEntree('d', 'EURUSD', 'ACHAT', VOLUME, 1.0, 2.0)] * 2)
        self.assertEqual(execution.sur_tick(tick(3, 1.5, 1.6))[1], RefusCommande('d', 'CLE_DEJA_OUVERTE'))
        with self.assertRaises(TypeError):
            execution.soumettre(['ordre'])

    def test_autre_symbole_attend_son_tick(self):
        execution = ExecutionPapierMinimale()
        execution.soumettre([CommandeEntree('g', 'GBPUSD', 'ACHAT', VOLUME, 1.0, 2.0)])
        self.assertEqual(execution.sur_tick(tick(1, 1.5, 1.6)), ())
        self.assertEqual(execution.sur_tick(tick(2, 1.3, 1.4, 'GBPUSD'))[0].prix, 1.4)


class MoteurQuiOrdonne:
    """Doublure du contrat `traiter_tick` : demande une entrée au premier tick, journalise chaque appel."""

    def __init__(self):
        self.appels = []

    def traiter_tick(self, t):
        self.appels.append(t.instant_ms)
        commandes = (CommandeEntree('k', 'EURUSD', 'ACHAT', VOLUME, 1.0, 2.0),) if t.instant_ms == 1 else ()
        return SortieMoteur(({'numero': len(self.appels)},), commandes)


class TestBoucleDeRejeu(unittest.TestCase):
    def test_execution_avant_moteur_et_remplissage_au_tick_suivant(self):
        moteur = MoteurQuiOrdonne()
        resultat = rejouer([tick(1, 1.5, 1.6), tick(2, 1.5, 1.7)], moteur, ExecutionPapierMinimale())
        self.assertEqual(resultat.nombre_ticks, 2)
        self.assertEqual(moteur.appels, [1, 2])
        self.assertEqual(resultat.reponses, (Remplissage('k', 'EURUSD', 'ACHAT', VOLUME, 1.7, 2),))
        self.assertEqual(len(resultat.enregistrements), 2)


if __name__ == '__main__':
    unittest.main()
