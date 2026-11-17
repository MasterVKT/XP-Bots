"""Actualisation causale d'un livre C10 existant, sans réinitialisation."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.rejeu import cas_simulateur,cotation_test
from xpbots.execution.c0a_types import OrdreCalcule
from xpbots.noyau.c1b_instrument import HorairesCotation,Intervalle
from xpbots.rejeu.c0a_types import ErreurRejeu,TarifCommission


class TestProfilCourant(unittest.TestCase):
    def test_fermeture_courante_et_tarif_sans_mouvement(self):
        b,e,c=cas_simulateur();t=e.instant_ms
        h=replace(b.profil.horaires,fermetures=(Intervalle(t,t+60000),))
        p=replace(b.profil,horaires=h,releve_ms=t)
        avant=(e.etat_compte(),e.courbe,e.reponses,e.positions_ouvertes)
        tarif=TarifCommission('PREUVE_FRAIS',entree_par_lot=D(2),minimum_entree=D(0),
                              sortie_par_lot=D(2),minimum_sortie=D(0))
        e.actualiser_profil(p,tarif,t)
        self.assertEqual(e.specifications(p.symbole),p)
        n=b.plan.niveaux
        ordre=OrdreCalcule(c.cle,p.symbole_courtier,b.plan.volume,n.entree,n.stop,n.objectif)
        self.assertFalse(e.controler(ordre,e.etat_compte()).admis)
        self.assertEqual(e.frais_aller_retour(p,c.cle.sens,D('.1')),D('.4'))
        self.assertEqual((e.etat_compte(),e.courbe,e.reponses,e.positions_ouvertes),avant)

    def test_refus_atomiques_du_futur_et_des_changements_de_contrat(self):
        b,e,_=cas_simulateur();t=e.instant_ms
        tarif=TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0))
        profils=(replace(b.profil,releve_ms=t+1),replace(b.profil,symbole_courtier='AUTRE'),
                 replace(b.profil,taille_contrat=b.profil.taille_contrat*2),
                 replace(b.profil,horaires=HorairesCotation((),(),t+1,t+60000)))
        for p in profils:
            with self.subTest(p=p):
                with self.assertRaises(ErreurRejeu):e.actualiser_profil(p,tarif,t)
                self.assertEqual(e.specifications(b.profil.symbole),b.profil)
        with self.assertRaises(ErreurRejeu):e.actualiser_profil(b.profil,tarif,t+1)

    def test_position_et_solde_conserves_et_validite_non_prolongee(self):
        b,e,c=cas_simulateur();t=e.instant_ms
        e.soumettre((c,));e.sur_tick(cotation_test(b,t+250));e.avancer_au(t+250)
        avant=(e.etat_compte(),e.positions_ouvertes,e.premiers_remplissages,e.courbe)
        tarif=TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0))
        e.actualiser_profil(replace(b.profil,releve_ms=t+250),tarif,t+250)
        self.assertEqual((e.etat_compte(),e.positions_ouvertes,e.premiers_remplissages,e.courbe),avant)
        b,e,_=cas_simulateur();e.actualiser_profil(b.profil,tarif,e.instant_ms)
        e.avancer_au(e.creation_ms+86400000)
        with self.assertRaises(ErreurRejeu):e.specifications(b.profil.symbole)
