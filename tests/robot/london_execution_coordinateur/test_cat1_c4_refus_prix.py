"""Catégorie 1, couche 4 : refus natifs permanents, prix et références de tentatives."""
from dataclasses import replace
import unittest
from robot.outils.cycle_execution import bloc_cycle,remplissage
from robot.outils.execution_partagee import T
from xpbots.execution.c0a_types import EtatIntention
from xpbots.execution.c4_cycle import (CycleOrdre,EtatCycle,ReponseCourtier,NatureReponse,NatureCommande)
from xpbots.noyau.c1c_domaine import Motif

PRIX=('TRADE_RETCODE_REQUOTE','TRADE_RETCODE_PRICE_CHANGED','TRADE_RETCODE_PRICE_OFF','TRADE_RETCODE_TOO_MANY_REQUESTS')


def accuse(b,commande,code,*,definitif=False,t=T+1,reference='ack-prix',statut='REFUSE'):
    return ReponseCourtier(NatureReponse.ACCUSE,b.plan.reservation.cle,reference,t,
        dict(commande=commande.reference,statut=statut,code_natif=code,definitif=definitif,ordre=None))


def preparer():
    b=bloc_cycle();sortie=b.cycle.preparer_envoi(T)
    return b,next(c for c in sortie.commandes if c.nature is NatureCommande.ENTREE)


class TestRefusNatifs(unittest.TestCase):
    def test_chaque_refus_de_prix_est_sans_issue_finale_et_sans_quota(self):
        for code in PRIX:
            b,c=preparer();e=b.cycle.sur_reponse(accuse(b,c,code))
            self.assertEqual(e.etat.statut,EtatIntention.REFUSEE)
            self.assertEqual(b.cycle.refus_reessayable_ms,T+1)
            self.assertFalse(e.issues);self.assertFalse(e.etat.quota_compte)
            b.cycle.sur_minuterie(T+2)
            self.assertEqual(b.cycle.refus_reessayable_ms,T+1)
            self.assertFalse(b.cycle.preparer_envoi(T+2).commandes)

    def test_codes_permanents_conservent_leurs_motifs(self):
        cas={'INVALID_VOLUME':Motif.MIN_VOLUME_OR_RISK_REJECT,'LIMIT_VOLUME':Motif.MIN_VOLUME_OR_RISK_REJECT,
             'NO_MONEY':Motif.MARGIN_REJECT,'INVALID_STOPS':Motif.PROTECTION_ERROR,
             'LIMIT_POSITIONS':Motif.ACCOUNT_RISK_CAP,'LIMIT_ORDERS':Motif.ACCOUNT_RISK_CAP,
             'MARKET_CLOSED':Motif.ENVIRONMENT_NOT_READY,'INVALID_FILL':Motif.ENVIRONMENT_NOT_READY}
        for code,motif in cas.items():
            b,c=preparer();e=b.cycle.sur_reponse(accuse(b,c,'TRADE_RETCODE_'+code,definitif=True))
            self.assertEqual(e.issues[0].motif,motif)
            self.assertIsNone(b.cycle.refus_reessayable_ms)
            self.assertEqual(e.etat.statut,EtatIntention.REFUSEE)

    def test_inconnu_ou_classification_contradictoire_n_autorise_pas_de_tentative(self):
        for code,definitif in (('INCONNU',False),(PRIX[0],True)):
            b,c=preparer();e=b.cycle.sur_reponse(accuse(b,c,code,definitif=definitif))
            self.assertEqual(e.etat.statut,EtatIntention.INCONNUE)
            self.assertIsNone(b.cycle.refus_reessayable_ms);self.assertFalse(e.issues)
            self.assertTrue(any(v.nature is NatureCommande.RAPPROCHEMENT for v in e.commandes))

    def test_numero_d_entree_ne_reutilise_pas_la_minuterie(self):
        b,c=preparer();b.cycle.sur_reponse(accuse(b,c,PRIX[0]))
        avant=b.cycle.etat
        etat=EtatCycle(avant.cle,dernier_ms=T+2,numero_commande=avant.numero_commande,
            reponses_recues=avant.reponses_recues,numero_entree=avant.numero_entree)
        nouveau=CycleOrdre(b.params,b.signal,b.plan,b.profil,16,etat)
        e=nouveau.preparer_envoi(T+2);entree=next(v for v in e.commandes if v.nature is NatureCommande.ENTREE)
        self.assertTrue(entree.reference.endswith(':ENTREE:3'))
        self.assertEqual(e.etat.numero_entree,3);self.assertEqual(e.etat.numero_commande,4)
        faux=replace(c,reference=c.reference.rsplit(':',1)[0]+':2')
        with self.assertRaises(ValueError):nouveau.sur_reponse(accuse(b,faux,PRIX[0],t=T+3,reference='faux'))

    def test_ack_ancien_refuse_ne_termine_pas_la_nouvelle_tentative(self):
        b,c=preparer();b.cycle.sur_reponse(accuse(b,c,PRIX[0]));avant=b.cycle.etat
        n=CycleOrdre(b.params,b.signal,b.plan,b.profil,16,EtatCycle(avant.cle,dernier_ms=T+2,
            numero_commande=avant.numero_commande,reponses_recues=avant.reponses_recues,numero_entree=avant.numero_entree))
        n.preparer_envoi(T+2)
        e=n.sur_reponse(accuse(b,c,PRIX[0],t=T+3,reference='ack-ancien'))
        self.assertEqual(e.etat.statut,EtatIntention.ENVOYEE);self.assertFalse(e.issues)
        e=n.sur_reponse(accuse(b,c,'ACCEPTE_ANCIEN',t=T+4,reference='contradictoire',statut='ACCEPTE',definitif=True))
        self.assertEqual(e.etat.statut,EtatIntention.INCONNUE)

    def test_refus_apres_volume_positif_ne_devient_pas_reessayable(self):
        b,c=preparer();b.cycle.sur_reponse(remplissage(b),b.cotation)
        e=b.cycle.sur_reponse(accuse(b,c,PRIX[0],t=T+2))
        self.assertIsNone(b.cycle.refus_reessayable_ms)
        self.assertTrue(e.etat.quota_compte);self.assertFalse(e.issues)

    def test_etat_legacy_et_compteurs_invalides(self):
        b,c=preparer();e=replace(b.cycle.etat,numero_entree=0)
        r=CycleOrdre(b.params,b.signal,b.plan,b.profil,16,e)
        self.assertEqual(r.etat.numero_entree,1)
        for n in (True,-1,e.numero_commande+1):
            with self.assertRaises(ValueError):replace(e,numero_entree=n)
