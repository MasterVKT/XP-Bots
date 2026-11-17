"""Catégorie 2, couche 6 : D12 actualise les sorties sur une position London réelle."""
from dataclasses import replace
from decimal import Decimal
import unittest
from robot.london_execution_coordinateur.test_cat2_c6_coordinateur import ouvert
from robot.outils.coordinateur_execution import traiter
from robot.outils.execution_partagee import T, cotation
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import CauseCloture, Motif
from xpbots.execution.c4_cycle import NatureCommande


class TestHorairesCourants(unittest.TestCase):
    def q(self, t):
        return replace(cotation(), instant_fournisseur_ms=t, instant_reception_ms=t)

    def test_nouvelle_fermeture_connue_borne_exacte_sans_attendre_un_signal(self):
        b, v, _ = ouvert()
        garde = int(b.technique.commun.native_market_close_guard_seconds*1000)
        fin = T+garde+100000
        h = HorairesCotation((Intervalle(T-86400000, fin),), (), T-86400000, T+172800000)
        b.port.profils['EURUSD'] = replace(v.profil, horaires=h, releve_ms=T+2)
        avant = traiter(b, fin-garde-1, cotations=(self.q(fin-garde-1),))
        self.assertFalse(any(c.nature is NatureCommande.CLOTURE for c in avant.commandes))
        lot = traiter(b, fin-garde, cotations=(self.q(fin-garde),))
        clotures = [c for c in lot.commandes if c.nature is NatureCommande.CLOTURE]
        self.assertEqual(len(clotures), 1)
        self.assertEqual(clotures[0].donnees['cause'], CauseCloture.FERMETURE_NATIVE)

    def test_information_native_future_ne_sert_pas_de_profil_courant(self):
        b, v, _ = ouvert(); t = T+2
        b.port.profils['EURUSD'] = replace(v.profil, releve_ms=t+1)
        lot = traiter(b, t, cotations=(self.q(t),))
        fermeture = next(c for c in lot.commandes if c.nature is NatureCommande.CLOTURE)
        self.assertEqual(fermeture.donnees['cause'], CauseCloture.PROTECTION)
        self.assertEqual(fermeture.donnees['motif'], Motif.ENVIRONMENT_NOT_READY)

    def test_profil_absent_ou_etranger_ne_conserve_pas_une_fausse_echeance(self):
        for nature in ('absent', 'etranger'):
            b, v, _ = ouvert(); t = T+2
            b.port.profils['EURUSD'] = None if nature == 'absent' else replace(v.profil, symbole_courtier='AUTRE')
            lot = traiter(b, t, cotations=(self.q(t),))
            fermeture = next(c for c in lot.commandes if c.nature is NatureCommande.CLOTURE)
            self.assertEqual(fermeture.donnees['cause'], CauseCloture.PROTECTION)
            self.assertEqual(fermeture.donnees['motif'], Motif.ENVIRONMENT_NOT_READY)
