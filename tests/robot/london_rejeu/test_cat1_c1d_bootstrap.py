"""Panel indépendant à huit journées, tirages témoins et percentiles manuels."""
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import C
from xpbots.rejeu.c0a_types import ErreurRejeu,JourMarche,ValeurJour
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1d_bootstrap import indices_bootstrap,percentile,bootstrap_apparie


def panel():
    return tuple(JourMarche(date(2026,11,j),'validation') for j in (2,3,4,5,6,9,10,11))


def parametres():return replace(charger_protocole(C).bootstrap,replications=3)


class TestBootstrap(unittest.TestCase):
    def test_tirages_par_blocs_temoin_remise_et_troncature(self):
        # Les choix de débuts, tirés indépendamment dans [0,3], sont (1,2), (2,3), (0,1).
        attendu=((1,2,3,4,5,2,3,4),(2,3,4,5,6,3,4,5),(0,1,2,3,4,1,2,3))
        self.assertEqual(tuple(indices_bootstrap(panel(),parametres())),attendu)
        self.assertEqual(tuple(indices_bootstrap(panel(),parametres())),attendu)
        autre=tuple(indices_bootstrap(panel(),replace(parametres(),graine=3)))
        self.assertNotEqual(autre,attendu)

    def test_percentiles_interpolation_lineaire_sans_modifier_entree(self):
        v=[D(5),D(1),D(3)]
        self.assertEqual(percentile(v,D('2.5')),D('1.1'))
        self.assertEqual(percentile(v,D('97.5')),D('4.9'))
        self.assertEqual(v,[D(5),D(1),D(3)])
        self.assertEqual(percentile((D(4),),D(50)),D(4));self.assertIsNone(percentile((),D(50)))
        for p in (D(-1),D(101),D('NaN'),50):
            with self.subTest(p=p),self.assertRaises(ErreurRejeu):percentile(v,p)

    def test_esperance_diff_et_gain_apparies_calcules_a_la_main(self):
        j=panel();a=tuple(ValeurJour(v.jour,v.periode,D(1),1) for v in j)
        b=tuple(ValeurJour(v.jour,v.periode,D(i+1),1) for i,v in enumerate(j))
        r=bootstrap_apparie(a,b,parametres(),D(100))
        self.assertEqual(r.esperance_candidat.valeurs,(D(4),D(5),D(3)))
        self.assertEqual((r.esperance_candidat.bas,r.esperance_candidat.haut),(D('3.05'),D('4.95')))
        self.assertEqual(r.difference_esperance.valeurs,(D(3),D(4),D(2)))
        self.assertEqual((r.difference_esperance.bas,r.difference_esperance.haut),(D('2.05'),D('3.95')))
        self.assertEqual(r.gain_incremental.valeurs,(D(24),D(32),D(16)))
        self.assertEqual(r.difference_drawdown.valeurs,(D(0),D(0),D(0)))
        self.assertEqual(r.empreinte_indices,bootstrap_apparie(a,b,parametres(),D(100)).empreinte_indices)

    def test_repliques_sans_trade_invalidees_pas_espérance_zero(self):
        j=panel();a=tuple(ValeurJour(v.jour,v.periode,D(0),0) for v in j)
        b=tuple(replace(v,pnl_net=D('-.02')) for v in a)
        r=bootstrap_apparie(a,b,parametres(),D(100))
        self.assertEqual((r.esperance_candidat.invalides,r.difference_esperance.invalides),(3,3))
        self.assertIsNone(r.esperance_candidat.bas);self.assertIsNone(r.difference_esperance.bas)
        self.assertEqual(r.gain_incremental.valeurs,(D('-.16'),)*3)
        self.assertEqual(r.difference_drawdown.valeurs,(D('.0016'),)*3)

    def test_periode_frontiere_jamais_franchie_dans_un_bloc(self):
        jours=tuple(JourMarche(date(2026,11,i+1),'a' if i<6 else 'b') for i in range(12))
        blocs={tuple(range(i,i+5)) for i in (0,1,6,7)}
        for tirage in indices_bootstrap(jours,parametres()):
            self.assertIn(tirage[:5],blocs);self.assertIn(tirage[5:10],blocs)
        trop_court=tuple(replace(j,periode='a' if i<4 else 'b') for i,j in enumerate(panel()))
        with self.assertRaises(ErreurRejeu):tuple(indices_bootstrap(trop_court,parametres()))

    def test_jours_decales_non_ordonnes_et_reprise_periode_refuses(self):
        j=panel();a=tuple(ValeurJour(v.jour,v.periode,D(1),1) for v in j)
        b=a[:-1]+(replace(a[-1],jour=date(2026,11,12)),)
        with self.assertRaises(ErreurRejeu):bootstrap_apparie(a,b,parametres(),D(100))
        with self.assertRaises(ErreurRejeu):tuple(indices_bootstrap(reversed(j),parametres()))
        j=tuple(replace(v,periode=('b' if i==3 else 'a')) for i,v in enumerate(j))
        with self.assertRaises(ErreurRejeu):tuple(indices_bootstrap(j,parametres()))

    def test_une_seule_esperance_invalide_ne_supprime_pas_le_gain_net(self):
        j=panel();a=tuple(ValeurJour(v.jour,v.periode,D(0),0) for v in j)
        b=tuple(replace(v,pnl_net=D(1),trades_clos=1) for v in a)
        r=bootstrap_apparie(a,b,parametres(),D(100))
        self.assertEqual((r.esperance_candidat.invalides,r.difference_esperance.invalides),(0,3))
        self.assertEqual(r.gain_incremental.valeurs,(D(8),)*3)
