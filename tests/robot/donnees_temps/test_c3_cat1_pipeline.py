"""Couche 3 — `pipeline_marche` : statuts, préchargement, trous, récupération, recalcul (R4, R5, R6′), reprise."""
import unittest

from robot.fixtures.series import DEBUT_LUNDI, M15, ticks_bougies
from xpbots.donnees_temps.c0_parametres_seances import CalendrierSeances, charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c2_etat_indicateurs import EtatIndicateursSymbole, SpecIndicateurs
from xpbots.donnees_temps.c3_pipeline import PipelineMarche
from xpbots.noyau.config import charger_bundle_technique
from xpbots.noyau.marche import BougieEnrichie, EvenementDonnees, NatureEvenementDonnees, StatutBougie

T0 = DEBUT_LUNDI
SESSIONS = SessionsLondres(charger_parametres_techniques(charger_bundle_technique()))
SPEC = SpecIndicateurs((3, 5), 4, 3, ((5, 2),), 10)


def seances(fin=T0 + 400 * M15, ouvertures=None):
    return CalendrierSeances('EURUSD', ouvertures or ((T0, fin),), T0, fin)


def ticks(nb=40, graine=5):
    return ticks_bougies('EURUSD', T0, nb, graine=graine)


class Banc:
    """Alimente un pipeline avec des ticks et des transitions de couverture ordonnées, et recueille les sorties."""

    def __init__(self, recuperation=None, debut=T0, etat=None, calendrier=None):
        self.pipeline = PipelineMarche('EURUSD', 900, calendrier or seances(), SESSIONS, SPEC, debut, recuperation,
                                       etat)
        self.sorties = []

    def jouer(self, liste_ticks, transitions=(), fin=None, couverture_initiale=True, debut=T0):
        transitions = sorted(([(debut, True)] if couverture_initiale else []) + list(transitions))
        for tick in liste_ticks:
            while transitions and transitions[0][0] <= tick.instant.ms:
                instant, etablie = transitions.pop(0)
                self.sorties += self.pipeline.sur_couverture(instant, etablie)
            self.sorties += self.pipeline.sur_tick(tick)
        for instant, etablie in transitions:
            self.sorties += self.pipeline.sur_couverture(instant, etablie)
        if fin is not None:
            self.sorties += self.pipeline.terminer(fin)
        return self

    def bougies(self):
        return [s for s in self.sorties if isinstance(s, BougieEnrichie)]

    def evenements(self, nature=None):
        return [s for s in self.sorties if isinstance(s, EvenementDonnees) and (nature is None or s.nature is nature)]

    def statuts(self):
        return [b.statut for b in self.bougies()]


def depuis(bougies, ouverture_ms):
    return [b for b in bougies if b.bougie.ouverture_ms >= ouverture_ms]


def sans_fenetre(liste_ticks, debut, fin):
    return [t for t in liste_ticks if not debut <= t.instant.ms < fin]


def recuperation_depuis(liste_ticks):
    def recuperer(symbole, debut, fin):
        return [t for t in liste_ticks if debut <= t.instant.ms < fin]
    return recuperer


class TestPrechauffage(unittest.TestCase):
    def test_warmup_puis_ok_avec_empreinte(self):
        banc = Banc().jouer(ticks(12), fin=T0 + 12 * M15)
        self.assertEqual(banc.statuts(), [StatutBougie.WARMUP] * 9 + [StatutBougie.OK] * 3)
        rang_evenement = banc.sorties.index(banc.evenements(NatureEvenementDonnees.PRECHARGEMENT)[0])
        self.assertIs(banc.sorties[rang_evenement + 1], banc.bougies()[9])
        empreinte = banc.evenements(NatureEvenementDonnees.PRECHARGEMENT)[0]
        self.assertEqual((empreinte.debut_ms, empreinte.fin_ms, empreinte.details['nombre']),
                         (T0, T0 + 10 * M15, 10))
        self.assertEqual(banc.bougies()[0].jour_londres, SESSIONS.jour_londres(T0 + M15))
        self.assertIsNotNone(banc.bougies()[-1].a_t)


class TestTrous(unittest.TestCase):
    def test_trou_de_couverture_puis_recalcul(self):
        debut, fin = T0 + 15 * M15 + 100, T0 + 15 * M15 + 200
        banc = Banc().jouer(sans_fenetre(ticks(), debut, fin), [(debut, False), (fin, True)], T0 + 40 * M15)
        trou, = banc.evenements(NatureEvenementDonnees.TROU)
        self.assertEqual((trou.debut_ms, trou.fin_ms, trou.details['motif']), (T0 + 15 * M15, T0 + 16 * M15,
                                                                               'COUVERTURE'))
        recalcul, = banc.evenements(NatureEvenementDonnees.RECALCUL)
        self.assertEqual((recalcul.details['motif'], recalcul.details['bougies']), ('RECUPERATION_INDISPONIBLE', 0))
        self.assertEqual(banc.evenements(NatureEvenementDonnees.REINITIALISATION), [])
        statuts = banc.statuts()
        self.assertEqual(statuts[15], StatutBougie.DATA_GAP)
        self.assertEqual(statuts[16:], [StatutBougie.OK] * 24)  # aucun nouveau préchauffage (R6′)
        self.assertEqual(len(banc.evenements(NatureEvenementDonnees.PRECHARGEMENT)), 1)
        self.assertEqual(banc.pipeline.etat.compte, 39)

    def test_recalcul_identique_aux_seules_bougies_valides(self):
        # Référence : mêmes ticks, l'intervalle perdu déclaré fermé officiellement (aucun trou) ; R6′ ne réinvente rien.
        debut, fin = T0 + 15 * M15 + 100, T0 + 15 * M15 + 200
        banc = Banc().jouer(sans_fenetre(ticks(), debut, fin), [(debut, False), (fin, True)], T0 + 40 * M15)
        calendrier = seances(ouvertures=((T0, T0 + 15 * M15), (T0 + 16 * M15, T0 + 400 * M15)))
        reference = Banc(calendrier=calendrier).jouer(sans_fenetre(ticks(), T0 + 15 * M15, T0 + 16 * M15),
                                                      fin=T0 + 40 * M15)
        self.assertEqual(depuis(banc.bougies(), T0 + 16 * M15), depuis(reference.bougies(), T0 + 16 * M15))
        self.assertEqual(banc.pipeline.etat.exporter(), reference.pipeline.etat.exporter())

    def test_intervalle_sans_bid_r4(self):
        banc = Banc().jouer(sans_fenetre(ticks(), T0 + 12 * M15, T0 + 13 * M15), fin=T0 + 40 * M15)
        trou, = banc.evenements(NatureEvenementDonnees.TROU)
        self.assertEqual(trou.details['motif'], 'SANS_BID')
        self.assertEqual(len(banc.bougies()), 39)  # aucun Bid : aucune bougie pour l'intervalle
        self.assertEqual(len(banc.evenements(NatureEvenementDonnees.RECALCUL)), 1)
        self.assertEqual(banc.bougies()[12].statut, StatutBougie.OK)
        self.assertEqual(banc.pipeline.etat.compte, 39)

    def test_trou_pendant_le_prechauffage(self):
        banc = Banc().jouer(sans_fenetre(ticks(30), T0 + 4 * M15, T0 + 5 * M15), fin=T0 + 30 * M15)
        prechargement, = banc.evenements(NatureEvenementDonnees.PRECHARGEMENT)
        # Le préchargement continue sur les bougies valides : dix bougies, l'intervalle perdu exclu (R6′).
        self.assertEqual((prechargement.debut_ms, prechargement.fin_ms, prechargement.details['nombre']),
                         (T0, T0 + 11 * M15, 10))

    def test_bougie_complete_en_trou_sans_couverture(self):
        calendrier = seances(ouvertures=((T0, T0 + 5 * M15 + M15 // 2), (T0 + 6 * M15, T0 + 400 * M15)))
        transitions = [(T0 + 4 * M15 + 100, False), (T0 + 5 * M15, True), (T0 + 5 * M15 + 600_000, False),
                       (T0 + 6 * M15, True)]
        liste = sans_fenetre(sans_fenetre(ticks(10), T0 + 4 * M15 + 100, T0 + 5 * M15),
                             T0 + 5 * M15 + M15 // 2, T0 + 6 * M15)
        banc = Banc(calendrier=calendrier).jouer(liste, transitions, T0 + 10 * M15)
        cinquieme, = [b for b in banc.bougies() if b.bougie.ouverture_ms == T0 + 5 * M15]
        self.assertTrue(cinquieme.bougie.valide)
        self.assertIs(cinquieme.statut, StatutBougie.DATA_GAP)  # entrées bloquées tant que le trou n'est pas résolu


class TestRecuperation(unittest.TestCase):
    def test_recuperation_identique_au_flux_sans_trou(self):
        complets = ticks()
        reference = Banc().jouer(complets, fin=T0 + 40 * M15)
        debut, fin = T0 + 15 * M15 + 100, T0 + 15 * M15 + 200
        banc = Banc(recuperation_depuis(complets)).jouer(sans_fenetre(complets, debut, fin),
                                                         [(debut, False), (fin, True)], T0 + 40 * M15)
        recup, = banc.evenements(NatureEvenementDonnees.RECUPERATION)
        self.assertEqual((recup.debut_ms, recup.fin_ms, recup.details['bougies']), (T0 + 15 * M15, T0 + 16 * M15, 1))
        self.assertEqual(banc.bougies()[15].statut, StatutBougie.DATA_GAP)
        self.assertEqual(banc.bougies()[16:], reference.bougies()[16:])
        self.assertEqual(banc.pipeline.etat.exporter(), reference.pipeline.etat.exporter())

    def test_recuperation_a_une_cloture_complete(self):
        complets = ticks()
        reference = Banc().jouer(complets, fin=T0 + 40 * M15)
        debut = T0 + 15 * M15 + 100
        banc = Banc(recuperation_depuis(complets)).jouer(sans_fenetre(complets, debut, T0 + 16 * M15),
                                                         [(debut, False), (T0 + 16 * M15, True)], T0 + 40 * M15)
        recup, = banc.evenements(NatureEvenementDonnees.RECUPERATION)
        self.assertEqual(recup.details['bougies'], 2)  # l'intervalle du trou et la clôture complète courante
        self.assertEqual(depuis(banc.bougies(), T0 + 16 * M15), depuis(reference.bougies(), T0 + 16 * M15))

    def test_historique_incomplet_ou_invalide(self):
        complets = ticks()
        debut, fin = T0 + 15 * M15 + 100, T0 + 15 * M15 + 200
        for recuperation, motif in (
                (lambda s, d, f: [t for t in complets if d <= t.instant.ms < f and t.instant.ms >= d + M15],
                 'HISTORIQUE_INCOMPLET'),
                (lambda s, d, f: [t for t in complets if t.instant.ms < f], 'HISTORIQUE_INVALIDE')):
            banc = Banc(recuperation).jouer(sans_fenetre(complets, debut, fin), [(debut, False), (fin, True)],
                                            T0 + 40 * M15)
            with self.subTest(motif=motif):
                recalcul, = banc.evenements(NatureEvenementDonnees.RECALCUL)
                self.assertEqual(recalcul.details['motif'], motif)
                self.assertEqual(banc.pipeline.etat.compte, 39)

    def test_recuperation_partielle_r6_prime(self):
        # Trou sur trois intervalles ; l'historique ne rend que l'intervalle du milieu : il est appliqué, seul.
        complets = ticks()
        debut, fin = T0 + 15 * M15 + 100, T0 + 17 * M15 + 200
        milieu = (T0 + 16 * M15, T0 + 17 * M15)
        banc = Banc(lambda s, d, f: [t for t in complets if milieu[0] <= t.instant.ms < milieu[1]]).jouer(
            sans_fenetre(complets, debut, fin), [(debut, False), (fin, True)], T0 + 40 * M15)
        recalcul, = banc.evenements(NatureEvenementDonnees.RECALCUL)
        self.assertEqual((recalcul.debut_ms, recalcul.fin_ms), (T0 + 15 * M15, T0 + 18 * M15))
        self.assertEqual((recalcul.details['motif'], recalcul.details['bougies']), ('HISTORIQUE_INCOMPLET', 1))
        self.assertEqual(banc.pipeline.etat.compte, 38)
        calendrier = seances(ouvertures=((T0, T0 + 15 * M15), (T0 + 16 * M15, T0 + 17 * M15),
                                         (T0 + 18 * M15, T0 + 400 * M15)))
        reference = Banc(calendrier=calendrier).jouer(
            sans_fenetre(sans_fenetre(complets, T0 + 15 * M15, T0 + 16 * M15), T0 + 17 * M15, T0 + 18 * M15),
            fin=T0 + 40 * M15)
        self.assertEqual(banc.pipeline.etat.exporter(), reference.pipeline.etat.exporter())


class TestReprise(unittest.TestCase):
    def test_redemarrage_apres_intervalles_manques(self):
        complets = ticks()
        avant = Banc().jouer([t for t in complets if t.instant.ms < T0 + 20 * M15], fin=T0 + 20 * M15)
        etat = EtatIndicateursSymbole.importer(SPEC, avant.pipeline.etat.exporter())
        reprise = T0 + 23 * M15
        banc = Banc(recuperation_depuis(complets), debut=reprise, etat=etat)
        banc.jouer([t for t in complets if t.instant.ms >= reprise], fin=T0 + 40 * M15, debut=reprise)
        trou = banc.evenements(NatureEvenementDonnees.TROU)[0]
        self.assertEqual((trou.debut_ms, trou.fin_ms, trou.details['motif']), (T0 + 20 * M15, reprise, 'REDEMARRAGE'))
        self.assertEqual(banc.evenements(NatureEvenementDonnees.RECUPERATION)[0].details['bougies'], 4)
        reference = Banc().jouer(complets, fin=T0 + 40 * M15)
        self.assertEqual(banc.bougies()[1:], reference.bougies()[24:])

    def test_redemarrage_pendant_une_fermeture_officielle(self):
        calendrier = seances(ouvertures=((T0, T0 + 20 * M15), (T0 + 30 * M15, T0 + 400 * M15)))
        complets = [t for t in ticks() if not T0 + 20 * M15 <= t.instant.ms < T0 + 30 * M15]
        avant = Banc(calendrier=calendrier).jouer([t for t in complets if t.instant.ms < T0 + 20 * M15],
                                                  fin=T0 + 20 * M15)
        etat = EtatIndicateursSymbole.importer(SPEC, avant.pipeline.etat.exporter())
        banc = Banc(debut=T0 + 30 * M15, etat=etat, calendrier=calendrier)
        banc.jouer([t for t in complets if t.instant.ms >= T0 + 30 * M15], fin=T0 + 40 * M15, debut=T0 + 30 * M15)
        self.assertEqual(banc.evenements(), [])
        self.assertEqual(banc.pipeline.etat.compte, 30)
        self.assertTrue(all(s is StatutBougie.OK for s in banc.statuts()))

    def test_etat_d_une_autre_specification(self):
        with self.assertRaises(ValueError):
            PipelineMarche('EURUSD', 900, seances(), SESSIONS, SPEC, T0,
                           etat=EtatIndicateursSymbole(SpecIndicateurs((3, 5), 4, 3, (), 10)))


if __name__ == '__main__':
    unittest.main()
