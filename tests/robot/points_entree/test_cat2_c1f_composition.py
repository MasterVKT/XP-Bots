"""Même moteur London, comptes A/B indépendants, reprise par les constructeurs C08."""
import unittest
from robot.outils.orchestration import C
from robot.points_entree.test_cat1_c1f_composition import composition,evenement
from xpbots.app.c1f_composition_moteur import composer_moteur,rejouer_incident
from xpbots.noyau.c2_journal import serialiser
from xpbots.orchestration.c3_codec import serialiser_valeur


class TestJonctionComposition(unittest.TestCase):
    def test_reprises_c08_archivees_sur_chaque_prefixe_rejouees_exactement(self):
        from xpbots.app.c0_configuration import ErreurApplication
        for ab in (False,True):
            with self.subTest(ab=ab):
                i,p=composition(ab);m=composer_moteur(C,i,p);appels=dict(m.initialisation_calculs)
                sorties=[evenement(m,p,0),evenement(m,p,1)]
                m=composer_moteur(C,i,p,checkpoint=m.exporter_checkpoint(),entrees=m.entrees)
                marqueur=m.exporter_checkpoint_journal()
                sorties.append(evenement(m,p,2))
                r,ss=rejouer_incident(C,i,appels,m.entrees,m.exporter_checkpoint_journal(),reprises=(marqueur,))
                self.assertEqual(ss,tuple(sorties));self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
                with self.assertRaisesRegex(ErreurApplication,'MARQUEUR_REPRISE_HORS_PREFIXE'):
                    rejouer_incident(C,i,appels,m.entrees[:1],m.exporter_checkpoint_journal(),reprises=(marqueur,))
                autre=dict(i,deploiement='AUTRE_DEPLOIEMENT')
                etranger=composer_moteur(C,autre,p).exporter_checkpoint_journal()
                with self.assertRaisesRegex(ErreurApplication,'REPRISE_INCIDENT_DIVERGENTE'):
                    rejouer_incident(C,i,appels,m.entrees,m.exporter_checkpoint_journal(),reprises=(etranger,))

    def test_c05_reel_calendrier_permission_et_rejeu_identiques(self):
        from robot.outils.fondamental import message,calendrier,octets,table_importance
        from xpbots.noyau.c0a_temps import instant_vers_iso
        from xpbots.noyau.c1c_domaine import Sens
        from xpbots.orchestration.c0_contrats import ReceptionExterne,EntreeMoteur
        from datetime import datetime,timezone
        i,p=composition();t=i['initiales']['REFERENCE']['instant_ms'];jour=86400000
        def natif(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
        i['scenario_fondamental']=None
        i['table_heure']=dict(schema='xp-heure-serveur-v1',serveur='FIXTURE_S01',version=1,
            date_releve=instant_vers_iso(t),mesures=['SONDE_SYNTHETIQUE'],segments=[dict(
                debut_utc=instant_vers_iso(t-jour),fin_utc=instant_vers_iso(t+7*jour),decalage_secondes=0)])
        m=composer_moteur(C,i,p)
        self.assertFalse(m.bras['REFERENCE'].fondamental.evaluer('EURUSD',Sens.ACHAT,t).admise)
        permission=message(issued_at_utc=instant_vers_iso(t),known_at_utc=instant_vers_iso(t),
            valid_from_utc=instant_vers_iso(t),valid_until_utc=instant_vers_iso(t+int(
                C.technique.commun.fundamental_max_validity_seconds*1000)))
        horizon=int((C.technique.commun.news_forward_coverage_seconds+
                     C.technique.commun.news_calendar_max_age_seconds+60)*1000)
        cal=calendrier(export_ms=t,export_serveur=natif(t),export_gmt=natif(t),
            fenetre_debut_serveur=natif(t-3600000),fenetre_fin_serveur=natif(t+horizon))
        s=m.traiter(EntreeMoteur(t,1,receptions=(ReceptionExterne('PERMISSION',octets(permission),'EURUSD'),
            ReceptionExterne('CALENDRIER',octets(cal),table=table_importance()))))
        self.assertTrue(m.bras['REFERENCE'].fondamental.evaluer('EURUSD',Sens.ACHAT,t).admise)
        r,ss=rejouer_incident(C,i,dict(m.initialisation_calculs),m.entrees,m.exporter_checkpoint_journal())
        self.assertEqual(ss,(s,));self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())

    def test_ab_rejoue_octets_commandes_et_etats_sans_partager_portefeuilles(self):
        i,p=composition(True);m=composer_moteur(C,i,p)
        self.assertIsNot(p['REFERENCE'],p['IA'])
        sorties=tuple(evenement(m,p,n) for n in range(3))
        r,ss=rejouer_incident(C,i,dict(m.initialisation_calculs),m.entrees,m.exporter_checkpoint_journal())
        self.assertEqual(tuple(serialiser(e) for s in ss for e in s.enregistrements),
                         tuple(serialiser(e) for s in sorties for e in s.enregistrements))
        self.assertEqual(serialiser_valeur(ss),serialiser_valeur(sorties))
        self.assertEqual(r.exporter_checkpoint(),m.exporter_checkpoint())
        reprise=composer_moteur(C,i,p,checkpoint=r.exporter_checkpoint(),entrees=r.entrees)
        self.assertEqual(reprise.entrees,m.entrees)
        self.assertEqual(tuple(b.etat.historique for b in reprise.bras.values()),
                         tuple(b.etat.historique for b in m.bras.values()))
        self.assertEqual(reprise.initialisation_calculs,(('REFERENCE',()),('IA',())))

    def test_reprise_attente_cotation_passee_par_c08(self):
        from robot.outils.execution_partagee import signal
        i,p=composition();m=composer_moteur(C,i,p)
        # Pas de cotation : une vraie intention attendante est enregistrée dans le coordinateur.
        b=m.bras['REFERENCE'];t=i['initiales']['REFERENCE']['instant_ms']
        lot=b.coordinateur.traiter(t,signaux=(signal(cloture_ms=t),))
        self.assertTrue(lot.etat.intentions)
        cp=m.exporter_checkpoint()
        reprise=composer_moteur(C,i,p,checkpoint=cp,entrees=m.entrees)
        lot=reprise.traiter_evenement(t)
        self.assertFalse(any(s.commandes for _,s in lot.sorties))
        self.assertTrue(any(d.issue is not None and d.issue.detail=='reprise_sans_entree_retroactive'
                            for d in reprise.bras['REFERENCE'].coordinateur.etat.intentions))
