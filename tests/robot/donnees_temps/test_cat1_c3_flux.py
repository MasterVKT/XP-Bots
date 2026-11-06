"""Catégorie 1, couche 3 (flux_bougies) : ordre H1/M15, enrichissement, trous, préfixe, reprise et refus."""
import copy
from datetime import date, datetime, timezone
import json
import unittest
from zoneinfo import ZoneInfo

from robot.outils.configuration import configuration_figee
from xpbots.donnees.c0a_types import (AnomalieDonnees, BougieEnrichie, ChangementTrou, ErreurDonneesTemps,
                                      NatureTrou, UniteTemps)
from xpbots.donnees.c1c_couverture import JournalConnexions, RegistreCouverture
from xpbots.donnees.c3_flux import SCHEMA_FLUX, FluxBougies
from xpbots.noyau.c0a_temps import instant_depuis_iso
from xpbots.noyau.c1a_marche import Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle

TECHNIQUE = configuration_figee().technique
M, H = 900_000, 3_600_000
T0 = instant_depuis_iso('2026-07-13T00:00:00Z')
FIN = T0 + 30 * 24 * H
OUVERT = HorairesCotation((Intervalle(T0, FIN),), (), T0, FIN)
LONDRES = ZoneInfo('Europe/London')


def tick(instant, bid=1.1, numero=0, symbole='EURUSD'):
    return Tick(symbole, symbole, instant, instant, numero, bid, bid + 0.0001)


def flux(couverture=None, horaires=OUVERT):
    return FluxBougies('EURUSD', TECHNIQUE, horaires, couverture or RegistreCouverture([Intervalle(T0, FIN)]))


def serie(n, pas=5 * 60_000, depuis=T0):
    """Ticks réguliers à prix déterministes, sans hasard."""
    return [tick(depuis + i * pas, 1.1 + 0.0001 * ((i * 7) % 11), i) for i in range(n)]


def tout(f, ticks):
    return [e for t in ticks for e in f.sur_tick(t)]


def bougies(evenements, unite=None):
    return [e for e in evenements if isinstance(e, BougieEnrichie) and (unite is None or e.unite is unite)]


class TestFlux(unittest.TestCase):
    def test_ordre_h1_avant_m15_a_fin_egale_et_h1_jamais_partielle(self):
        f = flux()
        avant = tout(f, serie(12))  # ticks jusqu'à T0 + 55 min
        self.assertEqual(bougies(avant, UniteTemps.H1), [], 'aucune H1 avant sa clôture')
        sortie = f.sur_tick(tick(T0 + H, 1.2, 99))
        self.assertEqual([(e.unite, e.bougie.fin_ms) for e in sortie], [(UniteTemps.H1, T0 + H), (UniteTemps.M15, T0 + H)])
        m15 = bougies(avant + list(sortie), UniteTemps.M15)
        h1 = sortie[0].bougie
        self.assertEqual((h1.ouverture, h1.haut, h1.bas, h1.cloture, h1.nombre_evenements),
                         (m15[0].bougie.ouverture, max(b.bougie.haut for b in m15), min(b.bougie.bas for b in m15),
                          m15[-1].bougie.cloture, sum(b.bougie.nombre_evenements for b in m15)))

    def test_enrichissement_londres_et_utc(self):
        f = flux()
        debut = instant_depuis_iso('2026-07-13T23:00:00Z')
        evenements = tout(f, [tick(debut, numero=0), tick(debut + M, numero=1)])
        b = bougies(evenements, UniteTemps.M15)[-1]
        self.assertEqual((b.jour_londres, b.jour_utc), (date(2026, 7, 14), date(2026, 7, 13)))
        self.assertEqual(b.ouverture_locale, datetime(2026, 7, 14, 0, 0, tzinfo=LONDRES))
        self.assertEqual(b.cloture_locale, datetime(2026, 7, 14, 0, 15, tzinfo=LONDRES))
        self.assertEqual(b.ouverture_locale.astimezone(timezone.utc), datetime(2026, 7, 13, 23, tzinfo=timezone.utc))
        self.assertEqual(b.indicateurs.rang, 0)
        self.assertIs(f.calendrier.jour_actif(b.jour_londres), True)

    def test_tick_anterieur_ignore_dans_les_deux_unites(self):
        f = flux()
        f.sur_tick(tick(T0, 1.10, 0))
        f.sur_tick(tick(T0 + 20 * 60_000, 1.10, 1))
        self.assertEqual(f.sur_tick(tick(T0 + 10 * 60_000, 9.0, 2)),
                         (AnomalieDonnees('EURUSD', 'TICK_ANTERIEUR', T0 + 10 * 60_000),))
        h1 = bougies(list(f.sur_tick(tick(T0 + H, 1.10, 3))), UniteTemps.H1)[0]
        self.assertEqual((h1.bougie.haut, h1.bougie.nombre_evenements), (1.10, 2), 'tick antérieur absent de la H1')

    def test_bougie_vide_couverte_p02_et_trou_p03(self):
        couverture = RegistreCouverture.depuis_registre_de_trous(T0, FIN, [Intervalle(T0 + 3 * M + 1, T0 + 3 * M + 2)])
        f = flux(couverture)
        evenements = tout(f, [tick(T0 + i * M, 1.1 + 0.01 * i, i) for i in (0, 1, 3, 4, 5)])
        m15 = [e for e in evenements if not isinstance(e, BougieEnrichie) or e.unite is UniteTemps.M15]
        resume = [(e.nature, e.intervalle_ms) if isinstance(e, ChangementTrou) else (e.bougie.debut_ms, e.bougie.motif_invalidite)
                  for e in m15]
        self.assertEqual(resume, [(T0, None), (T0 + M, None), (T0 + 2 * M, 'AUCUN_BID'), (NatureTrou.DEBUT, T0 + 3 * M),
                                  (T0 + 3 * M, 'TROU_DONNEES'), (NatureTrou.FIN, T0 + 4 * M), (T0 + 4 * M, None)])
        valides = [e for e in m15 if isinstance(e, BougieEnrichie) and e.bougie.valide]
        self.assertTrue(all(e.indicateurs is None for e in m15 if isinstance(e, BougieEnrichie) and not e.bougie.valide))
        self.assertEqual([e.indicateurs.rang for e in valides], [0, 1, 2])
        self.assertAlmostEqual(valides[-1].indicateurs.tr, 1.14 - 1.11, places=12, msg='TR sur la dernière clôture valide')
        self.assertFalse(f.en_trou)

    def test_changements_h1_non_emis_et_etat_de_trou_m15(self):
        couverture = RegistreCouverture.depuis_registre_de_trous(T0, FIN, [Intervalle(T0 + 5 * M, T0 + 6 * M)])
        f = flux(couverture)
        evenements = tout(f, [tick(T0, numero=0), tick(T0 + 5 * M + 10, numero=1), tick(T0 + 6 * M + 1, numero=2)])
        self.assertEqual([e.nature for e in evenements if isinstance(e, ChangementTrou)], [NatureTrou.DEBUT])
        self.assertTrue(f.en_trou)
        sortie = f.sur_tick(tick(T0 + 2 * H, numero=3))
        self.assertEqual([e.nature for e in sortie if isinstance(e, ChangementTrou)], [NatureTrou.FIN],
                         'le DEBUT du validateur H1 n\'est pas émis')
        self.assertIsInstance(sortie[0], ChangementTrou)
        self.assertEqual(bougies(list(sortie), UniteTemps.H1)[0].bougie.motif_invalidite, 'TROU_DONNEES')
        self.assertFalse(f.en_trou)

    def test_connexions_en_direct(self):
        journal = JournalConnexions()
        f = flux(journal)
        f.sur_connexion(True, T0)
        f.sur_tick(tick(T0, numero=0))
        f.sur_connexion(False, T0 + M + 5)
        f.sur_connexion(True, T0 + 2 * M + 5)
        evenements = tout(f, [tick(T0 + 2 * M + 6, numero=1), tick(T0 + 3 * M, numero=2), tick(T0 + 4 * M, numero=3)])
        m15 = bougies(evenements, UniteTemps.M15)
        self.assertEqual([b.bougie.motif_invalidite for b in m15], [None, 'TROU_DONNEES', 'TROU_DONNEES', None])
        with self.assertRaises(ErreurDonneesTemps):
            f.sur_connexion(True, T0 + 5 * M)
        with self.assertRaises(ErreurDonneesTemps):
            flux().sur_connexion(True, T0)

    def test_horaires_actualises(self):
        courts = HorairesCotation((Intervalle(T0, T0 + H),), (), T0, T0 + H)
        f = flux(horaires=courts)
        evenements = tout(f, [tick(T0, numero=0), tick(T0 + H, numero=1), tick(T0 + H + M, numero=2)])
        self.assertEqual(bougies(evenements, UniteTemps.M15)[-1].bougie.motif_invalidite, 'HORAIRES_INCONNUS')
        f.actualiser_horaires(OUVERT)
        b = bougies(list(f.sur_tick(tick(T0 + H + 2 * M, numero=3))), UniteTemps.M15)[-1]
        self.assertTrue(b.bougie.valide)
        with self.assertRaises(ErreurDonneesTemps):
            f.actualiser_horaires('horaires')

    def test_invariance_par_prefixe_c11_1(self):
        ticks = serie(200, pas=7 * 60_000 + 13)
        complet = tout(flux(), ticks)
        for n in (0, 1, 17, 64, 133, 199):
            with self.subTest(n=n):
                prefixe = tout(flux(), ticks[:n])
                self.assertEqual(prefixe, complet[:len(prefixe)])

    def test_reprise_identique_a_un_traitement_continu(self):
        couverture = RegistreCouverture.depuis_registre_de_trous(T0, FIN, [Intervalle(T0 + 9 * H, T0 + 9 * H + 40 * 60_000)])
        ticks = [t for t in serie(260, pas=4 * 60_000 + 17) if not T0 + 5 * H < t.instant_fournisseur_ms < T0 + 6 * H + 7]
        for coupure in (0, 1, 15, 74, 130, 141, 200):
            continu, coupe = flux(couverture), flux(couverture)
            for t in ticks[:coupure]:
                continu.sur_tick(t)
                coupe.sur_tick(t)
            export = json.loads(json.dumps(coupe.exporter_etat(), allow_nan=False))
            self.assertEqual(export['schema'], SCHEMA_FLUX)
            reprise = FluxBougies.reprendre(export, TECHNIQUE, OUVERT, couverture)
            with self.subTest(coupure=coupure):
                self.assertEqual(tout(reprise, ticks[coupure:]), tout(continu, ticks[coupure:]))
                self.assertEqual((reprise.en_trou, reprise.identite(UniteTemps.M15), reprise.identite('H1')),
                                 (continu.en_trou, continu.identite(UniteTemps.M15), continu.identite(UniteTemps.H1)))

    def test_reprise_refusee(self):
        f = flux()
        tout(f, serie(40))
        export = f.exporter_etat()
        couverture = RegistreCouverture([Intervalle(T0, FIN)])

        def refuse(donnees, technique=TECHNIQUE):
            with self.assertRaises(ErreurDonneesTemps):
                FluxBougies.reprendre(donnees, technique, OUVERT, couverture)

        for cle, valeur in (('schema', 'autre'), ('symbole', 'GBPUSD'), ('symbole', ''), ('empreinte_configuration', 'f' * 64),
                            ('unites', {'M15': export['unites']['M15']})):
            altere = copy.deepcopy(export)
            altere[cle] = valeur
            with self.subTest(cle=cle, valeur=valeur):
                refuse(altere)
        permute = copy.deepcopy(export)
        permute['unites']['M15']['constructeur'], permute['unites']['H1']['constructeur'] = \
            permute['unites']['H1']['constructeur'], permute['unites']['M15']['constructeur']
        en_retard = copy.deepcopy(export)
        en_retard['unites']['H1']['constructeur']['derniere_fin_ms'] = T0 + 5 * H
        en_retard['unites']['H1']['constructeur']['ouverte'] = None
        sans_trou = copy.deepcopy(export)
        sans_trou['unites']['M15']['en_trou'] = 'non'
        incomplet = copy.deepcopy(export)
        del incomplet['unites']['H1']['chaine']
        for nom, donnees in (('permute', permute), ('en_retard', en_retard), ('en_trou', sans_trou),
                             ('incomplet', incomplet), ('texte', 'etat')):
            with self.subTest(nom=nom):
                refuse(donnees)
        with self.assertRaises(ErreurDonneesTemps):
            FluxBougies.reprendre(export, TECHNIQUE, 'horaires', couverture)

    def test_refus(self):
        couverture = RegistreCouverture([Intervalle(T0, FIN)])
        for arguments in (('', TECHNIQUE, OUVERT, couverture), ('EURUSD', TECHNIQUE.commun, OUVERT, couverture),
                          ('EURUSD', TECHNIQUE, None, couverture), ('EURUSD', TECHNIQUE, OUVERT, object())):
            with self.subTest(arguments=arguments[:2]), self.assertRaises(ErreurDonneesTemps):
                FluxBougies(*arguments)
        f = flux()
        for valeur in (tick(T0, symbole='GBPUSD'), 'tick'):
            with self.subTest(valeur=valeur), self.assertRaises(ErreurDonneesTemps):
                f.sur_tick(valeur)
        with self.assertRaises(ErreurDonneesTemps):
            f.identite('D1')
        with self.assertRaises(ErreurDonneesTemps):
            f.sur_connexion('oui', T0)


if __name__ == '__main__':
    unittest.main()
