"""Catégorie 2, couche 3 : bloc réel {0a → 3} sur des journées de Londres fabriquées, comparé à la référence."""
from datetime import date, time, timedelta
import json
import math
import unittest

import pandas as pd

from reference.technical import LONDON_CFG, add_indicators, local_decision_in_window
from robot.outils.configuration import configuration_figee
from robot.outils.fabrique_ticks import bornes_journee_londres, journee_londres
from xpbots.donnees.c0a_types import BougieEnrichie, ChangementTrou, NatureTrou, UniteTemps
from xpbots.donnees.c1c_couverture import RegistreCouverture
from xpbots.donnees.c3_flux import FluxBougies
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

TECHNIQUE = configuration_figee().technique
COMMUN, LONDON = TECHNIQUE.commun, TECHNIQUE.london
M15 = UniteTemps.M15.duree_ms(COMMUN)


def ticks_de_jours(premier: date, nombre: int):
    """Ticks du noyau de `nombre` jours civils de Londres consécutifs (le tick final de chaque jour est retiré,
    sauf le dernier : le premier tick du jour suivant joue le rôle de tick de frontière)."""
    ticks = []
    for i in range(nombre):
        _, fabriques = journee_londres(premier + timedelta(days=i), duree_ms=M15)
        if i < nombre - 1:
            fabriques = fabriques[:-1]
        ticks.extend(fabriques)
    return [Tick(t.symbole, t.symbole, t.instant_ms, t.instant_ms, n, float(t.bid), float(t.ask))
            for n, t in enumerate(ticks)]


def flux_sur(ticks, trous=()):
    debut, fin = ticks[0].instant_fournisseur_ms, ticks[-1].instant_fournisseur_ms + M15
    horaires = HorairesCotation((Intervalle(debut, fin),), (), debut, fin)
    return FluxBougies('EURUSD', TECHNIQUE, horaires, RegistreCouverture.depuis_registre_de_trous(debut, fin, list(trous)))


def evenements(flux, ticks):
    return [e for t in ticks for e in flux.sur_tick(t)]


def comparer_a_add_indicators(cas, enrichies):
    cadre = pd.DataFrame({'O': [e.bougie.ouverture for e in enrichies], 'H': [e.bougie.haut for e in enrichies],
                          'L': [e.bougie.bas for e in enrichies], 'C': [e.bougie.cloture for e in enrichies]},
                         index=pd.to_datetime([e.bougie.debut_ms for e in enrichies], unit='ms', utc=True))
    reference = add_indicators(cadre)
    for i, e in enumerate(enrichies):
        for valeur, attendu in ((e.indicateurs.tr, reference.TR.iloc[i]), (e.indicateurs.atr, reference.ATR.iloc[i]),
                                (e.indicateurs.a, reference.A.iloc[i])):
            if valeur is None:
                cas.assertTrue(math.isnan(attendu), f'bougie {i}')
            else:
                cas.assertTrue(math.isclose(valeur, attendu, rel_tol=1e-12, abs_tol=1e-15), f'bougie {i}')


class TestJonctionFlux(unittest.TestCase):
    def test_semaines_d_hiver_et_d_ete_egales_a_add_indicators_en_m15_et_h1(self):
        for premier in (date(2026, 1, 12), date(2026, 7, 13), date(2026, 3, 27), date(2026, 10, 23)):
            ticks = ticks_de_jours(premier, 4)
            sortie = evenements(flux_sur(ticks), ticks)
            m15 = [e for e in sortie if e.unite is UniteTemps.M15]
            h1 = [e for e in sortie if e.unite is UniteTemps.H1]
            with self.subTest(premier=premier):
                self.assertTrue(all(isinstance(e, BougieEnrichie) and e.bougie.valide for e in sortie))
                debut, _ = bornes_journee_londres(premier)
                _, fin = bornes_journee_londres(premier + timedelta(days=3))
                self.assertEqual(len(m15), (fin - debut) // M15)
                comparer_a_add_indicators(self, m15)
                comparer_a_add_indicators(self, h1)
                attendu = pd.DataFrame({'H': [e.bougie.haut for e in m15], 'L': [e.bougie.bas for e in m15],
                                        'C': [e.bougie.cloture for e in m15]},
                                       index=pd.to_datetime([e.bougie.debut_ms for e in m15], unit='ms', utc=True))
                agrege = attendu.resample('1h', closed='left', label='left').agg({'H': 'max', 'L': 'min', 'C': 'last'})
                agrege = agrege.loc[[pd.Timestamp(e.bougie.debut_ms, unit='ms', tz='UTC') for e in h1]]
                self.assertEqual([(e.bougie.haut, e.bougie.bas, e.bougie.cloture) for e in h1],
                                 list(agrege.itertuples(index=False, name=None)))

    def test_vingt_bougies_de_range_par_jour_ete_et_hiver_et_fenetre_de_decision(self):
        debut_range = time.fromisoformat(LONDON['range_start_local'])
        fin_range = time.fromisoformat(LONDON['range_end_local_exclusive'])
        session = time.fromisoformat(LONDON['session_start_local'])
        fin_entrees = time.fromisoformat(LONDON['entry_end_local_exclusive'])
        for premier in (date(2026, 1, 12), date(2026, 7, 13), date(2026, 3, 27), date(2026, 10, 23)):
            ticks = ticks_de_jours(premier, 4)
            flux = flux_sur(ticks)
            m15 = [e for e in evenements(flux, ticks) if e.unite is UniteTemps.M15]
            for jour in sorted({e.jour_londres for e in m15}):
                du_jour = [e for e in m15 if e.jour_londres == jour]
                range_ = [e for e in du_jour if debut_range <= e.ouverture_locale.time() < fin_range]
                with self.subTest(jour=jour):
                    self.assertEqual(len(range_), LONDON['expected_range_m15_bars'])
                    self.assertEqual([e.bougie.debut_ms for e in range_],
                                     list(flux.calendrier.ouvertures(jour, debut_range, fin_range, M15)))
                    for e in du_jour:
                        attendu = local_decision_in_window(pd.Timestamp(e.bougie.debut_ms, unit='ms', tz='UTC'),
                                                           pd.Timestamp(e.bougie.fin_ms, unit='ms', tz='UTC'), LONDON_CFG)
                        self.assertEqual(flux.calendrier.decision_dans_fenetre(e.bougie.debut_ms, e.bougie.fin_ms,
                                                                               session, fin_entrees), attendu)
                        self.assertEqual(e.ouverture_locale.date(), e.jour_londres)

    def test_trou_suivi_de_recuperation_p03(self):
        ticks = ticks_de_jours(date(2026, 1, 14), 1)
        debut, _ = bornes_journee_londres(date(2026, 1, 14))
        trou = Intervalle(debut + 10 * M15 + 1, debut + 12 * M15 - 1)
        sortie = evenements(flux_sur(ticks, [trou]), ticks)
        m15 = [e for e in sortie if not isinstance(e, BougieEnrichie) or e.unite is UniteTemps.M15]
        changements = [(i, e.nature) for i, e in enumerate(m15) if isinstance(e, ChangementTrou)]
        self.assertEqual([n for _, n in changements], [NatureTrou.DEBUT, NatureTrou.FIN])
        apres = m15[changements[1][0] + 1]
        avant = [e for e in m15[:changements[0][0]] if isinstance(e, BougieEnrichie)][-1]
        self.assertEqual([e.bougie.motif_invalidite for e in m15[changements[0][0] + 1:changements[1][0]]],
                         ['TROU_DONNEES', 'TROU_DONNEES'])
        b, c = apres.bougie, avant.bougie.cloture
        self.assertEqual(apres.indicateurs.tr, max(b.haut - b.bas, abs(b.haut - c), abs(b.bas - c)))
        self.assertEqual(apres.indicateurs.rang, avant.indicateurs.rang + 1)

    def test_prechargement_p10_et_identite_c03_7(self):
        ticks = ticks_de_jours(date(2026, 1, 5), 13)
        flux = flux_sur(ticks)
        sortie = evenements(flux, ticks)
        m15 = [e for e in sortie if e.unite is UniteTemps.M15]
        h1 = [e for e in sortie if e.unite is UniteTemps.H1]
        self.assertGreaterEqual(len(m15), COMMUN.warmup_closed_m15_bars)
        self.assertGreaterEqual(len(h1), COMMUN.warmup_closed_h1_bars)
        self.assertEqual(m15[COMMUN.warmup_closed_m15_bars - 1].indicateurs.rang, COMMUN.warmup_closed_m15_bars - 1)
        self.assertEqual(h1[COMMUN.warmup_closed_h1_bars - 1].indicateurs.rang, COMMUN.warmup_closed_h1_bars - 1)
        decale = flux_sur(ticks[4:])
        evenements(decale, ticks[4:])
        self.assertNotEqual(decale.identite(UniteTemps.M15), flux.identite(UniteTemps.M15),
                            'préchargement différent : initialisation différente')

    def test_reprise_a_travers_plusieurs_jours(self):
        ticks = ticks_de_jours(date(2026, 3, 27), 4)
        continu = flux_sur(ticks)
        attendu = evenements(continu, ticks)
        for coupure in (97, 385, 389):
            premier = flux_sur(ticks)
            sortie = evenements(premier, ticks[:coupure])
            etat = json.loads(json.dumps(premier.exporter_etat(), allow_nan=False))
            debut, fin = ticks[0].instant_fournisseur_ms, ticks[-1].instant_fournisseur_ms + M15
            reprise = FluxBougies.reprendre(etat, TECHNIQUE, HorairesCotation((Intervalle(debut, fin),), (), debut, fin),
                                            RegistreCouverture([Intervalle(debut, fin)]))
            with self.subTest(coupure=coupure):
                self.assertEqual(sortie + evenements(reprise, ticks[coupure:]), attendu)


if __name__ == '__main__':
    unittest.main()
