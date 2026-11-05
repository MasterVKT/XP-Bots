"""Couche 2 — `etat_indicateurs` : disponibilité, A_t, préchauffage, empreinte, export, persistance."""
import dataclasses
import unittest
from decimal import Decimal

from robot.doublures.stockage_memoire import StockageMemoire
from robot.fixtures.series import M15, bougies_directes
from xpbots.donnees_temps.c1c_indicateurs import ValeurInvalide
from xpbots.donnees_temps.c2_etat_indicateurs import (EtatIncompatible, EtatIndicateursSymbole,
                                                      PrechargementInsuffisant, SpecIndicateurs)
from xpbots.noyau.config import charger_bundle_technique

T0 = 1793664000000


def spec_config():
    b = charger_bundle_technique().donnees
    periodes = tuple(b['ema']['ema_periods'])
    return SpecIndicateurs(periodes, b['ema']['rsi_period'], b['common']['atr_period'],
                           ((max(periodes), b['ema']['slow_ema_slope_lookback_bars']),),
                           b['common']['warmup_closed_m15_bars'])


def spec_courte():
    return SpecIndicateurs((3, 5), 4, 3, ((5, 2),), 10)


class TestDisponibilite(unittest.TestCase):
    def test_chronologie_des_indicateurs(self):
        etat = EtatIndicateursSymbole(spec_courte())
        cles = [set(etat.appliquer(b).valeurs) for b in bougies_directes('EURUSD', T0, 10)]
        self.assertEqual(cles[0], {'tr'})
        self.assertIn('ema_3', cles[2])
        self.assertIn('atr_3', cles[2])
        self.assertNotIn('rsi_4', cles[3])
        self.assertIn('rsi_4', cles[4])
        self.assertIn('ema_5', cles[4])
        self.assertNotIn('ema_5_t_moins_2', cles[5])
        self.assertIn('ema_5_t_moins_2', cles[6])

    def test_ema_decalee_et_a_t(self):
        etat = EtatIndicateursSymbole(spec_courte())
        sorties = [etat.appliquer(b) for b in bougies_directes('EURUSD', T0, 12)]
        for i in range(6, 12):
            self.assertEqual(sorties[i].valeurs['ema_5_t_moins_2'], sorties[i - 2].valeurs['ema_5'])
        self.assertIsNone(sorties[2].a_t)
        for i in range(3, 12):
            self.assertEqual(sorties[i].a_t, sorties[i - 1].valeurs['atr_3'])

    def test_pret_a_la_bougie_du_prechauffage(self):
        etat = EtatIndicateursSymbole(spec_courte())
        sorties = [etat.appliquer(b) for b in bougies_directes('EURUSD', T0, 11)]
        self.assertEqual([s.compte for s in sorties][:3], [1, 2, 3])
        etat2 = EtatIndicateursSymbole(spec_courte())
        drapeaux = []
        for b in bougies_directes('EURUSD', T0, 11):
            etat2.appliquer(b)
            drapeaux.append(etat2.pret)
        self.assertEqual(drapeaux.index(True), 9)  # la 10e bougie (préchauffage 10) est la première décidable

    def test_spec_de_la_configuration(self):
        s = spec_config()
        self.assertEqual(s.prechauffage, charger_bundle_technique().donnees['common']['warmup_closed_m15_bars'])
        with self.assertRaises(ValueError):
            dataclasses.replace(s, prechauffage=40)
        for mauvaise in (lambda: SpecIndicateurs((3, 3), 4, 3, (), 10), lambda: SpecIndicateurs((3,), 0, 3, (), 10),
                         lambda: SpecIndicateurs((3,), 4, 3, ((4, 2),), 10),
                         lambda: SpecIndicateurs((3,), 4, 3, ((3, 0),), 10)):
            with self.assertRaises(ValueError):
                mauvaise()


class TestPrechargementEtEmpreinte(unittest.TestCase):
    def test_empreinte_deterministe_et_sensible(self):
        bougies = bougies_directes('EURUSD', T0, 12)
        a, b = EtatIndicateursSymbole(spec_courte()), EtatIndicateursSymbole(spec_courte())
        ea, eb = a.precharger(bougies), b.precharger(bougies)
        self.assertEqual(ea, eb)
        self.assertEqual((ea.premiere_ouverture_ms, ea.nombre), (T0, 10))
        self.assertEqual(ea.derniere_cloture_ms, T0 + 10 * M15)
        meme_ohlc = list(bougies)
        meme_ohlc[3] = dataclasses.replace(bougies[3], nb_ticks=bougies[3].nb_ticks + 1)
        self.assertEqual(EtatIndicateursSymbole(spec_courte()).precharger(meme_ohlc), ea)  # l'empreinte porte sur l'OHLC
        autre_haut = list(bougies)
        autre_haut[3] = dataclasses.replace(bougies[3], h=bougies[3].h + Decimal('0.00001'))
        self.assertNotEqual(EtatIndicateursSymbole(spec_courte()).precharger(autre_haut).sha256, ea.sha256)

    def test_prechargement_refuse(self):
        with self.assertRaises(PrechargementInsuffisant):
            EtatIndicateursSymbole(spec_courte()).precharger(bougies_directes('EURUSD', T0, 9))
        etat = EtatIndicateursSymbole(spec_courte())
        etat.appliquer(bougies_directes('EURUSD', T0, 1)[0])
        with self.assertRaises(EtatIncompatible):
            etat.precharger(bougies_directes('EURUSD', T0 + M15, 10))

    def test_bougies_refusees(self):
        etat = EtatIndicateursSymbole(spec_courte())
        bougies = bougies_directes('EURUSD', T0, 2)
        etat.appliquer(bougies[1])
        with self.assertRaises(ValeurInvalide):
            etat.appliquer(bougies[0])  # rétrograde
        with self.assertRaises(ValeurInvalide):
            etat.appliquer(dataclasses.replace(bougies_directes('EURUSD', T0 + 5 * M15, 1)[0], valide=False))

    def test_reinitialisation(self):
        etat = EtatIndicateursSymbole(spec_courte())
        etat.precharger(bougies_directes('EURUSD', T0, 10))
        etat.reinitialiser()
        self.assertEqual((etat.compte, etat.empreinte_prechargement, etat.derniere_cloture_ms), (0, None, None))
        self.assertEqual(set(etat.appliquer(bougies_directes('EURUSD', T0, 1)[0]).valeurs), {'tr'})


class TestPersistance(unittest.TestCase):
    def test_export_import_a_l_identique(self):
        bougies = bougies_directes('EURUSD', T0, 30)
        continu, coupe = EtatIndicateursSymbole(spec_courte()), EtatIndicateursSymbole(spec_courte())
        attendues = [continu.appliquer(b) for b in bougies]
        obtenues = [coupe.appliquer(b) for b in bougies[:7]]
        coupe = EtatIndicateursSymbole.importer(spec_courte(), coupe.exporter())
        obtenues += [coupe.appliquer(b) for b in bougies[7:]]
        self.assertEqual(obtenues, attendues)
        self.assertEqual(coupe.empreinte_prechargement, continu.empreinte_prechargement)

    def test_stockage_et_empreinte_attendue(self):
        stockage = StockageMemoire()
        self.assertIsNone(EtatIndicateursSymbole.restaurer(spec_courte(), stockage, 'EURUSD'))
        etat = EtatIndicateursSymbole(spec_courte())
        empreinte = etat.precharger(bougies_directes('EURUSD', T0, 10))
        etat.sauvegarder(stockage, 'EURUSD')
        restaure = EtatIndicateursSymbole.restaurer(spec_courte(), stockage, 'EURUSD', empreinte.sha256)
        self.assertEqual(restaure.exporter(), etat.exporter())
        with self.assertRaises(EtatIncompatible):
            EtatIndicateursSymbole.restaurer(spec_courte(), stockage, 'EURUSD', '0' * 64)
        with self.assertRaises(EtatIncompatible):
            EtatIndicateursSymbole.restaurer(SpecIndicateurs((3, 5), 4, 3, ((5, 2),), 11), stockage, 'EURUSD')
        stockage.ecrire('corrompu', b'{"schema":')
        with self.assertRaises(EtatIncompatible):
            EtatIndicateursSymbole.restaurer(spec_courte(), stockage, 'corrompu')

    def test_import_incoherent(self):
        etat = EtatIndicateursSymbole(spec_courte())
        for b in bougies_directes('EURUSD', T0, 8):
            etat.appliquer(b)
        export = etat.exporter()
        for altere in (dict(export, schema='autre'), dict(export, compte=-1), dict(export, compte=True),
                       dict(export, historiques=[[float('nan')]]), dict(export, ema=[]),
                       {k: v for k, v in export.items() if k != 'rsi'}):
            with self.subTest(cle=sorted(set(export) ^ set(altere)) or 'valeur'), self.assertRaises(EtatIncompatible):
                EtatIndicateursSymbole.importer(spec_courte(), altere)


if __name__ == '__main__':
    unittest.main()
