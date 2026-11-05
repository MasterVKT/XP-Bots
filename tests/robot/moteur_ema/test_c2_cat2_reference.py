"""Couche 2, catégorie 2 — bloc réel {0 → 2} : équivalence avec `reference.technical.ema_setups`.

La machine est nourrie des indicateurs calculés par la référence elle-même (mêmes flottants) ; chaque reprise est
convertie en stop par la couche 1d puis refusée (la référence n'a ni fill ni compteur : cooldown d'une clôture).
"""
import math
import unittest
from decimal import Decimal

from robot.fixtures.series import DEBUT_LUNDI, bougies_tendances
from robot.moteur_ema.outils_ema import BUNDLE, P
from robot.moteur_ema.reference_ema import REFERENCE_DISPONIBLE, cadre_reference, setups_reference
from xpbots.donnees_temps.c0_parametres_seances import charger_parametres_techniques
from xpbots.donnees_temps.c1a_sessions import SessionsLondres
from xpbots.moteur_ema.c1d_stop import stop_technique
from xpbots.moteur_ema.c2_machine_etats import MachineEtatsEMA, NatureTransition, ObservationEMA
from xpbots.noyau.decisions import MotifRefus, Refuse

SESSIONS = SessionsLondres(charger_parametres_techniques(BUNDLE))
TICK = Decimal('0.00001')
PRECHAUFFAGE = BUNDLE.donnees['common']['warmup_closed_m15_bars']
RAPIDE, MOYENNE, LENTE = P.periodes_ema


def fini(*valeurs):
    return all(isinstance(v, float) and math.isfinite(v) for v in valeurs)


def rejouer_machine(bougies, cadre):
    machine, setups, trop_larges = MachineEtatsEMA(P), [], 0
    for t, b in enumerate(bougies):
        ligne = cadre.iloc[t]
        valeurs = dict(o=float(b.o), h=float(b.h), l=float(b.l), c=float(b.c), tr=float(ligne.TR),
                       e_rapide=float(ligne[f'E{RAPIDE}']), e_moyenne=float(ligne[f'E{MOYENNE}']),
                       e_lente=float(ligne[f'E{LENTE}']),
                       e_lente_decalee=float(cadre[f'E{LENTE}'].iloc[t - P.decalage_pente]),
                       rsi=float(ligne.RSI), a_t=float(ligne.A))
        exploitable = t >= PRECHAUFFAGE - 1 and fini(*valeurs.values()) and valeurs['a_t'] > 0
        obs = ObservationEMA(b.cloture_ms, SESSIONS.jour_londres(b.cloture_ms),
                             SESSIONS.dans_fenetre(b.ouverture_ms, b.cloture_ms, P.debut_session,
                                                   P.fin_entrees_exclue),
                             exploitable, **(valeurs if exploitable else {}))
        transition = machine.etape(obs)
        if transition.nature is NatureTransition.REPRISE:
            r = transition.reprise
            stop = stop_technique(r.sens, valeurs['c'], r.extreme, valeurs['a_t'], TICK, P)
            if stop.trop_large:
                trop_larges += 1
            else:
                setups.append({'cloture_ms': b.cloture_ms, 'sens': int(r.sens), 'cloture_bid': valeurs['c'],
                               'a_t': valeurs['a_t'], 'b_sl': stop.b_sl, 'age': r.age})
            machine.appliquer_issue(Refuse(MotifRefus.ENVIRONMENT_NOT_READY, b.cloture_ms))
    return setups, trop_larges


@unittest.skipUnless(REFERENCE_DISPONIBLE, 'numpy et pandas requis par reference.technical')
class TestEquivalenceReference(unittest.TestCase):
    def test_configurations_identiques_a_la_reference(self):
        for graine in (1, 2, 3):
            bougies = bougies_tendances('EURUSD', DEBUT_LUNDI, 4000, graine)
            cadre = cadre_reference(bougies)
            attendus = setups_reference(cadre, TICK)
            obtenus, _ = rejouer_machine(bougies, cadre)  # stops trop larges : absents des deux listes
            with self.subTest(graine=graine):
                self.assertGreater(len(attendus), 20)
                self.assertEqual(obtenus, attendus)


if __name__ == '__main__':
    unittest.main()
