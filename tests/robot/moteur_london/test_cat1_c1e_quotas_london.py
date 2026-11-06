"""Catégorie 1, couche 1e (quotas_london) : premier fill partiel, refus, idempotence et jour Londres."""
from dataclasses import replace
from datetime import date, timedelta
import unittest

from robot.outils.london import JOUR, issue, parametres
from xpbots.london.c0b_types import ErreurLondon
from xpbots.london.c1e_quotas import QuotasLondon
from xpbots.noyau.c1c_domaine import CauseCloture, Motif, NatureIssue, Sens


class TestQuotasLondon(unittest.TestCase):
    def setUp(self):
        self.p = parametres()
        self.q = QuotasLondon(self.p, 'EURUSD')
        self.q.changer_jour(JOUR)

    def test_premier_fill_non_nul_partiel_compte_une_fois(self):
        rempli = issue()
        self.q.sur_issue(rempli)
        self.q.sur_issue(rempli)
        self.q.sur_issue(replace(rempli, nature=NatureIssue.CLOTUREE, cause=CauseCloture.STOP_LOSS))
        self.q.sur_issue(rempli)
        self.assertEqual((self.q.total, self.q.par_sens(Sens.ACHAT), self.q.par_sens(Sens.VENTE)), (1, 1, 0))
        self.assertEqual(self.q.refus(Sens.ACHAT).detail, 'SENS_DEJA_REMPLI')
        self.assertIsNone(self.q.refus(Sens.VENTE))

    def test_refus_et_expiration_ne_consoment_rien(self):
        for nature, motif, detail in ((NatureIssue.REFUSEE, Motif.SPREAD_CAP, None),
                                      (NatureIssue.EXPIREE, Motif.SIGNAL_EXPIRED, 'AUCUNE_COTATION')):
            self.q.sur_issue(issue(nature=nature, motif=motif, detail=detail))
        self.assertEqual(self.q.total, 0)
        self.assertIsNone(self.q.refus(Sens.ACHAT))

    def test_deux_sens_remplis_bloquent_la_troisieme_entree(self):
        self.q.sur_issue(issue())
        self.q.sur_issue(issue(heure='08:30:00', sens=Sens.VENTE))
        self.assertEqual(self.q.total, self.p.max_filled_entries_per_symbol_local_day)
        for sens in Sens:
            self.assertEqual(self.q.refus(sens).detail, 'MAXIMUM_JOURNALIER')

    def test_meme_jour_conserve_et_nouveau_jour_reinitialise_seul(self):
        self.q.sur_issue(issue())
        self.q.changer_jour(JOUR)
        self.assertEqual(self.q.total, 1)
        self.q.changer_jour(JOUR+timedelta(days=1))
        self.assertEqual(self.q.total, 0)
        self.q.sur_issue(issue())  # réception répétée d'une issue de la veille
        self.assertEqual(self.q.total, 0)
        with self.assertRaises(ErreurLondon):
            self.q.changer_jour(JOUR)

    def test_etat_exporte_et_restaure_garde_l_idempotence(self):
        self.q.sur_issue(issue())
        reprise = QuotasLondon(self.p, 'EURUSD', self.q.etat)
        reprise.sur_issue(issue())
        self.assertEqual(reprise.etat, self.q.etat)
        with self.assertRaises(ErreurLondon):
            QuotasLondon(self.p, 'GBPUSD', self.q.etat)

    def test_quota_modifie_change_le_refus(self):
        p = parametres(lambda j: j['london'].update(max_filled_entries_per_symbol_local_day=3,
                                                   max_filled_entries_per_direction_local_day=2))
        q = QuotasLondon(p, 'EURUSD')
        q.sur_issue(issue(p=p))
        self.assertIsNone(q.refus(Sens.ACHAT))
        q.sur_issue(issue(p=p, heure='08:30:00'))
        self.assertEqual(q.refus(Sens.ACHAT).detail, 'SENS_DEJA_REMPLI')

    def test_mauvais_types_et_issue_etrangere_refuses(self):
        for action in (lambda: self.q.refus('ACHAT'), lambda: self.q.sur_issue(None),
                       lambda: self.q.sur_issue(issue(symbole='GBPUSD')), lambda: QuotasLondon(self.p, '')):
            with self.assertRaises(ErreurLondon):
                action()
