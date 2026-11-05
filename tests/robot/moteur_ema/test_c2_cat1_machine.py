"""Couche 2 — `machine_etats_ema` : transitions T1 à T12 (plan maître 7.B), R1, R2, persistance de l'état."""
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal

from robot.moteur_ema.outils_ema import P
from xpbots.moteur_ema.c2_machine_etats import (EtatIncompatible, EtatTechnique, IssueInattendue, MachineEtatsEMA,
                                                NatureTransition, ObservationEMA)
from xpbots.noyau.decisions import MotifRefus, Refuse, Rempli, Sens

E = EtatTechnique
N = NatureTransition
M15 = 900_000
T0 = 1793779200000  # 2026-11-04 08:00 UTC
JOUR = date(2026, 11, 4)
A = 0.001
# Tendance longue : EMA15 > EMA25 > EMA50 et EMA50 > EMA50(t−4).
LONG = dict(e_rapide=1.1010, e_moyenne=1.1005, e_lente=1.1000, e_lente_decalee=1.0995)
COURT = dict(e_rapide=1.0990, e_moyenne=1.0995, e_lente=1.1000, e_lente_decalee=1.1005)
# Bougies types (tendance longue) : armement sans contact, contact sans reprise, repli sans contact, reprise.
ARMEMENT = dict(o=1.1012, h=1.1016, l=1.1011, c=1.1015, tr=0.0005, rsi=55.0)
CONTACT = dict(o=1.1009, h=1.1012, l=1.1004, c=1.1008, tr=0.0008, rsi=45.0)
REPLI = dict(o=1.1013, h=1.1014, l=1.1011, c=1.1012, tr=0.0003, rsi=48.0)
REPRISE = dict(o=1.1006, h=1.1017, l=1.1004, c=1.1016, tr=0.0013, rsi=55.0)
# Tendance courte : armement court sans contact.
ARMEMENT_COURT = dict(o=1.0988, h=1.0989, l=1.0984, c=1.0985, tr=0.0005, rsi=45.0)


class Scenario:
    """Fait avancer une machine clôture par clôture (M15 consécutives d'un même jour, dans la fenêtre)."""

    def __init__(self, machine=None):
        self.machine = machine or MachineEtatsEMA(P)
        self.cloture = T0

    def obs(self, bougie=None, tendance=LONG, **options):
        self.cloture += M15
        valeurs = dict(cloture_ms=self.cloture, jour=JOUR, dans_fenetre=True, exploitable=True, a_t=A)
        valeurs.update(tendance)
        valeurs.update(bougie or ARMEMENT)
        valeurs.update(options)
        if not valeurs['exploitable']:
            valeurs = {k: valeurs[k] for k in ('cloture_ms', 'jour', 'dans_fenetre', 'exploitable')}
        return ObservationEMA(**valeurs)

    def pas(self, bougie=None, tendance=LONG, **options):
        return self.machine.etape(self.obs(bougie, tendance, **options))

    def jusqu_a_reprise(self):
        self.pas(ARMEMENT)
        return self.pas(REPRISE)


def refus(instant):
    return Refuse(MotifRefus.ENVIRONMENT_NOT_READY, instant)


def rempli(instant):
    return Rempli(Decimal('0.01'), Decimal('1.1001'), instant)


class TestT1Armement(unittest.TestCase):
    def test_armement_long_et_court(self):
        s = Scenario()
        t = s.pas(ARMEMENT)
        self.assertEqual((t.nature, t.avant, t.apres, t.tendance), (N.ARMEMENT, E.IDLE, E.ARMED_LONG, Sens.ACHAT))
        s = Scenario()
        self.assertIs(s.pas(ARMEMENT_COURT, COURT).apres, E.ARMED_SHORT)

    def test_bougie_d_armement_jamais_repli_ni_signal(self):
        s = Scenario()
        t = s.pas(REPRISE)  # contact et reprise valides, mais l'état était IDLE
        self.assertEqual((t.nature, t.apres, t.reprise), (N.ARMEMENT, E.ARMED_LONG, None))

    def test_pas_d_armement_sans_tendance_ou_contexte(self):
        s = Scenario()
        self.assertIs(s.pas(ARMEMENT, dict(LONG, e_moyenne=LONG['e_rapide'])).nature, N.AUCUNE)  # EMA égales
        self.assertIs(s.pas(ARMEMENT, dict(LONG, e_lente_decalee=LONG['e_lente'])).nature, N.AUCUNE)  # pente nulle
        self.assertIs(s.pas(dict(ARMEMENT, rsi=49.0)).nature, N.AUCUNE)
        self.assertIs(s.machine.etat, E.IDLE)


class TestT2T3Repli(unittest.TestCase):
    def test_premier_contact_age_un(self):
        s = Scenario()
        s.pas(ARMEMENT)
        t = s.pas(CONTACT)
        self.assertEqual((t.nature, t.apres), (N.CONTACT, E.PULLBACK_LONG))
        self.assertEqual(s.machine.etat_detecteur()['age_repli'], 1)

    def test_armed_sans_contact_reste_arme(self):
        s = Scenario()
        s.pas(ARMEMENT)
        self.assertEqual((s.pas(ARMEMENT).nature, s.machine.etat), (N.AUCUNE, E.ARMED_LONG))

    def test_contact_peut_etre_le_signal(self):
        s = Scenario()
        t = s.jusqu_a_reprise()
        self.assertEqual((t.nature, t.apres, t.reprise.age), (N.REPRISE, E.ATTENTE_ISSUE, 1))

    def test_extremes_de_toutes_les_bougies_signal_compris(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        s.pas(dict(CONTACT, l=1.1002, h=1.1009, o=1.1008, c=1.1003))
        t = s.pas(dict(REPRISE, l=1.1001, o=1.1003))
        self.assertEqual((t.reprise.plus_bas, t.reprise.plus_haut, t.reprise.age), (1.1001, 1.1017, 3))
        self.assertEqual(t.reprise.extreme, 1.1001)

    def test_reprise_sans_nouveau_contact(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        self.assertIs(s.pas(REPLI).nature, N.REPLI)
        t = s.pas(dict(o=1.1012, h=1.1020, l=1.1011, c=1.1019, tr=0.0009, rsi=55.0))  # aucun contact
        self.assertEqual((t.nature, t.reprise.age), (N.REPRISE, 3))

    def test_baisse_temporaire_de_l_ema_rapide(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        t = s.pas(REPLI, dict(LONG, e_rapide=1.1007))  # EMA15 en baisse, ordre et pente conservés
        self.assertEqual((t.nature, t.apres), (N.REPLI, E.PULLBACK_LONG))


class TestT4T5Annulation(unittest.TestCase):
    def test_cloture_au_dela_de_la_limite_annule(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        limite = LONG['e_lente'] - P.depassement_ema_lente_atr * A
        t = s.pas(dict(o=1.1000, h=1.1001, l=limite - 0.0003, c=limite - 0.0001, tr=0.0004, rsi=45.0))
        self.assertEqual((t.nature, t.apres), (N.ANNULATION, E.IDLE))

    def test_meche_sous_l_ema_lente_n_annule_pas(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        t = s.pas(dict(o=1.1005, h=1.1006, l=1.0990, c=1.1001, tr=0.0016, rsi=45.0))
        self.assertEqual((t.nature, t.apres), (N.REPLI, E.PULLBACK_LONG))

    def test_rsi_de_repli_au_seuil_admis_en_dessous_annule(self):
        s = Scenario()
        s.pas(ARMEMENT)
        self.assertIs(s.pas(dict(CONTACT, rsi=P.rsi_repli_long_min)).nature, N.CONTACT)
        self.assertIs(s.pas(dict(CONTACT, rsi=P.rsi_repli_long_min - 0.5)).nature, N.ANNULATION)

    def test_inversion_de_tendance_reamorce_sans_entree(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        t = s.pas(ARMEMENT_COURT, COURT)
        self.assertEqual((t.nature, t.apres, t.reprise), (N.ANNULATION, E.ARMED_SHORT, None))

    def test_age_huit_admis_neuf_annule_puis_reamorce(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        for _ in range(P.age_max_repli - 2):
            s.pas(REPLI)
        temoin = Scenario(MachineEtatsEMA.importer(P, s.machine.exporter()))
        temoin.cloture = s.cloture
        self.assertEqual(temoin.pas(REPRISE).reprise.age, P.age_max_repli)  # âge 8 : signal admis
        s.pas(REPLI)
        t = s.pas(REPRISE)  # âge 9 : annulé ; la bougie réarme sans entrée
        self.assertEqual((t.nature, t.apres, t.reprise), (N.EXPIRATION, E.ARMED_LONG, None))


class TestT6aT9Issues(unittest.TestCase):
    def test_t7_refus_cooldown_d_une_cloture(self):
        s = Scenario()
        t = s.jusqu_a_reprise()
        s.machine.appliquer_issue(refus(s.cloture))
        self.assertIs(s.machine.etat, E.COOLDOWN)
        self.assertEqual((s.pas(ARMEMENT).nature, s.machine.etat), (N.IGNOREE, E.IDLE))
        self.assertEqual(P.clotures_cooldown, 1)  # « exactement la clôture suivante » (S01.2 point 3)
        self.assertIs(s.pas(ARMEMENT).nature, N.ARMEMENT)
        self.assertEqual(t.reprise.sens, Sens.ACHAT)

    def test_t6_repli_consomme(self):
        s = Scenario()
        s.jusqu_a_reprise()
        self.assertIsNone(s.machine.etat_detecteur()['age_repli'])
        self.assertEqual(s.machine.signal_cloture_ms, s.cloture)

    def test_t8_fill_position_possedee_sans_preparation(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.machine.appliquer_issue(rempli(s.cloture + 1200))
        self.assertIs(s.machine.etat, E.OWNED_POSITION)
        self.assertEqual(s.machine.entrees_remplies(JOUR), 1)
        for bougie in (ARMEMENT, CONTACT, REPRISE):
            self.assertEqual((s.pas(bougie).nature, s.machine.etat), (N.POSITION, E.OWNED_POSITION))
        self.assertIs(s.pas(ARMEMENT, dans_fenetre=False).nature, N.POSITION)

    def test_t9_sortie_entre_deux_clotures(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.machine.appliquer_issue(rempli(s.cloture + 1000))
        s.pas(ARMEMENT)
        s.machine.notifier_sortie(s.cloture + 300_000)
        self.assertIs(s.machine.etat, E.COOLDOWN)
        self.assertIs(s.pas(ARMEMENT).nature, N.IGNOREE)  # première clôture strictement postérieure
        self.assertIs(s.pas(ARMEMENT).nature, N.ARMEMENT)

    def test_r1_sortie_exactement_a_une_cloture(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.machine.appliquer_issue(rempli(s.cloture + 1000))
        s.machine.notifier_sortie(s.cloture + M15)  # sortie pile à la prochaine clôture
        t1, t2, t3 = s.pas(ARMEMENT), s.pas(ARMEMENT), s.pas(ARMEMENT)
        self.assertEqual([t1.nature, t2.nature, t3.nature], [N.IGNOREE, N.IGNOREE, N.ARMEMENT])
        self.assertEqual(t1.apres, E.COOLDOWN)  # clôture = sortie : ni préparation ni entrée, non décomptée

    def test_evenements_inattendus(self):
        s = Scenario()
        with self.assertRaises(IssueInattendue):
            s.machine.appliquer_issue(refus(T0))
        with self.assertRaises(IssueInattendue):
            s.machine.notifier_sortie(T0)
        s.jusqu_a_reprise()
        with self.assertRaises(ValueError):
            s.machine.appliquer_issue(refus(s.cloture - 1))
        with self.assertRaises(IssueInattendue):
            s.machine.notifier_sortie(s.cloture)


class TestT10Effacements(unittest.TestCase):
    def preparer(self):
        s = Scenario()
        s.pas(ARMEMENT)
        s.pas(CONTACT)
        return s

    def test_hors_fenetre(self):
        s = self.preparer()
        self.assertEqual((s.pas(REPRISE, dans_fenetre=False).nature, s.machine.etat), (N.HORS_FENETRE, E.IDLE))

    def test_changement_de_jour(self):
        s = self.preparer()
        t = s.pas(REPRISE, jour=date(2026, 11, 5))
        self.assertEqual((t.nature, t.apres), (N.ARMEMENT, E.ARMED_LONG))  # repli effacé ; la bougie réarme

    def test_bougie_inexploitable(self):
        s = self.preparer()
        self.assertEqual((s.pas(exploitable=False).nature, s.machine.etat), (N.DONNEES, E.IDLE))

    def test_trou_efface_armement_et_repli(self):
        s = self.preparer()
        s.machine.effacer()
        self.assertIs(s.machine.etat, E.IDLE)

    def test_cooldown_hors_fenetre_efface_inexploitable_conserve(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.machine.appliquer_issue(refus(s.cloture))
        self.assertIs(s.pas(exploitable=False).nature, N.DONNEES)
        self.assertIs(s.machine.etat, E.COOLDOWN)  # non décompté, comme la référence
        s.machine.effacer()
        self.assertIs(s.machine.etat, E.COOLDOWN)
        self.assertIs(s.pas(ARMEMENT, dans_fenetre=False).nature, N.HORS_FENETRE)
        self.assertIs(s.machine.etat, E.IDLE)


class TestT11Compteur(unittest.TestCase):
    def test_compteur_par_jour_londres_et_persistant(self):
        s = Scenario()
        for _ in range(P.entrees_max_jour):
            s.jusqu_a_reprise()
            s.machine.appliquer_issue(rempli(s.cloture + 100))
            s.machine.notifier_sortie(s.cloture + 200)
            s.pas(ARMEMENT)  # clôture ignorée
        self.assertEqual(s.machine.entrees_remplies(JOUR), P.entrees_max_jour)
        redemarree = MachineEtatsEMA.importer(P, s.machine.exporter())  # un redémarrage ne remet pas à zéro
        self.assertEqual(redemarree.entrees_remplies(JOUR), P.entrees_max_jour)
        self.assertEqual(redemarree.entrees_remplies(date(2026, 11, 5)), 0)  # nouveau jour Londres
        self.assertEqual(redemarree.etat_detecteur()['entrees_jour'], P.entrees_max_jour)

    def test_refus_n_incremente_pas(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.machine.appliquer_issue(refus(s.cloture))
        self.assertEqual(s.machine.entrees_remplies(JOUR), 0)


class TestT12IssueDifferee(unittest.TestCase):
    def test_r2_attente_puis_refus_tardif(self):
        s = Scenario()
        s.jusqu_a_reprise()
        for bougie in (ARMEMENT, CONTACT):
            self.assertEqual((s.pas(bougie).nature, s.machine.etat), (N.ATTENTE, E.ATTENTE_ISSUE))
        s.machine.appliquer_issue(refus(s.cloture + 4000))  # résolu après la clôture courante
        self.assertIs(s.pas(ARMEMENT).nature, N.IGNOREE)  # cooldown à partir de la résolution
        self.assertIs(s.pas(ARMEMENT).nature, N.ARMEMENT)

    def test_r2_fill_tardif(self):
        s = Scenario()
        s.jusqu_a_reprise()
        s.pas(ARMEMENT)
        s.machine.appliquer_issue(rempli(s.cloture + 4000))
        self.assertIs(s.machine.etat, E.OWNED_POSITION)
        self.assertEqual(s.machine.entrees_remplies(JOUR), 1)


class TestPersistance(unittest.TestCase):
    def test_aller_retour_dans_chaque_etat(self):
        s = Scenario()
        etats = []
        for action in (lambda: s.pas(ARMEMENT), lambda: s.pas(CONTACT), lambda: s.pas(REPRISE),
                       lambda: s.machine.appliquer_issue(rempli(s.cloture + 1)),
                       lambda: s.machine.notifier_sortie(s.cloture + 2)):
            action()
            exporte = s.machine.exporter()
            copie = MachineEtatsEMA.importer(P, exporte)
            self.assertEqual(copie.exporter(), exporte)
            etats.append(copie.etat)
        self.assertEqual(etats, [E.ARMED_LONG, E.PULLBACK_LONG, E.ATTENTE_ISSUE, E.OWNED_POSITION, E.COOLDOWN])

    def test_etat_incoherent_refuse(self):
        s = Scenario()
        s.pas(ARMEMENT)
        bon = s.machine.exporter()
        for changements in ({'format': 'autre'}, {'etat': 'INCONNU'}, {'sens': None}, {'sens': -1},
                            {'age': 1}, {'entrees': -1}, {'cooldown_restantes': 0}, {'dernier_jour': '2026-13-01'}):
            with self.subTest(changements=changements), self.assertRaises(EtatIncompatible):
                MachineEtatsEMA.importer(P, dict(bon, **changements))
        with self.assertRaises(EtatIncompatible):
            MachineEtatsEMA.importer(P, {k: v for k, v in bon.items() if k != 'age'})

    def test_observation_validee(self):
        with self.assertRaises(ValueError):
            ObservationEMA(T0, JOUR, True, True, o=1.0)  # valeurs manquantes pour une bougie exploitable
        with self.assertRaises(ValueError):
            replace(Scenario().obs(), a_t=0.0)
        with self.assertRaises(ValueError):
            MachineEtatsEMA(P).etape('bougie')
        ObservationEMA(T0, JOUR, True, False)


if __name__ == '__main__':
    unittest.main()
