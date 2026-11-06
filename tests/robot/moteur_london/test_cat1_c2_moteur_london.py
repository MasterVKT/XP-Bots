"""Catégorie 1, couche 2 (moteur_london) : S02.6, L-01 à L-13 et ordre déterministe des refus."""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import math
import unittest

from robot.outils.london import JOUR, TICK, bougie, bougies_range, issue, miroir, parametres
from xpbots.donnees.c0a_types import UniteTemps
from xpbots.london.c0b_types import ErreurLondon
from xpbots.london.c2_moteur import MoteurLondon, StrategieLondon, fabriquer_strategie
from xpbots.noyau.c1c_domaine import CauseCloture, Motif, NatureIssue, Sens, SignalTechnique


def amorcer(moteur, p, *, jour=JOUR, haut=100, bas=98, atr_h1=1, rang_h1=None, retard_h1=0,
            supprimer=None, invalider=None, symbole='EURUSD', sans_h1=False):
    suite = bougies_range(p, jour, symbole)
    suite = [replace(e, bougie=replace(e.bougie, ouverture=(haut+bas)/2, haut=haut, bas=bas, cloture=(haut+bas)/2))
             for e in suite]
    if invalider is not None:
        e = suite[invalider]
        suite[invalider] = replace(e, bougie=replace(e.bougie, valide=False, motif_invalidite='AUCUN_BID'),
                                   indicateurs=None)
    if supprimer is not None:
        suite.pop(supprimer)
    if not sans_h1:
        suite.append(bougie(p=p, jour=jour, symbole=symbole, heure='06:00:00', unite=UniteTemps.H1,
                             atr=atr_h1, rang=rang_h1, retard_ms=retard_h1))
    for e in sorted(suite, key=lambda e: (e.bougie.fin_ms, e.unite is UniteTemps.M15)):
        moteur.sur_bougie(e)
    return moteur


class TestMoteurLondon(unittest.TestCase):
    def setUp(self):
        self.p = parametres()

    def pret(self, **kwargs):
        jour = kwargs.get('jour', JOUR)
        return amorcer(MoteurLondon(self.p, 'EURUSD', TICK), self.p, **kwargs)

    def test_signal_complet_et_mesures_exactes_du_contexte(self):
        m = self.pret()
        b = bougie(p=self.p)
        resultat = m.sur_bougie(b)
        self.assertIsInstance(resultat, SignalTechnique)
        self.assertEqual(resultat.sens, Sens.ACHAT)
        self.assertEqual(resultat.cloture_ms, b.bougie.fin_ms)
        self.assertEqual(resultat.multiple_objectif, self.p.take_profit_gross_price_r)
        c = resultat.contexte
        self.assertEqual((c['range_haut'], c['range_bas'], c['largeur_range'], c['atr_h1'],
                          c['rapport_range_atr_h1'], c['tr_signal'], c['atr_reference']), (100, 98, 2, 1, 2, 1.25, 1))
        self.assertEqual(c['composantes_stop'][0], b.bougie.bas-max(float(TICK), self.p.commun.structural_buffer_atr))
        self.assertEqual(c['gel_disponible_ms'], m.gel.disponible_ms)
        self.assertEqual(c['tick_size'], str(TICK))
        self.assertEqual(c['composantes_contraignantes'], ('BOUGIE',))

    def test_l01_exemple_chiffre_s02_5(self):
        m = MoteurLondon(self.p, 'EURUSD', Decimal('0.00001'))
        amorcer(m, self.p, haut=1.10000, bas=1.09800, atr_h1=0.00080)
        signal = m.sur_bougie(bougie(o=1.09995, h=1.10055, l=1.09990, c=1.10050, a=0.00050, tr=0.00065))
        self.assertEqual(signal.sens, Sens.ACHAT)
        self.assertTrue(math.isclose(signal.stop_technique, 1.09985, rel_tol=1e-12))

    def test_l02_l03_l04_fenetre_ete_hiver_et_lendemains_de_changement(self):
        for jour in (JOUR, date(2026, 7, 1), date(2026, 3, 30), date(2026, 10, 26)):
            for heure, admis in (('07:45:00', False), ('08:00:00', True), ('10:30:00', True), ('10:45:00', False)):
                m = self.pret(jour=jour)
                resultat = m.sur_bougie(bougie(p=self.p, jour=jour, heure=heure))
                with self.subTest(jour=jour, heure=heure):
                    self.assertEqual(isinstance(resultat, SignalTechnique), admis)
                    if not admis:
                        self.assertEqual((resultat.motif, resultat.detail), (Motif.OUTSIDE_SESSION, 'HORS_FENETRE'))

    def test_l05_weekend_aucun_range_ni_signal(self):
        for jour in (date(2026, 7, 4), date(2026, 7, 5)):
            m = self.pret(jour=jour)
            r = m.sur_bougie(bougie(jour=jour))
            self.assertIsNone(m.range)
            self.assertEqual((r.motif, r.detail), (Motif.OUTSIDE_SESSION, 'JOUR_INACTIF'))

    def test_l06_largeur_exactement_aux_deux_bornes_et_juste_en_dehors(self):
        for largeur, admis in ((self.p.range_min_h1_atr, True), (self.p.range_max_h1_atr, True),
                               (self.p.range_min_h1_atr-math.ulp(100), False),
                               (self.p.range_max_h1_atr+math.ulp(100), False)):
            m = self.pret(haut=100, bas=100-largeur)
            r = m.sur_bougie(bougie())
            with self.subTest(largeur=largeur):
                self.assertEqual(isinstance(r, SignalTechnique), admis)
                if not admis:
                    self.assertEqual(r.detail, 'RANGE_HORS_BORNES')

    def test_l07_gel_tardif_refuse_0815_puis_admet_0830_sans_fuite_du_contexte(self):
        m = self.pret(retard_h1=80*60000)
        r = m.sur_bougie(bougie())
        self.assertEqual((r.motif, r.detail), (Motif.NO_SETUP, 'GEL_ATR_H1_POSTERIEUR'))
        self.assertNotIn('atr_h1', r.contexte)
        self.assertIsInstance(m.sur_bougie(bougie(heure='08:15:00')), SignalTechnique)

    def test_l07_prechargement_h1_atr_nul_et_h1_absente(self):
        for kw in ({'rang_h1': self.p.commun.warmup_closed_h1_bars-2}, {'atr_h1': 0}, {'sans_h1': True}):
            m = self.pret(**kw)
            r = m.sur_bougie(bougie())
            self.assertEqual((r.motif, r.detail), (Motif.WARMUP, 'ATR_H1_INDISPONIBLE'))

    def test_p09_gel_ne_change_ni_sur_h1_suivante_ni_sur_correction(self):
        m = self.pret()
        gel = m.gel
        m.sur_bougie(bougie(heure='06:00:00', unite=UniteTemps.H1, atr=99))
        m.sur_bougie(bougie(heure='07:00:00', unite=UniteTemps.H1, atr=99))
        self.assertEqual(m.gel, gel)
        self.assertEqual(m.sur_bougie(bougie()).contexte['atr_h1'], gel.atr)

    def test_premiere_h1_valide_peut_achever_un_gel_encore_indisponible(self):
        m = self.pret(sans_h1=True)
        m.sur_bougie(bougie(heure='06:00:00', unite=UniteTemps.H1, valide=False, motif='AUCUN_BID'))
        self.assertIsNone(m.gel)
        h1 = bougie(heure='06:00:00', unite=UniteTemps.H1, atr=1, retard_ms=60*60000)
        m.sur_bougie(h1)
        self.assertEqual(m.gel.disponible_ms, h1.bougie.instant_disponibilite_ms)
        self.assertIsInstance(m.sur_bougie(bougie()), SignalTechnique)

    def test_l08_range_manquant_ou_invalide_reste_refuse_pour_le_jour(self):
        for kw, detail in (({'supprimer': 0}, 'RANGE_INCOMPLET'), ({'invalider': 5}, 'RANGE_BOUGIE_INVALIDE')):
            m = self.pret(**kw)
            self.assertEqual(m.sur_bougie(bougie()).detail, detail)
            self.assertIsNone(m.sur_bougie(bougies_range(self.p)[5]), 'aucune réécriture d’une ancienne M15')
            self.assertEqual(m.sur_bougie(bougie(heure='08:15:00')).detail, detail)

    def test_l09_07h_ne_modifie_pas_le_range_et_prix_deja_hors_range_admis(self):
        m = self.pret()
        r = m.range
        m.sur_bougie(bougie(heure='07:00:00', h=200, l=1))
        m.sur_bougie(bougie(heure='07:45:00'))
        self.assertEqual(m.range, r)
        self.assertIsInstance(m.sur_bougie(bougie()), SignalTechnique)

    def test_l10_motifs_de_bougie_et_l11_stop_trop_large(self):
        for kw, detail in (({'o': 100.875}, 'CORPS_INSUFFISANT'), ({'tr': 3}, 'TR_EXCESSIF'),
                           ({'o': 100, 'h': 100, 'l': 100, 'c': 100}, 'BOUGIE_PLATE')):
            self.assertEqual(self.pret().sur_bougie(bougie(**kw)).detail, detail)
        r = self.pret().sur_bougie(bougie(o=99, h=101, l=98, c=100.875, tr=2))
        self.assertEqual((r.motif, r.detail), (Motif.STOP_TOO_WIDE, None))

    def test_p10_m15_999_contre_1000_a_absent_et_non_positif(self):
        seuil = self.p.commun.warmup_closed_m15_bars-1
        for kw, detail in (({'rang': seuil-1}, 'M15_INSUFFISANTES'), ({'a': None}, 'ATR_M15_INDISPONIBLE'),
                           ({'a': 0}, 'ATR_NON_POSITIF')):
            self.assertEqual(self.pret().sur_bougie(bougie(**kw)).detail, detail)
        self.assertIsInstance(self.pret().sur_bougie(bougie(rang=seuil)), SignalTechnique)

    def test_l12_refus_veto_ou_expiration_sans_quota_nouveau_signal_uniquement(self):
        for nature, motif, detail in ((NatureIssue.REFUSEE, Motif.AI_CONTEXT_VETO, 'preuve_fictive'),
                                      (NatureIssue.EXPIREE, Motif.SIGNAL_EXPIRED, 'AUCUNE_COTATION')):
            m = self.pret()
            b = bougie()
            self.assertIsInstance(m.sur_bougie(b), SignalTechnique)
            self.assertIsNone(m.sur_issue(issue(nature=nature, motif=motif, detail=detail)))
            self.assertEqual(m.etat_quotas.remplissages, ())
            self.assertIsNone(m.sur_bougie(b))
            self.assertIsInstance(m.sur_bougie(bougie(heure='08:15:00')), SignalTechnique)

    def test_l12_fill_partiel_cloture_nouveau_sens_et_troisieme_entree(self):
        m = self.pret()
        m.sur_bougie(bougie())
        rempli = issue()
        m.sur_issue(rempli)
        m.sur_issue(rempli)
        self.assertTrue(m.position_ouverte)
        self.assertEqual(len(m.etat_quotas.remplissages), 1)
        self.assertIsNone(m.sur_issue(replace(rempli, nature=NatureIssue.CLOTUREE, cause=CauseCloture.STOP_LOSS)))
        m.sur_issue(rempli)  # répétition tardive après clôture, pas de réouverture
        self.assertFalse(m.position_ouverte)
        self.assertIsNone(m.sur_bougie(bougie()), 'aucune inversion sur l’ancienne clôture')
        self.assertEqual(m.sur_bougie(bougie(heure='08:15:00')).detail, 'SENS_DEJA_REMPLI')
        vente = miroir(bougie(heure='08:30:00'), centre=99)
        self.assertEqual(m.sur_bougie(vente).sens, Sens.VENTE)
        rempli_vente = issue(heure='08:45:00', sens=Sens.VENTE)
        m.sur_issue(rempli_vente)
        m.sur_issue(replace(rempli_vente, nature=NatureIssue.CLOTUREE, cause=CauseCloture.TAKE_PROFIT))
        self.assertEqual(m.sur_bougie(bougie(heure='08:45:00')).detail, 'MAXIMUM_JOURNALIER')

    def test_l13_propriete_prioritaire_et_cloture_etrangere_sans_effet(self):
        m = self.pret()
        m.sur_issue(issue())
        r = m.sur_bougie(bougie(o=100.875))
        self.assertEqual((r.motif, r.detail), (Motif.SYMBOL_BUSY, 'POSITION_METHODE'))
        m.sur_issue(issue(heure='08:30:00', nature=NatureIssue.CLOTUREE, cause=CauseCloture.STOP_LOSS))
        self.assertTrue(m.position_ouverte)

    def test_symboles_et_bras_independants(self):
        strategie = StrategieLondon(self.p, {'EURUSD': TICK, 'GBPUSD': TICK})
        amorcer(strategie, self.p)
        amorcer(strategie, self.p, symbole='GBPUSD')
        strategie.sur_issue(issue())
        self.assertEqual(strategie.sur_bougie(bougie()).motif, Motif.SYMBOL_BUSY)
        self.assertIsInstance(strategie.sur_bougie(bougie(symbole='GBPUSD')), SignalTechnique)
        self.assertIsInstance(self.pret().sur_bougie(bougie()), SignalTechnique)

    def test_nouveau_jour_efface_range_gel_et_quotas_sans_perdre_la_propriete(self):
        m = self.pret()
        m.sur_issue(issue())
        demain = JOUR+timedelta(days=1)
        m.sur_bougie(bougie(jour=demain, heure='00:00:00'))
        self.assertEqual(m.etat_quotas.remplissages, ())
        self.assertIsNone(m.range)
        self.assertIsNone(m.gel)
        self.assertTrue(m.position_ouverte)
        m.sur_issue(issue(nature=NatureIssue.CLOTUREE, cause=CauseCloture.STOP_LOSS))
        self.assertFalse(m.position_ouverte)

    def test_p03_trou_efface_le_range_puis_recuperation_sans_nouveau_prechargement(self):
        m = self.pret()
        ancien = m.range
        r = m.sur_bougie(bougie(heure='07:45:00', valide=False, motif='TROU_DONNEES'))
        self.assertEqual((r.motif, r.detail), (Motif.DATA_GAP, 'TROU_ACTIF'))
        self.assertIsNone(m.range)
        self.assertIsInstance(m.sur_bougie(bougie()), SignalTechnique)
        self.assertEqual(m.range, ancien)

    def test_fabrique_copie_les_tailles_et_refuse_les_entrees_hors_contrat(self):
        tailles = {'EURUSD': TICK}
        strategie = StrategieLondon(self.p, tailles)
        tailles['EURUSD'] = Decimal('10')
        amorcer(strategie, self.p)
        self.assertIsInstance(strategie.sur_bougie(bougie()), SignalTechnique)
        for action in (lambda: strategie.sur_bougie(bougie(symbole='GBPUSD')),
                       lambda: strategie.sur_bougie(None), lambda: strategie.sur_issue(None),
                       lambda: MoteurLondon(self.p, 'INCONNU', TICK),
                       lambda: StrategieLondon(self.p, {'EURUSD': 0.1}),
                       lambda: fabriquer_strategie({}, {})):
            with self.assertRaises(ErreurLondon):
                action()

    def test_metadonnees_locales_incoherentes_et_issue_etrangere_refusees(self):
        m = self.pret()
        b = bougie()
        with self.assertRaises(ErreurLondon):
            m.sur_bougie(replace(b, jour_londres=JOUR+timedelta(days=1)))
        with self.assertRaises(ErreurLondon):
            m.sur_issue(issue(symbole='GBPUSD'))
