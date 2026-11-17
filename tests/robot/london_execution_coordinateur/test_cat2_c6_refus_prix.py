"""Catégorie 2, couche 6 : nouvelles tentatives contrôlées sur le vrai bloc 0→6."""
from dataclasses import replace
from decimal import Decimal as D
import unittest
from robot.outils.coordinateur_execution import bloc_coordinateur,traiter,confirmer,bloc_remplissage,positionner
from robot.outils.execution_partagee import T,signal,cotation
from robot.outils.cycle_execution import remplissage
from xpbots.execution.c0a_types import EtatIntention
from xpbots.execution.c4_cycle import ReponseCourtier,NatureReponse,NatureCommande
from xpbots.noyau.c1c_domaine import Motif,NatureIssue

PRIX=('TRADE_RETCODE_REQUOTE','TRADE_RETCODE_PRICE_CHANGED','TRADE_RETCODE_PRICE_OFF','TRADE_RETCODE_TOO_MANY_REQUESTS')


def preparer():
    b=bloc_coordinateur();lot=traiter(b,signaux=(signal(),),cotations=(cotation(),));envoi=confirmer(b,lot)
    c=next(c for c in envoi.commandes if c.nature is NatureCommande.ENTREE)
    return b,c


def reponse(c,code=PRIX[0],*,t=T+1,definitif=False,statut='REFUSE',reference='ack-prix'):
    return ReponseCourtier(NatureReponse.ACCUSE,c.cle,reference,t,
        dict(commande=c.reference,statut=statut,code_natif=code,definitif=definitif,ordre=None))


def quote(t,**kw):return replace(cotation(),instant_fournisseur_ms=t,instant_reception_ms=t,**kw)


class TestNouvellesTentatives(unittest.TestCase):
    def test_prix_refuse_attend_nouveau_prix_et_nouvelle_preuve_pour_chaque_code(self):
        for code in PRIX:
            b,c=preparer();lot=traiter(b,T+1,reponses=(reponse(c,code),))
            self.assertFalse(lot.issues);self.assertFalse(lot.preparations)
            self.assertEqual(lot.etat.intentions[0].statut,EtatIntention.EN_ATTENTE_COTATION)
            self.assertFalse(lot.etat.reprise.reservations.reservations)
            for t,qs in ((T+2,()),(T+3,(quote(T+1),))):
                lot=traiter(b,t,cotations=qs)
                self.assertFalse(lot.preparations)
            lot=traiter(b,T+4,cotations=(quote(T+4),))
            self.assertEqual(len(lot.preparations),1)
            nouvelle=lot.preparations[0]
            self.assertNotEqual(nouvelle.reference,c.reference)
            self.assertTrue(nouvelle.reference.endswith(':ENTREE:3'))
            self.assertFalse(any(v.nature is NatureCommande.ENTREE for v in lot.commandes))
            envoi=confirmer(b,lot,T+4)
            self.assertEqual(tuple(v.reference for v in envoi.commandes if v.nature is NatureCommande.ENTREE),(nouvelle.reference,))

    def test_ttl_exact_et_gardes_sur_la_nouvelle_cotation(self):
        b,c=preparer();traiter(b,T+1,reponses=(reponse(c),))
        fin=T+int(b.technique.commun.entry_signal_ttl_seconds*1000)
        lot=traiter(b,fin,cotations=(quote(fin),))
        self.assertEqual(lot.issues[0].nature,NatureIssue.EXPIREE)
        self.assertEqual(lot.issues[0].motif,Motif.SIGNAL_EXPIRED);self.assertFalse(lot.preparations)
        b,c=preparer();traiter(b,T+1,reponses=(reponse(c),))
        cap=D(str(b.technique.commun.max_spread_price['EURUSD']))
        lot=traiter(b,T+2,cotations=(quote(T+2,ask=cotation().bid+cap+D('.00001')),))
        self.assertFalse(lot.preparations)
        self.assertEqual(lot.etat.intentions[0].derniere_cause,'SPREAD_CAP')

    def test_remplissage_de_la_seconde_tentative_consomme_une_seule_entree(self):
        b,c=preparer();traiter(b,T+1,reponses=(reponse(c),))
        lot=traiter(b,T+2,cotations=(quote(T+2),))
        self.assertEqual(len(lot.preparations),1)
        self.assertNotEqual(lot.preparations[0].reference,c.reference)
        v=bloc_remplissage(b,lot);confirmer(b,lot,T+2)
        positionner(b,v,T+3)
        lot=traiter(b,T+3,reponses=(remplissage(v,instant_ms=T+3),),cotations=(quote(T+3),))
        self.assertEqual(sum(i.nature is NatureIssue.REMPLIE for i in lot.issues),1)
        self.assertEqual(len(lot.etat.reprise.reservations.reservations),1)
        self.assertTrue(lot.etat.reprise.reservations.reservations[0].remplie)

    def test_inconnu_ne_liberera_pas_la_reserve_pour_un_nouveau_prix(self):
        b,c=preparer();lot=traiter(b,T+1,reponses=(reponse(c,'TRADE_RETCODE_CONNECTION',statut='INCONNU'),))
        self.assertEqual(len(lot.etat.reprise.reservations.reservations),1)
        lot=traiter(b,T+2,cotations=(quote(T+2),))
        self.assertFalse(lot.preparations);self.assertTrue(lot.etat.reprise.reservations.verrous)

    def test_refus_definitif_ne_prepare_pas_de_seconde_entree(self):
        b,c=preparer();lot=traiter(b,T+1,reponses=(reponse(c,'TRADE_RETCODE_NO_MONEY',definitif=True),))
        self.assertEqual(lot.issues[0].motif,Motif.MARGIN_REJECT)
        self.assertFalse(traiter(b,T+2,cotations=(quote(T+2),)).preparations)

    def test_reprise_entre_refus_et_nouveau_prix_n_est_pas_une_entree_retroactive(self):
        b,c=preparer();lot=traiter(b,T+1,reponses=(reponse(c),))
        r=bloc_coordinateur(t=T+2,etat=lot.etat)
        suivant=traiter(r,T+2,cotations=(quote(T+2),),signaux=(signal(),))
        self.assertFalse(suivant.preparations)
        self.assertFalse(any(v.nature is NatureCommande.ENTREE for v in suivant.commandes))
        self.assertEqual(suivant.etat.intentions[0].statut,EtatIntention.REFUSEE)
        self.assertEqual(suivant.etat.intentions[0].issue.detail,'reprise_sans_entree_retroactive')

    def test_refus_prix_concluant_apres_inconnu_libere_seulement_sa_reserve(self):
        b,c=preparer()
        lot=traiter(b,T+1,reponses=(reponse(c,'TRADE_RETCODE_CONNECTION',statut='INCONNU',reference='ack-inconnu'),))
        self.assertTrue(lot.etat.reprise.reservations.verrous)
        lot=traiter(b,T+2,reponses=(reponse(c,t=T+2),))
        self.assertFalse(lot.issues);self.assertFalse(lot.etat.reprise.reservations.reservations)
        self.assertFalse(lot.etat.reprise.reservations.verrous)
        lot=traiter(b,T+3,cotations=(quote(T+3),))
        self.assertEqual(len(lot.preparations),1)
        self.assertNotEqual(lot.preparations[0].reference,c.reference)

    def test_refus_ancien_repete_ne_libere_pas_la_nouvelle_reserve(self):
        b,c=preparer();traiter(b,T+1,reponses=(reponse(c),))
        lot=traiter(b,T+2,cotations=(quote(T+2),));confirmer(b,lot,T+2)
        avant=b.coordinateur.etat.reprise.reservations.reservations
        lot=traiter(b,T+3,reponses=(reponse(c,t=T+3,reference='ack-ancien'),))
        self.assertEqual(lot.etat.reprise.reservations.reservations,avant)
        self.assertFalse(lot.issues);self.assertEqual(lot.etat.intentions[0].statut,EtatIntention.ENVOYEE)
