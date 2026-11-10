"""Jonctions sur le vrai London, C05, lecteur IA, coordinateur et simulateur."""
from dataclasses import replace
from datetime import date,timedelta
from decimal import Decimal as D
import unittest
from robot.outils.rejeu import (C,experience_courte,experience_london,fabriques_horloge,lot_csv)
from xpbots.rejeu.c0a_types import ErreurRejeu
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c2_executeur import (ControlesRejeu,SourceTicks,executer_experience,
    executer_continu,rejouer_experience,AutorisationReserve)


def neutre(_):return ControlesRejeu.technique_neutre(C)


class TestJonctionExecuteur(unittest.TestCase):
    def test_vrai_london_precharge_ete_hiver_reference_et_stress(self):
        for jour,scenario in ((date(2026,7,15),'REFERENCE'),(date(2026,1,14),'STRESS')):
            with self.subTest(jour=jour,scenario=scenario):
                d,source,conditions,_=experience_london(jour,scenario=scenario)
                r=executer_experience(C,d,source,conditions,fabrique_controles=neutre)
                b=r.bras['REFERENCE']
                self.assertTrue(b.trades);self.assertTrue(r.complet)
                self.assertTrue(all(t.entree_ms>=r.debut_effectif_ms for t in b.trades))
                self.assertTrue(all('rapport_range_atr_h1' in t.contexte for t in b.trades))
                self.assertGreaterEqual(b.comptages[('LONDON_V3','EURUSD')].configurations,len(b.trades))

    def test_journal_rejoue_exactement_sans_backend_ni_seconde_lecture(self):
        d,source,conditions,s,compteur=experience_courte();fab=fabriques_horloge((s,))
        r=executer_experience(C,d,source,conditions,fabriques=fab,fabrique_controles=neutre)
        transmissions=tuple((j.entree.instant_ms,v) for j in r.pilote.entrees
            for nom,maj in j.entree.mises_a_jour if nom=='REFERENCE' for v in maj.reponses)
        self.assertEqual(transmissions,tuple((v.instant_ms,v) for v in r.pilote.reponses['REFERENCE']))
        lignes,entrees,etats=rejouer_experience(r,fabriques=fab,fabrique_controles=neutre)
        self.assertEqual(lignes,r.pilote.enregistrements);self.assertEqual(entrees,r.pilote.entrees)
        self.assertEqual(etats['REFERENCE'],r.bras['REFERENCE'].etat)
        self.assertEqual(compteur,['LECTURE'])

    def test_deux_methodes_sur_un_compte_arbitrees_par_le_vrai_coordinateur(self):
        d,source,conditions,s,_=experience_courte()
        fab=fabriques_horloge((s,),(C.technique.london['strategy_id'],C.technique.ema['strategy_id']))
        r=executer_experience(C,d,source,conditions,fabriques=fab,fabrique_controles=neutre)
        self.assertEqual(len(r.bras),1);b=r.bras['REFERENCE']
        self.assertEqual(len(b.premiers_remplissages),1)
        self.assertEqual(b.premiers_remplissages[0][0].strategie,C.technique.london['strategy_id'])
        self.assertEqual(b.comptages[('EMA_V3','EURUSD')].refus['SYMBOL_BUSY'],1)
        self.assertEqual(b.courbe[0].fonds_propres,D(100))

    def test_veto_archive_ab_et_rejeu_integral_sans_reinference(self):
        from robot.squelette.test_contexte_ia import paquet
        from xpbots.rejeu.squelette import SourceSnapshotScenario
        d,source,conditions,s,_=experience_courte(mode=C.ia.parametres['default_evaluation_mode'])
        def controles(_):
            c=neutre(None)
            return replace(c,source_ia=SourceSnapshotScenario(c.lecteur_ia,(paquet(s-1000,s+60000),)))
        fab=fabriques_horloge((s,))
        r=executer_experience(C,d,source,conditions,fabriques=fab,fabrique_controles=controles)
        self.assertEqual(len(r.bras['REFERENCE'].trades),1);self.assertFalse(r.bras['IA'].premiers_remplissages)
        self.assertEqual(r.bras['IA'].comptages[('LONDON_V3','EURUSD')].refus['AI_CONTEXT_VETO'],1)
        lignes,_,_=rejouer_experience(r,fabriques=fab,fabrique_controles=controles)
        self.assertEqual(lignes,r.pilote.enregistrements)

    def test_perturbation_future_ne_change_pas_les_decisions_passees(self):
        d,source,conditions,s,_=experience_courte();fab=fabriques_horloge((s,))
        r=executer_experience(C,d,source,conditions,fabriques=fab,fabrique_controles=neutre)
        original=tuple(source.lire());lignes=original[:-1]+(original[-1].replace('1.102','1.09'),)
        _,m=lot_csv(lignes,debut=source.manifeste.intervalle.debut_ms,fin=source.manifeste.intervalle.fin_ms)
        futur=SourceTicks(m,lambda:iter(lignes))
        autre=executer_experience(C,d,futur,conditions,fabriques=fab,fabrique_controles=neutre)
        def prefixe(v):return tuple(j for j in v.pilote.entrees if j.entree.instant_ms<s+900000)
        self.assertEqual(prefixe(r),prefixe(autre))

    def test_continu_garde_un_seul_capital_et_arret_global(self):
        # Le flux disponible couvre deux jours ; le reste est déclaré manquant, jamais inventé.
        d,source,conditions,s,_=experience_courte(jour=date(2020,1,1),perte=True)
        bloc=charger_protocole(C).continu
        # Un gap extrême atteint le seuil réel C07 sur le premier trade.
        lignes=tuple(v.replace('1.09','1.0') for v in source.lire())
        fin=bloc.intervalle_ms.fin_ms
        couverture=source.manifeste.couverture
        from xpbots.noyau.c1b_instrument import Intervalle,HorairesCotation
        a=source.manifeste.intervalle.debut_ms
        h=HorairesCotation((Intervalle(a,fin),),(),a,fin+3600000)
        _,m=lot_csv(lignes,debut=a,fin=fin,couverture=couverture,trous=(Intervalle(couverture[-1].fin_ms,fin),),horaires={'EURUSD':h})
        conditions=tuple(replace(c,fin_ms=fin,profil=replace(c.profil,horaires=h)) for c in conditions)
        d=replace(d,bloc=bloc,autorisation=AutorisationReserve(True,'a'*64,lambda _:True))
        r=executer_continu(C,d,SourceTicks(m,lambda:iter(lignes)),conditions,
            fabriques=fabriques_horloge((s,)),fabrique_controles=neutre)
        b=r.bras['REFERENCE'];self.assertEqual(b.courbe[0].fonds_propres,D(100))
        self.assertTrue(b.etat.coordinateur.reprise.gardes.arret_global)
        self.assertFalse(r.couverture_complete);self.assertFalse(r.complet)
        self.assertGreater(len(r.jours),1000)
