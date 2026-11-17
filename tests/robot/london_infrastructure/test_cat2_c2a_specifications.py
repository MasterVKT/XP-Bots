"""Jonction : les profils natifs alimentent le vrai coordinateur C04/C07/C08."""
from dataclasses import replace
from decimal import Decimal as D
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from robot.outils.qualification_mt5 import T,JOUR,frontiere,exports,octets,iso,natif
from robot.outils.execution_partagee import configuration,signal,cotation
from robot.outils.coordinateur_execution import traiter,confirmer,bloc_remplissage,positionner
from robot.outils.cycle_execution import remplissage
from robot.doublures.calculs_execution import CalculSynthetique
from xpbots.execution.c0a_types import EtatCompte
from xpbots.execution.c0b_controles import ControleTechniqueNeutre
from xpbots.execution.c1b_gardes import reconstituer_base_utc
from xpbots.execution.c4_cycle import NatureCommande
from xpbots.execution.c5b_reprise import ObservationNative
from xpbots.execution.c6_coordinateur import CoordinateurCompte
from xpbots.noyau.c1b_instrument import ProfilInstrument,Intervalle
from xpbots.noyau.c1c_domaine import CauseCloture


class TestJonctionSpecifications(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk,self.session,self.specs=frontiere(self.temp.name)
        self.addCleanup(self.session.fermer)
        self.s,self.f=exports()
        self.specs.recevoir_exports(T,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(self.f))

    def bloc(self):
        p=self.specs.instrument('EURUSD',T);pc=self.specs.compte(T);conf=configuration()
        self.assertIsInstance(p,ProfilInstrument)
        compte=EtatCompte(T,D(100),D(100),D(0));port=CalculSynthetique(compte,p)
        base=reconstituer_base_utc(compte,(),Intervalle(T//JOUR*JOUR,T+1),aucune_position_minuit=True)
        c=CoordinateurCompte(conf,'synthetique',{'EURUSD':p},pc,port,ControleTechniqueNeutre(),T,longueur_empreinte=16,
            mode='REJEU',observation=ObservationNative(compte,T//JOUR*JOUR,True),base_utc=base)
        return SimpleNamespace(coordinateur=c,port=port,technique=conf,base=base)

    def test_dimensionnement_reel_sur_grille_native_et_preuve_avant_entree(self):
        b=self.bloc();s=signal(cloture_ms=T);q=cotation(instant_fournisseur_ms=T,instant_reception_ms=T)
        lot=traiter(b,T,signaux=(s,),cotations=(q,))
        self.assertEqual(len(lot.preparations),1)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
        plan=lot.etat.reprise.cycles[0].plan;p=b.port.profil
        self.assertEqual(plan.volume%p.volume_pas,0)
        self.assertLessEqual(plan.risque,D(str(b.technique.commun.risk_fraction_per_entry))*D(100))
        self.assertTrue(any(c.nature is NatureCommande.ENTREE for c in confirmer(b,lot,T).commandes))

    def test_nouvelle_fermeture_native_impose_sortie_sur_le_vrai_coordinateur(self):
        b=self.bloc();q=cotation(instant_fournisseur_ms=T,instant_reception_ms=T)
        lot=traiter(b,T,signaux=(signal(cloture_ms=T),),cotations=(q,));v=bloc_remplissage(b,lot)
        confirmer(b,lot,T);positionner(b,v,T+1)
        traiter(b,T+1,reponses=(remplissage(v,instant_ms=T+1),),cotations=(replace(q,instant_fournisseur_ms=T+1,instant_reception_ms=T+1),))
        f=dict(self.f,version=2,date_releve=iso(T+2),fermetures=[dict(symbole='EURUSD.micro',debut_utc=iso(T+30000),
            fin_utc=iso(T+3600000),nature='FERMETURE',source='AVIS_FIXTURE_MODIFIE')])
        self.specs.recevoir_exports(T+2,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(f))
        b.port.profil=self.specs.instrument('EURUSD',T+2)
        lot=traiter(b,T+2,cotations=(replace(q,instant_fournisseur_ms=T+2,instant_reception_ms=T+2),))
        fermetures=[c for c in lot.commandes if c.nature is NatureCommande.CLOTURE]
        self.assertEqual(len(fermetures),1)
        self.assertIs(fermetures[0].donnees['cause'],CauseCloture.FERMETURE_NATIVE)
        self.assertFalse(any(c.nature is NatureCommande.ENTREE for c in lot.commandes))
