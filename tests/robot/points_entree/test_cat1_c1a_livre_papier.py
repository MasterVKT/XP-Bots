"""Livre durable : même simulateur, reprise causale et préfixe lié au checkpoint."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from robot.outils.orchestration import C
from robot.outils.rejeu import cas_simulateur,cotation_test
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1a_livre_papier import LivrePapier,TYPES_PAPIER
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission


def livre():
    b,e,c=cas_simulateur()
    condition=ConditionContrat(e.creation_ms,e.creation_ms+86400000,e.creation_ms,b.profil,
                              TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0)))
    p=LivrePapier(C,(condition,),e.creation_ms);p.avancer_au(e.instant_ms)
    return b,p,c


def reprendre(p,*,checkpoint=None,operations=None):
    i=p.initialisation
    return LivrePapier(C,i['conditions'],i['creation_ms'],i['scenario'],
        checkpoint=p.checkpoint if checkpoint is None else checkpoint,
        operations=p.operations_depuis(0) if operations is None else operations)


class TestLivrePapier(unittest.TestCase):
    def test_admission_fermee_jusqua_la_disponibilite_reelle(self):
        b,p,c=livre()
        self.assertIsInstance(p.specifications(b.profil.symbole),RefusExecution)
        p.fixer_disponibilite(b.profil.symbole,True,p.instant_ms)
        self.assertEqual(p.specifications(b.profil.symbole),b.profil)
        p.fixer_disponibilite(b.profil.symbole,False,p.instant_ms)
        self.assertIsInstance(reprendre(p).specifications(b.profil.symbole),RefusExecution)
        self.assertEqual(p.etat_compte().solde,D(100))

    def test_reprise_exacte_avec_position_et_puis_sortie(self):
        b,p,c=livre();t=p.instant_ms
        p.fixer_disponibilite(b.profil.symbole,True,t)
        p.soumettre((c,));p.sur_tick(cotation_test(b,t+250))
        q=reprendre(p)
        self.assertEqual(q.checkpoint,p.checkpoint)
        self.assertEqual((q.observation(),q.courbe,q.reponses),(p.observation(),p.courbe,p.reponses))
        tick=cotation_test(b,t+251,'1.09','1.0901')
        self.assertEqual(p.sur_tick(tick),q.sur_tick(tick))
        self.assertEqual((p.trades,p.etat_compte(),p.checkpoint),(q.trades,q.etat_compte(),q.checkpoint))

    def test_copie_du_contexte_et_initialisation_sans_alias(self):
        _,p,c=livre();contexte={'origine':{'valeurs':[1]}}
        p.enregistrer_contexte(c.cle,contexte)
        contexte['origine']['valeurs'].append(2)
        b=deserialiser_valeur(p.operations_depuis(0)[0],types_supplementaires=TYPES_PAPIER)
        args=deserialiser_valeur(b['arguments'],types_supplementaires=TYPES_PAPIER)
        self.assertEqual(args[1]['origine']['valeurs'],[1])
        i=p.initialisation;i['conditions']=()
        self.assertTrue(p.initialisation['conditions'])

    def test_prefixe_tronque_inverse_et_resultat_altere_refuses(self):
        b,p,_=livre();p.fixer_disponibilite(b.profil.symbole,True,p.instant_ms)
        p.extraire_reponses(p.instant_ms+1);ops=p.operations_depuis(0)
        for mauvais in (ops[:-1],tuple(reversed(ops))):
            with self.assertRaises(ErreurApplication):reprendre(p,operations=mauvais)
        d=deserialiser_valeur(ops[0],types_supplementaires=TYPES_PAPIER)
        d['resultat_sha256']='a'*64
        modifie=serialiser_valeur(d,types_supplementaires=TYPES_PAPIER)
        with self.assertRaises(ErreurApplication):reprendre(p,operations=(modifie,)+ops[1:])
        cp=dict(p.checkpoint);cp['signature']='a'*64
        with self.assertRaises(ErreurApplication):reprendre(p,checkpoint=cp)

    def test_checkpoint_borne_et_delta_sans_courbe_ni_historique(self):
        _,p,_=livre();avant=len(serialiser_valeur(p.checkpoint))
        for _ in range(100):p.extraire_reponses(p.instant_ms+1)
        self.assertLess(len(serialiser_valeur(p.checkpoint)),avant+32)
        self.assertNotIn('courbe',p.checkpoint)
        self.assertEqual(p.operations_depuis(100),())
        self.assertEqual(len(p.operations_depuis(99)),1)
        with self.assertRaises(ErreurApplication):p.operations_depuis(True)

    def test_actualisation_des_horaires_rejouee_sans_renouveler_le_livre(self):
        b,p,_=livre();t=p.instant_ms
        h=replace(b.profil.horaires,fermetures=(Intervalle(t,t+60000),))
        profil=replace(b.profil,horaires=h,releve_ms=t)
        p.actualiser_profil(profil,TarifCommission('ZERO_DECLARE',D(0),D(0),D(0),D(0)),t)
        p.fixer_disponibilite(profil.symbole,True,t)
        self.assertFalse(reprendre(p).specifications(profil.symbole).horaires.ouvert_a(t))

    def test_deux_livres_independants_et_erreur_de_mutation_invalide(self):
        b,p,c=livre();_,q,_=livre();p.soumettre((c,));p.sur_tick(cotation_test(b,p.instant_ms+250))
        self.assertTrue(p.positions_ouvertes);self.assertFalse(q.positions_ouvertes)
        with self.assertRaises(ValueError):q.sur_tick(object())
        # Le codec refuse l'objet avant toute mutation : le compte reste lisible.
        self.assertEqual(q.etat_compte().solde,D(100))
        with self.assertRaises(ValueError):q.extraire_reponses(q.creation_ms-1)
        with self.assertRaisesRegex(ErreurApplication,'REPRISE_REQUISE'):q.checkpoint
