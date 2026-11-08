"""Catégorie 2 : cycle réel 0–4, moteur London et réservations partagées."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.cycle_execution import bloc_cycle, remplissage, cloture
from robot.outils.execution_partagee import profil, cotation
from robot.outils.london import parametres, bougie, miroir
from robot.moteur_london.test_cat1_c2_moteur_london import amorcer
from xpbots.london.c2_moteur import MoteurLondon
from xpbots.execution.c4_cycle import NatureCommande, NatureReponse, ReponseCourtier
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle
from xpbots.noyau.c1c_domaine import NatureIssue, CauseCloture, Motif, Sens, SignalTechnique


class TestJonctionCycle(unittest.TestCase):
    def test_l12_partiel_consomme_une_entree_cloture_libere_et_seul_nouveau_sens_admis(self):
        p=parametres(); m=MoteurLondon(p,'EURUSD',D('.00001'))
        amorcer(m,p,haut=1.10000,bas=1.09800,atr_h1=.00080)
        def barre(heure='08:00:00'):
            return bougie(heure=heure,o=1.09995,h=1.10055,l=1.09990,c=1.10050,a=.00050,tr=.00065)
        s=m.sur_bougie(barre()); self.assertIsInstance(s,SignalTechnique)
        t=s.cloture_ms
        h=HorairesCotation((Intervalle(t-86400000,t+86400000),),(),t-86400000,t+172800000)
        q=cotation(bid=D('1.10050'),ask=D('1.10060'),instant_fournisseur_ms=t,instant_reception_ms=t)
        b=bloc_cycle(signal_=s,profil_=profil(horaires=h,releve_ms=t),cotation_=q)
        b.cycle.preparer_envoi(t)
        r=remplissage(b,volume_cumule=D('.2'),volume_position=D('.2'),
            reliquat=b.plan.volume-D('.2'),reliquat_annule=False)
        e=b.cycle.sur_reponse(r)
        for i in e.issues: b.registre.sur_issue(i); m.sur_issue(i)
        self.assertEqual(len(m.etat_quotas.remplissages),1)
        self.assertTrue(m.position_ouverte)
        self.assertEqual(m.sur_bougie(barre('08:15:00')).motif,Motif.SYMBOL_BUSY)
        self.assertFalse(b.cycle.sur_reponse(replace(r,reference='duplicate',instant_ms=t+2)).issues)
        e=b.cycle.sur_reponse(cloture(b,instant_ms=t+3,cause=CauseCloture.STOP_LOSS))
        self.assertFalse(e.issues); self.assertEqual(len(b.registre.etat.reservations),1)
        e=b.cycle.sur_reponse(ReponseCourtier(NatureReponse.ANNULATION,b.plan.reservation.cle,'annule',t+4,
            dict(ordre='ordre-1',confirmee=True)))
        for i in e.issues: b.registre.sur_issue(i); m.sur_issue(i)
        self.assertFalse(m.position_ouverte); self.assertFalse(b.registre.etat.reservations)
        self.assertEqual(m.sur_bougie(barre('08:30:00')).detail,'SENS_DEJA_REMPLI')
        vente=miroir(barre('08:45:00'),centre=1.099)
        self.assertEqual(m.sur_bougie(vente).sens,Sens.VENTE)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in e.commandes))

    def test_remplissage_apres_timeout_utilise_le_meme_risque_jusqu_a_cloture_confirmee(self):
        b=bloc_cycle(); t=b.signal.cloture_ms
        b.cycle.preparer_envoi(t); b.cycle.sur_minuterie(t+5000)
        initial=b.registre.etat.reservations[0].risque_initial
        e=b.cycle.sur_reponse(remplissage(b,instant_ms=t+6000,execution_ms=t+1))
        for i in e.issues: b.registre.sur_issue(i)
        self.assertTrue(b.registre.etat.reservations[0].remplie)
        self.assertEqual(b.registre.etat.reservations[0].risque_initial,initial)
        b.cycle.demander_cloture(t+6001,CauseCloture.DUREE_MAXIMALE)
        self.assertEqual(len(b.registre.etat.reservations),1)
        e=b.cycle.sur_reponse(cloture(b,instant_ms=t+7000))
        for i in e.issues: b.registre.sur_issue(i)
        self.assertEqual([i.nature for i in e.issues],[NatureIssue.CLOTUREE])
        self.assertFalse(b.registre.etat.reservations)
