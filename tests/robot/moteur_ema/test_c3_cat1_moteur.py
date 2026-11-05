"""Couche 3 — `moteur_ema` : motifs et ordre des traitements, plafond de six fills (T11), persistance, port."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from robot.doublures.stockage_memoire import StockageMemoire
from robot.moteur_ema.outils_ema import BUNDLE, P
from xpbots.donnees_temps.c0_parametres_seances import charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.donnees_temps.c1c_indicateurs import CLE_TR, cle_ema, cle_ema_decalee, cle_rsi
from xpbots.moteur_ema.c2_machine_etats import EtatTechnique, IssueInattendue
from xpbots.moteur_ema.c3_moteur import MoteurEMA
from xpbots.noyau.decisions import CleIntention, MotifRefus, Refuse, Rempli, Sens, Signal
from xpbots.noyau.marche import (Bougie, BougieEnrichie, EvenementDonnees, NatureEvenementDonnees, StatutBougie)
from xpbots.noyau.ports import Strategie

SESSIONS = SessionsLondres(charger_parametres_techniques(BUNDLE))
TICKS = {'EURUSD': Decimal('0.00001'), 'GBPUSD': Decimal('0.00001')}
M15 = 900_000
RAPIDE, MOYENNE, LENTE = P.periodes_ema
A = 0.001
LONG = {cle_ema(RAPIDE): 1.1010, cle_ema(MOYENNE): 1.1005, cle_ema(LENTE): 1.1000,
        cle_ema_decalee(LENTE, P.decalage_pente): 1.0995}
ARMEMENT = ('1.1012', '1.1016', '1.1011', '1.1015', 0.0005, 55.0)
CONTACT = ('1.1009', '1.1012', '1.1004', '1.1008', 0.0008, 45.0)
REPRISE = ('1.1006', '1.1017', '1.1004', '1.1016', 0.0013, 55.0)
# Reprise dont le repli est trop profond : stop au-delà de 2,5 A.
CONTACT_PROFOND = ('1.1009', '1.1012', '1.0980', '1.1008', 0.0032, 45.0)


def ms(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp() * 1000)


def bougie(ouverture_ms, valeurs=ARMEMENT, statut=StatutBougie.OK, symbole='EURUSD', indicateurs=None):
    o, h, l, c, tr, rsi = valeurs  # noqa: E741
    b = Bougie(symbole, M15 // 1000, ouverture_ms, Decimal(o), Decimal(h), Decimal(l), Decimal(c), 4,
               statut is not StatutBougie.DATA_GAP)
    if statut is not StatutBougie.OK:
        return BougieEnrichie(b, statut, {}, None, SESSIONS.jour_londres(b.cloture_ms))
    valeurs_ind = dict(LONG, **{cle_rsi(P.periode_rsi): rsi, CLE_TR: tr}) if indicateurs is None else indicateurs
    return BougieEnrichie(b, statut, valeurs_ind, A, SESSIONS.jour_londres(b.cloture_ms))


class Banc:
    def __init__(self, stockage=None, debut=ms(2026, 11, 4, 9)):
        self.stockage = stockage or StockageMemoire()
        self.moteur = MoteurEMA(P, SESSIONS, TICKS, self.stockage)
        self.ouverture = debut - M15

    def cloture(self, valeurs=ARMEMENT, **options):
        self.ouverture += M15
        return self.moteur.sur_cloture(bougie(self.ouverture, valeurs, **options))

    def signal(self):
        self.cloture(ARMEMENT)
        return self.cloture(REPRISE)

    def cle(self, resultat):
        return CleIntention.du_signal('test', resultat.signal)

    def refuser(self, resultat):
        self.moteur.appliquer_issue(self.cle(resultat), Refuse(MotifRefus.ENVIRONMENT_NOT_READY,
                                                               resultat.signal.cloture_ms))

    def remplir(self, resultat):
        self.moteur.appliquer_issue(self.cle(resultat), Rempli(Decimal('0.01'), Decimal('1.10168'),
                                                               resultat.signal.cloture_ms + 900))


class TestPort(unittest.TestCase):
    def test_conforme_au_port_strategie(self):
        moteur = Banc().moteur
        self.assertIsInstance(moteur, Strategie)
        self.assertEqual(moteur.strategie_id, BUNDLE.donnees['ema']['strategy_id'])
        self.assertEqual(moteur.symboles, ('EURUSD', 'GBPUSD'))

    def test_configuration_invalide(self):
        for ticks in ({}, {'EURUSD': 0.00001}, {'EURUSD': Decimal('0')}, {'': Decimal('0.00001')}):
            with self.subTest(ticks=ticks), self.assertRaises(ValueError):
                MoteurEMA(P, SESSIONS, ticks, StockageMemoire())
        with self.assertRaises(ValueError):
            Banc().moteur.sur_cloture(bougie(ms(2026, 11, 4, 9), symbole='XAUUSD'))


class TestMotifs(unittest.TestCase):
    def test_signal_complet(self):
        banc = Banc()
        r = banc.signal()
        s = r.signal
        self.assertIs(type(s), Signal)
        self.assertEqual((s.strategie, s.symbole, s.sens, s.cloture_bid, s.a_t),
                         (P.strategie_id, 'EURUSD', Sens.ACHAT, Decimal('1.1016'), A))
        tampon = max(float(TICKS['EURUSD']), P.tampon_structurel_atr * A)
        self.assertEqual(s.b_sl, min(1.1004 - tampon, 1.1016 - P.stop_min_atr * A))
        self.assertEqual(s.multiple_objectif, P.multiple_objectif)
        self.assertEqual(s.etat_detecteur['etat'], EtatTechnique.ATTENTE_ISSUE)
        self.assertEqual(s.etat_detecteur['extreme_repli'], 1.1004)
        self.assertEqual(s.etat_detecteur['age_repli'], 1)
        self.assertEqual(r.etat_detecteur, s.etat_detecteur)

    def test_no_setup_et_etat_du_detecteur(self):
        r = Banc().cloture(ARMEMENT)
        self.assertEqual((r.motif, r.etat_detecteur['etat'], r.etat_detecteur['transition']),
                         (MotifRefus.NO_SETUP, EtatTechnique.ARMED_LONG, 'ARMEMENT'))

    def test_statuts_de_donnees(self):
        banc = Banc()
        self.assertIs(banc.cloture(statut=StatutBougie.WARMUP).motif, MotifRefus.WARMUP)
        self.assertIs(banc.cloture(statut=StatutBougie.DATA_GAP).motif, MotifRefus.DATA_GAP)
        self.assertIs(banc.cloture(indicateurs={}).motif, MotifRefus.WARMUP)  # indicateurs indisponibles

    def test_fenetre_de_session(self):
        banc = Banc(debut=ms(2026, 11, 4, 7, 45))  # novembre : Londres = UTC
        self.assertIs(banc.cloture().motif, MotifRefus.OUTSIDE_SESSION)  # ouverte avant 08:00
        self.assertIs(banc.cloture().motif, MotifRefus.NO_SETUP)  # 08:00–08:15 : première clôture possible
        banc = Banc(debut=ms(2026, 11, 4, 15, 30))
        self.assertIs(banc.cloture().motif, MotifRefus.NO_SETUP)  # dernière clôture possible 15:45
        self.assertIs(banc.cloture(REPRISE).motif, MotifRefus.OUTSIDE_SESSION)  # clôture à 16:00 interdite
        banc = Banc(debut=ms(2026, 11, 8, 10))  # dimanche
        self.assertIs(banc.cloture().motif, MotifRefus.OUTSIDE_SESSION)

    def test_stop_trop_large_consomme_et_cooldown(self):
        banc = Banc()
        banc.cloture(ARMEMENT)
        banc.cloture(CONTACT_PROFOND)
        r = banc.cloture(REPRISE)
        self.assertEqual((r.motif, r.etat_detecteur['etat']), (MotifRefus.STOP_TOO_WIDE, EtatTechnique.COOLDOWN))
        self.assertGreater(r.etat_detecteur['distance_stop'], P.stop_max_atr * A)
        self.assertEqual(banc.cloture(ARMEMENT).etat_detecteur['transition'], 'IGNOREE')
        self.assertEqual(banc.cloture(ARMEMENT).etat_detecteur['transition'], 'ARMEMENT')

    def test_position_et_issue_en_attente(self):
        banc = Banc()
        r = banc.signal()
        self.assertIs(banc.cloture(ARMEMENT).motif, MotifRefus.UNKNOWN_ORDER_STATE)  # R2
        banc.remplir(r)
        self.assertIs(banc.cloture(REPRISE).motif, MotifRefus.SYMBOL_BUSY)
        banc.moteur.notifier_sortie('EURUSD', banc.ouverture + M15 + 1)
        self.assertEqual(banc.cloture(ARMEMENT).etat_detecteur['transition'], 'IGNOREE')

    def test_issue_inattendue(self):
        banc = Banc()
        r = banc.signal()
        for cle in (CleIntention('test', 'AUTRE', 'EURUSD', r.signal.cloture_ms, Sens.ACHAT),
                    CleIntention('test', P.strategie_id, 'EURUSD', r.signal.cloture_ms - M15, Sens.ACHAT),
                    CleIntention('test', P.strategie_id, 'EURUSD', r.signal.cloture_ms, Sens.VENTE),
                    CleIntention('test', P.strategie_id, 'GBPUSD', r.signal.cloture_ms, Sens.ACHAT)):
            with self.subTest(cle=cle), self.assertRaises(IssueInattendue):
                banc.moteur.appliquer_issue(cle, Refuse(MotifRefus.SPREAD_CAP, r.signal.cloture_ms))


class TestPlafondJournalier(unittest.TestCase):
    def test_septieme_entree_refusee_puis_nouveau_jour(self):
        banc = Banc()
        for _ in range(P.entrees_max_jour):
            r = banc.signal()
            banc.remplir(r)
            banc.moteur.notifier_sortie('EURUSD', r.signal.cloture_ms + 60_000)  # sortie après le fill
            banc.cloture(ARMEMENT)  # clôture ignorée
        r = banc.signal()
        self.assertEqual((r.signal, r.motif), (None, MotifRefus.DAILY_ENTRY_CAP))
        self.assertEqual(r.etat_detecteur['etat'], EtatTechnique.COOLDOWN)  # repli consommé, cooldown
        self.assertEqual(r.etat_detecteur['entrees_jour'], P.entrees_max_jour)
        lendemain = Banc(banc.stockage, debut=ms(2026, 11, 5, 9))  # redémarrage, puis jour suivant
        self.assertIsNotNone(lendemain.signal().signal)

    def test_refus_ne_compte_pas(self):
        banc = Banc()
        for _ in range(P.entrees_max_jour + 1):
            banc.refuser(banc.signal())
            banc.cloture(ARMEMENT)
        self.assertIsNotNone(banc.signal().signal)


class TestEvenementsEtPersistance(unittest.TestCase):
    def test_trou_efface_le_repli(self):
        banc = Banc()
        banc.cloture(ARMEMENT)
        banc.cloture(CONTACT)
        trou = EvenementDonnees('EURUSD', NatureEvenementDonnees.TROU, banc.ouverture + M15, banc.ouverture,
                                banc.ouverture + M15, {'motif': 'COUVERTURE'})
        banc.moteur.sur_evenement_donnees(trou)
        self.assertIs(banc.moteur.machine('EURUSD').etat, EtatTechnique.IDLE)
        self.assertEqual(banc.cloture(REPRISE).etat_detecteur['transition'], 'ARMEMENT')  # aucune reprise

    def test_autres_evenements_sans_effet(self):
        banc = Banc()
        banc.cloture(ARMEMENT)
        for evenement in (EvenementDonnees('EURUSD', NatureEvenementDonnees.RECALCUL, banc.ouverture),
                          EvenementDonnees('XAUUSD', NatureEvenementDonnees.TROU, banc.ouverture)):
            banc.moteur.sur_evenement_donnees(evenement)
        self.assertIs(banc.moteur.machine('EURUSD').etat, EtatTechnique.ARMED_LONG)

    def test_redemarrage_reprend_le_meme_etat(self):
        banc = Banc()
        banc.cloture(ARMEMENT)
        banc.cloture(CONTACT)
        reprise = Banc(banc.stockage)
        reprise.ouverture = banc.ouverture
        r = reprise.cloture(REPRISE)
        self.assertEqual((r.signal.sens, r.etat_detecteur['age_repli']), (Sens.ACHAT, 2))
        self.assertEqual(banc.stockage.lire(f'moteur_ema/{P.strategie_id}/GBPUSD'), None)

    def test_symboles_independants(self):
        banc = Banc()
        banc.cloture(ARMEMENT)
        r = banc.moteur.sur_cloture(bougie(banc.ouverture + M15, REPRISE, symbole='GBPUSD'))
        self.assertEqual(r.etat_detecteur['transition'], 'ARMEMENT')
        self.assertIs(banc.moteur.machine('EURUSD').etat, EtatTechnique.ARMED_LONG)


if __name__ == '__main__':
    unittest.main()
