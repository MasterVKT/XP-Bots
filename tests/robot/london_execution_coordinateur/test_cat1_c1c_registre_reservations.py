"""Catégorie 1, couche 1c (registre_reservations) : contrat et bornes des sources C04–C09."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.execution_partagee import *
from xpbots.execution.c0a_types import *
from xpbots.execution.c1c_reservations import RegistreReservations
from xpbots.noyau.c1c_domaine import Issue,NatureIssue,Motif,CauseCloture

def compte(**kw): return EtatCompte(T,D(100),D(100),D(0),**kw)
def reservation(s=None,risque=D('.5'),sous=None):
    k=cle(s);return Reservation(k,sous or k.symbole,risque,D(1),D('.1'))

class TestReservations(unittest.TestCase):
    def test_plafond_risque_total_inclus_et_refus_sans_mutation(self):
        r=RegistreReservations(commun());a=reservation();r.reserver(a,compte(),0)
        b=reservation(signal(symbole='GBPUSD'));r.reserver(b,compte(),1)
        self.assertEqual(r.risque_total(compte()),D(1))
        r=RegistreReservations(commun());r.reserver(a,compte(),0);avant=r.etat
        b=replace(b,risque_initial=D('.50001'));v=r.reserver(b,compte(),1)
        self.assertEqual((v.motif,v.detail),(Motif.ACCOUNT_RISK_CAP,'RESERVE_TOTALE'));self.assertEqual(r.etat,avant)
    def test_version_comparee_et_idempotence(self):
        r=RegistreReservations(commun());a=reservation();e=r.reserver(a,compte(),0)
        self.assertEqual(r.reserver(a,compte(),0),e)
        v=r.reserver(reservation(signal(symbole='GBPUSD')),compte(),0)
        self.assertEqual(v.detail,'version_reservations');self.assertEqual(r.etat,e)
        with self.assertRaises(ValueError):r.reserver(replace(a,risque_initial=D('.4')),compte(),1)
    def test_symbole_alias_sous_jacent_et_verrou(self):
        r=RegistreReservations(commun());r.reserver(reservation(),compte(),0)
        for b in (reservation(signal(strategie='EMA_V3')),reservation(signal(symbole='GBPUSD'),sous='EURUSD')):
            self.assertIs(r.reserver(b,compte(),r.etat.version).motif,Motif.SYMBOL_BUSY)
        r=RegistreReservations(commun());r.verrouiller('EURUSD')
        self.assertEqual(r.reserver(reservation(),compte(),r.etat.version).detail,'ETAT_ORDRE_INCONNU')
    def test_positions_externes_et_nombre_compte(self):
        p=PositionCompte('externe','EURUSD','EURUSD',D('.1'),None)
        r=RegistreReservations(commun());self.assertEqual(r.reserver(reservation(),compte(positions=(p,)),0).detail,'POSITIONS_EXTERNES')
        ps=tuple(PositionCompte(str(i),s,s,D('.1'),D('.1'),cle(signal(symbole=s))) for i,s in enumerate(('GBPUSD','XAUUSD')))
        self.assertEqual(r.reserver(reservation(),compte(positions=ps),0).detail,'NOMBRE_POSITIONS')
    def test_position_et_reserve_comptees_une_fois_au_plus_prudent(self):
        r=RegistreReservations(commun());a=reservation();r.reserver(a,compte(),0)
        p=PositionCompte('p','EURUSD','EURUSD',D('.1'),D('.4'),a.cle)
        c=compte(positions=(p,));self.assertEqual(r.risque_total(c),D('.5'));self.assertEqual(r.marge_en_attente(c),D(0))
        self.assertEqual(r.risque_total(compte(positions=(replace(p,risque_initial=D('.6')),))),D('.6'))
    def test_fill_et_profit_ne_liberent_pas_avant_cloture(self):
        r=RegistreReservations(commun());a=reservation();r.reserver(a,compte(),0)
        r.sur_issue(Issue(a.cle,NatureIssue.REMPLIE,T));e=r.etat
        self.assertEqual(r.sur_issue(Issue(a.cle,NatureIssue.REMPLIE,T)),e)
        self.assertEqual(r.risque_total(replace(compte(),fonds_propres=D(200))),D('.5'))
        with self.assertRaises(ValueError):r.sur_issue(Issue(a.cle,NatureIssue.REFUSEE,T,Motif.SPREAD_CAP))
        r.sur_issue(Issue(a.cle,NatureIssue.CLOTUREE,T,cause=CauseCloture.STOP_LOSS))
        self.assertFalse(r.etat.reservations);self.assertEqual(r.reserver(a,compte(),r.etat.version).detail,'cle_terminee')
    def test_refus_avant_fill_termine_la_reserve(self):
        r=RegistreReservations(commun());a=reservation();r.reserver(a,compte(),0)
        r.sur_issue(Issue(a.cle,NatureIssue.REFUSEE,T,Motif.SPREAD_CAP))
        self.assertFalse(r.etat.reservations)
    def test_replacement_ne_supprime_pas_reserve_d_un_autre_robot(self):
        r=RegistreReservations(commun());a=reservation();b=reservation(signal(symbole='GBPUSD'),risque=D('.4'))
        r.reserver(a,compte(),0);r.reserver(b,compte(),1);r.sur_issue(Issue(a.cle,NatureIssue.REMPLIE,T))
        self.assertIsNone(r.verifier_admission(a.cle,'EURUSD',D('.6'),compte(),remplacement=True))
        self.assertEqual(r.verifier_admission(a.cle,'EURUSD',D('.60001'),compte(),remplacement=True).detail,'RESERVE_TOTALE')
