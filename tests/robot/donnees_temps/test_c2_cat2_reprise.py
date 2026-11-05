"""Couche 2, catégorie 2 — bloc réel {0 → 2} : bougies construites par la couche 1b puis indicateurs persistés."""
import unittest

from robot.doublures.stockage_memoire import StockageMemoire
from robot.fixtures.series import DEBUT_LUNDI, M15, ticks_bougies
from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances
from xpbots.donnees_temps.c1b_bougies import ConstructeurBougies
from xpbots.donnees_temps.c2_etat_indicateurs import EtatIndicateursSymbole, SpecIndicateurs
from xpbots.noyau.config import charger_bundle_technique

NB = 1100


def spec_config():
    b = charger_bundle_technique().donnees
    periodes = tuple(b['ema']['ema_periods'])
    return SpecIndicateurs(periodes, b['ema']['rsi_period'], b['common']['atr_period'],
                           ((max(periodes), b['ema']['slow_ema_slope_lookback_bars']),),
                           b['common']['warmup_closed_m15_bars'])


def bougies_construites(nb=NB):
    fin = DEBUT_LUNDI + (nb + 1) * M15
    constructeur = ConstructeurBougies('EURUSD', 900, CalendrierSeances('EURUSD', ((DEBUT_LUNDI, fin),),
                                                                       DEBUT_LUNDI, fin), DEBUT_LUNDI)
    constructeur.couverture(DEBUT_LUNDI, True)
    clotures = []
    for tick in ticks_bougies('EURUSD', DEBUT_LUNDI, nb):
        clotures += constructeur.ajouter_tick(tick)
    clotures += constructeur.terminer(DEBUT_LUNDI + nb * M15)
    assert all(c.complet for c in clotures) and len(clotures) == nb
    return [c.bougie for c in clotures]


class TestRepriseSurBougiesConstruites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = spec_config()
        cls.bougies = bougies_construites()

    def test_redemarrage_identique_au_flux_continu(self):
        continu = EtatIndicateursSymbole(self.spec)
        attendues = [continu.appliquer(b) for b in self.bougies]
        stockage = StockageMemoire()
        avant = EtatIndicateursSymbole(self.spec)
        obtenues = [avant.appliquer(b) for b in self.bougies[:1037]]
        avant.sauvegarder(stockage, 'EURUSD')
        apres = EtatIndicateursSymbole.restaurer(self.spec, stockage, 'EURUSD',
                                                 avant.empreinte_prechargement.sha256)
        obtenues += [apres.appliquer(b) for b in self.bougies[1037:]]
        self.assertEqual(obtenues, attendues)
        self.assertTrue(apres.pret)
        self.assertEqual(set(attendues[-1].valeurs),
                         {'ema_15', 'ema_25', 'ema_50', 'ema_50_t_moins_4', 'rsi_14', 'atr_14', 'tr'})

    def test_prechargement_puis_flux_identique_au_flux_seul(self):
        seul = EtatIndicateursSymbole(self.spec)
        attendues = [seul.appliquer(b) for b in self.bougies]
        precharge = EtatIndicateursSymbole(self.spec)
        empreinte = precharge.precharger(self.bougies[:self.spec.prechauffage])
        self.assertEqual(empreinte, seul.empreinte_prechargement)
        suite = [precharge.appliquer(b) for b in self.bougies[self.spec.prechauffage:]]
        self.assertEqual(suite, attendues[self.spec.prechauffage:])


if __name__ == '__main__':
    unittest.main()
