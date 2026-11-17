"""Catégorie 2, couche 3 : codec durable et états de marché reçus par le vrai moteur."""
from dataclasses import replace
import unittest
from robot.orchestration.test_cat1_c2_marche import composer, recevoir, paquet
from robot.outils.orchestration import C, T
from xpbots.orchestration.c0_contrats import ErreurOrchestration
from xpbots.orchestration.c1_bras import construire_bras
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.orchestration.c3_codec import serialiser_valeur, deserialiser_valeur
from xpbots.execution.c0b_controles import ControleTechniqueNeutre


class TestCodecMarche(unittest.TestCase):
    def test_checkpoint_decode_restaure_horaires_et_couverture_connus(self):
        m,b,p,h,c=composer();recevoir(m,p,T,paquet(T))
        cp=deserialiser_valeur(serialiser_valeur(m.exporter_checkpoint()))
        journal=deserialiser_valeur(serialiser_valeur(m.entrees))
        b2=construire_bras(C,b.deploiement,b.nom,p.profils,p,b.fondamental,cp.instant_ms,
            observation=p.observation(),base_utc=p.base_utc(),etat=cp.bras[0])
        r=MoteurDecision(C,(b2,),h,c,scenario_fondamental=ControleTechniqueNeutre.scenario,checkpoint=cp,entrees=journal)
        self.assertEqual(r.exporter_checkpoint(),cp)
        self.assertEqual(r.etat.flux,m.etat.flux)

    def test_journal_decode_rejoue_les_mises_a_jour_sans_frontiere(self):
        m,b,p,h,c=composer();sorties=[]
        for n in range(3):sorties.append(recevoir(m,p,T+n,paquet(T+n,n+1)))
        journal=deserialiser_valeur(serialiser_valeur(m.entrees))
        r,_,port,_,_=composer()
        def interdit(*a,**kw):raise AssertionError('backend du codec au rejeu')
        for n in ('profit','frais_aller_retour','frais_sortie','marge','controler','specifications','etat_compte'):
            setattr(port,n,interdit)
        for j,s in zip(journal,sorties):self.assertEqual(r.rejouer(j),s)
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())

    def test_corruption_du_flux_enveloppe_refusee_par_le_sceau(self):
        m,_,p,_,_=composer();recevoir(m,p,T,paquet(T))
        cp=m.exporter_checkpoint();s,v=cp.flux[0]
        faux=replace(cp,flux=((s,v.replace('"version":1','"version":2')),))
        with self.assertRaises(ErreurOrchestration):deserialiser_valeur(serialiser_valeur(faux))
