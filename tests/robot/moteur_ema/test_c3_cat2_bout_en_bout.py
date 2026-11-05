"""Couche 3, catégorie 2 — bloc réel {donnees-temps → moteur-ema} : équivalence avec la référence, causalité C11.1,
changement d'heure et absence d'entrée dominicale C11.4, fenêtre S01.1, trou C03.6.

Ticks synthétiques reproduisant des bougies à tendances → `PipelineMarche` → `MoteurEMA` ; chaque signal est
refusé (la référence n'a ni fill ni compteur), ce qui impose le cooldown d'une clôture comme `ema_setups`.
"""
import math
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from robot.doublures.stockage_memoire import StockageMemoire
from robot.fixtures.series import M15, bougies_tendances, ticks_depuis_bougies
from robot.moteur_ema.outils_ema import BUNDLE, P
from robot.moteur_ema.reference_ema import REFERENCE_DISPONIBLE, cadre_reference, setups_reference
from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances, charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c2_etat_indicateurs import SpecIndicateurs
from xpbots.donnees_temps.c3_pipeline import PipelineMarche
from xpbots.moteur_ema.c3_moteur import MoteurEMA
from xpbots.noyau.decisions import CleIntention, MotifRefus, Refuse
from xpbots.noyau.marche import BougieEnrichie

TECHNIQUE = charger_parametres_techniques(BUNDLE)
SESSIONS = SessionsLondres(TECHNIQUE)
TICK = Decimal('0.00001')
SPEC = SpecIndicateurs(P.periodes_ema, P.periode_rsi, TECHNIQUE.periode_atr,
                       ((max(P.periodes_ema), P.decalage_pente),), TECHNIQUE.prechauffage_m15)
DEBUT = int(datetime(2026, 10, 12, tzinfo=timezone.utc).timestamp() * 1000)  # lundi ; heure d'été le 25 octobre
NB = 4000


def rejouer(ticks, fin, debut=DEBUT, retirer=None):
    """Pipeline puis moteur ; `retirer` = intervalle [a, b) de ticks perdus avec couverture interrompue."""
    calendrier = CalendrierSeances('EURUSD', ((debut, fin + M15),), debut, fin + M15)
    pipeline = PipelineMarche('EURUSD', TECHNIQUE.periode_m15_s, calendrier, SESSIONS, SPEC, debut)
    moteur = MoteurEMA(P, SESSIONS, {'EURUSD': TICK}, StockageMemoire())
    transitions = [(debut, True)] + ([(retirer[0], False), (retirer[1], True)] if retirer else [])
    resultats = []

    def traiter(sorties):
        for sortie in sorties:
            if not isinstance(sortie, BougieEnrichie):
                moteur.sur_evenement_donnees(sortie)
                continue
            r = moteur.sur_cloture(sortie)
            resultats.append((sortie, r))
            if r.signal is not None:
                moteur.appliquer_issue(CleIntention.du_signal('test', r.signal),
                                       Refuse(MotifRefus.FUNDAMENTAL_INVALID, r.signal.cloture_ms))

    for tick in ticks:
        if retirer and retirer[0] <= tick.instant.ms < retirer[1]:
            continue
        while transitions and transitions[0][0] <= tick.instant.ms:
            traiter(pipeline.sur_couverture(*transitions.pop(0)))
        traiter(pipeline.sur_horloge(tick.instant.ms))
        traiter(pipeline.sur_tick(tick))
    traiter(pipeline.terminer(fin))
    return resultats


def signaux(resultats):
    return [{'cloture_ms': r.signal.cloture_ms, 'sens': int(r.signal.sens), 'cloture_bid': float(r.signal.cloture_bid),
             'a_t': r.signal.a_t, 'b_sl': r.signal.b_sl, 'age': r.signal.etat_detecteur['age_repli']}
            for _, r in resultats if r.signal is not None]


def proches(obtenus, attendus):
    if len(obtenus) != len(attendus):
        return False
    for o, a in zip(obtenus, attendus):
        if (o['cloture_ms'], o['sens'], o['cloture_bid'], o['age']) != (a['cloture_ms'], a['sens'],
                                                                      a['cloture_bid'], a['age']):
            return False
        if not (math.isclose(o['a_t'], a['a_t'], rel_tol=1e-12) and math.isclose(o['b_sl'], a['b_sl'],
                                                                                   rel_tol=1e-12)):
            return False
    return True


class TestBoutEnBout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bougies = bougies_tendances('EURUSD', DEBUT, NB, graine=1)
        cls.ticks = ticks_depuis_bougies(cls.bougies)
        cls.fin = DEBUT + NB * M15
        cls.resultats = rejouer(cls.ticks, cls.fin)

    def test_bougies_identiques_aux_bougies_sources(self):
        produites = [(b.bougie.o, b.bougie.h, b.bougie.l, b.bougie.c) for b, _ in self.resultats]
        self.assertEqual(produites, [(b.o, b.h, b.l, b.c) for b in self.bougies])

    @unittest.skipUnless(REFERENCE_DISPONIBLE, 'numpy et pandas requis par reference.technical')
    def test_signaux_identiques_a_la_reference(self):
        attendus = setups_reference(cadre_reference(self.bougies), TICK)
        obtenus = signaux(self.resultats)
        self.assertGreater(len(attendus), 20)
        self.assertTrue(proches(obtenus, attendus), (obtenus[:3], attendus[:3]))

    def test_fenetre_et_jours_sur_le_changement_d_heure(self):
        heures, avant, apres = set(), 0, 0
        changement = int(datetime(2026, 10, 25, 1, tzinfo=timezone.utc).timestamp() * 1000)
        for b, r in self.resultats:
            if r.signal is None:
                continue
            ouverture, cloture = SESSIONS.local(b.bougie.ouverture_ms), SESSIONS.local(b.bougie.cloture_ms)
            self.assertLess(cloture.weekday(), 5)  # aucune entrée le week-end, dimanche compris
            self.assertTrue(ouverture.time() >= P.heures[0] and cloture.time() < P.heures[1])
            heures.add(cloture.utcoffset())
            avant += b.bougie.cloture_ms < changement
            apres += b.bougie.cloture_ms >= changement
        self.assertEqual(len(heures), 2)  # signaux en heure d'été (UTC+1) et d'hiver (UTC)
        self.assertGreater(avant * apres, 0)

    def test_motifs_et_cooldown(self):
        motifs = {r.motif for _, r in self.resultats if r.motif is not None}
        self.assertTrue({MotifRefus.WARMUP, MotifRefus.OUTSIDE_SESSION, MotifRefus.NO_SETUP} <= motifs)
        rangs = [i for i, (_, r) in enumerate(self.resultats) if r.signal is not None]
        for i in rangs:  # la clôture suivante est ignorée (cooldown), ou hors fenêtre après 15:45 (tout effacé)
            suivante = self.resultats[i + 1][1]
            attendue = 'HORS_FENETRE' if suivante.motif is MotifRefus.OUTSIDE_SESSION else 'IGNOREE'
            self.assertEqual(suivante.etat_detecteur['transition'], attendue)
        self.assertTrue(any(self.resultats[i + 1][1].etat_detecteur['transition'] == 'IGNOREE' for i in rangs))

    def test_c11_1_causalite(self):
        coupure = DEBUT + 2600 * M15
        partiel = rejouer([t for t in self.ticks if t.instant.ms < coupure], coupure)
        self.assertEqual([(b, r) for b, r in partiel], self.resultats[:len(partiel)])
        self.assertEqual(len(partiel), 2600)

    def test_trou_efface_le_repli_et_bloque(self):
        # Couverture perdue pendant une bougie : aucune décision sur elle, armements et replis effacés.
        rang = next(i for i, (_, r) in enumerate(self.resultats) if r.signal is not None)
        ouverture = self.resultats[rang - 1][0].bougie.ouverture_ms
        resultats = rejouer(self.ticks, self.fin, retirer=(ouverture + 100_000, ouverture + 300_000))
        par_ouverture = {b.bougie.ouverture_ms: r for b, r in resultats}
        self.assertIs(par_ouverture[ouverture].motif, MotifRefus.DATA_GAP)
        self.assertEqual(par_ouverture[ouverture].etat_detecteur['etat'], 'IDLE')
        self.assertIsNone(par_ouverture[ouverture + M15].signal)  # la reprise n'a plus de repli


if __name__ == '__main__':
    unittest.main()
