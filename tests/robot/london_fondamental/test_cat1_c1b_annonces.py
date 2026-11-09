"""Catégorie 1, couche 1b : format MQL5, fenêtres et historique causal C05."""
from dataclasses import replace
import unittest
from robot.outils.fondamental import (T, commun, octets, calendrier, evenement, heure_native,
    table_importance, ConversionServeurScenario)
from xpbots.fondamental.c0_types import ErreurFondamental, TableImportance, millisecondes
from xpbots.fondamental.c1b_annonces import EtatCalendrier, GardeAnnonces


def garde(): return GardeAnnonces(commun(), ConversionServeurScenario())
def recevoir(g, p, t=T, table=None): return g.recevoir(octets(p), t, table or table_importance())


class TestGardeAnnonces(unittest.TestCase):
    def test_calendrier_vide_frais_et_couvert_admet(self):
        g=garde();r=recevoir(g,calendrier())
        self.assertTrue(r.acceptee)
        self.assertTrue(g.evaluer('EURUSD',T).admise)
        self.assertEqual((r.version.export_ms,r.version.reception_ms,r.version.annonces),(T,T,()))

    def test_champs_natifs_exacts_et_types_refuses(self):
        fautifs=[]
        for k in calendrier():
            p=calendrier();del p[k];fautifs.append(p)
        p=calendrier();p['extra']=0;fautifs.append(p)
        for changement in ({'schema':'autre'},{'version':True},{'evenements':{}},{'export_gmt':'2026-11-09T08:00:00Z'}):
            p=calendrier();p.update(changement);fautifs.append(p)
        for changement in ({'id_valeur':False},{'revision':1.0},{'importance':'CALENDAR_IMPORTANCE_LOW'}, {'heure_serveur':''}):
            fautifs.append(calendrier(evenements=[evenement(**changement)]))
        e=evenement();e['ajout']=1;fautifs.append(calendrier(evenements=[e]))
        for p in fautifs:
            g=garde()
            with self.subTest(p=p):
                self.assertFalse(recevoir(g,p).acceptee)
                self.assertEqual(g.etat,EtatCalendrier())

    def test_aucun_fuseau_serveur_ne_se_devine(self):
        for conversion in (lambda t: True,lambda t:T,lambda t: (_ for _ in ()).throw(ValueError('inconnue'))):
            g=GardeAnnonces(commun(),conversion)
            self.assertFalse(recevoir(g,calendrier()).acceptee)
        self.assertFalse(recevoir(garde(),calendrier(export_ms=T+1000)).acceptee,'export futur')

    def test_fenetre_debut_inclus_fin_exclue(self):
        g=garde();n=T+1800000;recevoir(g,calendrier(evenements=[evenement(n)]))
        avant=millisecondes(commun().news_before_seconds);apres=millisecondes(commun().news_after_seconds)
        for t,fermer in ((n-avant-1,False),(n-avant,True),(n+apres-1,True),(n+apres,False)):
            with self.subTest(t=t):self.assertEqual(g.evaluer('EURUSD',t).cloture_obligatoire,fermer)

    def test_devises_exactes_des_trois_symboles(self):
        for devise,concernes in (('EUR',{'EURUSD'}),('GBP',{'GBPUSD'}),('USD',{'EURUSD','GBPUSD','XAUUSD'})):
            g=garde();recevoir(g,calendrier(evenements=[evenement(devise=devise)]))
            self.assertEqual({s for s in commun().universe_priority if g.evaluer(s,T+900000).cloture_obligatoire},concernes)

    def test_fraicheur_exacte_et_peremption_sans_liquidation(self):
        g=garde();recevoir(g,calendrier())
        limite=T+millisecondes(commun().news_calendar_max_age_seconds)
        self.assertTrue(g.evaluer('EURUSD',limite).admise)
        d=g.evaluer('EURUSD',limite+1)
        self.assertEqual((d.detail,d.cloture_obligatoire),('CALENDRIER_PERIME',False))

    def test_couverture_exacte_et_juste_insuffisante(self):
        g=garde();fin=T+millisecondes(commun().news_forward_coverage_seconds)
        recevoir(g,calendrier(fenetre_fin_serveur=heure_native(fin)))
        self.assertTrue(g.evaluer('EURUSD',T).admise)
        d=g.evaluer('EURUSD',T+1)
        self.assertEqual((d.detail,d.cloture_obligatoire),('COUVERTURE_INSUFFISANTE',False))

    def test_annonce_connue_reste_prioritaire_sur_couverture_insuffisante(self):
        g=garde();recevoir(g,calendrier(evenements=[evenement()],fenetre_fin_serveur=heure_native(T+3600000)))
        self.assertEqual(g.evaluer('EURUSD',T).detail,'COUVERTURE_INSUFFISANTE')
        d=g.evaluer('EURUSD',T+900000)
        self.assertEqual((d.detail,d.cloture_obligatoire),('ANNONCE_HIGH',True))

    def test_annonce_tardive_ferme_immediatement_sans_changer_le_passe(self):
        g=garde();recevoir(g,calendrier())
        passe=g.evaluer('EURUSD',T+900000)
        r=recevoir(g,calendrier(2,T+960000,[evenement()]),T+960000)
        self.assertTrue(r.acceptee)
        self.assertEqual(r.version.annonces[0].known_at_ms,T+960000)
        self.assertTrue(g.evaluer('EURUSD',T+960000).cloture_obligatoire)
        self.assertEqual(g.evaluer('EURUSD',T+900000),passe)

    def test_relecture_ignoree_sans_rafraichir_la_connaissance(self):
        g=garde();p=calendrier();recevoir(g,p)
        etat=g.etat;r=recevoir(g,p,T+120000)
        self.assertTrue(r.ignoree)
        self.assertIs(g.etat,etat)
        self.assertEqual(g.version_connue(T+120000).reception_ms,T)
        p['export_gmt']=heure_native(T+1000,0);p['export_serveur']=heure_native(T+1000)
        self.assertEqual(recevoir(g,p,T+120000).raison,'VERSION_REECRITE')

    def test_versions_en_recul_et_reception_ancienne_rejetees_sans_mutation(self):
        g=garde();recevoir(g,calendrier(3));etat=g.etat
        self.assertEqual(recevoir(g,calendrier(2),T+1000).raison,'VERSION_ANTERIEURE')
        self.assertEqual(recevoir(g,calendrier(4),T-1).raison,'RECEPTION_EN_RECUL')
        self.assertIs(g.etat,etat)

    def test_evenement_inchange_garde_sa_connaissance_revision_la_renouvelle(self):
        g=garde();recevoir(g,calendrier(evenements=[evenement()]))
        recevoir(g,calendrier(2,T+60000,[evenement()]),T+60000)
        self.assertEqual(g.etat.versions[-1].annonces[0].known_at_ms,T)
        recevoir(g,calendrier(3,T+120000,[evenement(revision=1)]),T+120000)
        self.assertEqual(g.etat.versions[-1].annonces[0].known_at_ms,T+120000)
        self.assertEqual(len(g.etat.versions),3)

    def test_reprise_exacte_et_etat_altere_refuse(self):
        for mauvais in (None, (object(),)):
            with self.assertRaises(ErreurFondamental): EtatCalendrier(mauvais)
        g=garde();recevoir(g,calendrier(evenements=[evenement()]))
        recevoir(g,calendrier(2,T+60000,[evenement()]),T+60000)
        r=GardeAnnonces(commun(),ConversionServeurScenario(),g.etat)
        for t in (T,T+900000,T+2700000):
            self.assertEqual(r.evaluer('EURUSD',t),g.evaluer('EURUSD',t))
            self.assertEqual(r.prochaine_echeance_ms(t),g.prochaine_echeance_ms(t))
        v=g.etat.versions[-1];a=replace(v.annonces[0],known_at_ms=T+60000)
        for versions in ((v,g.etat.versions[0]),(g.etat.versions[0],replace(v,annonces=(a,)))):
            with self.assertRaises(ErreurFondamental):GardeAnnonces(commun(),ConversionServeurScenario(),EtatCalendrier(versions))

    def test_prochaine_echeance_est_une_borne_future_connue(self):
        g=garde();self.assertIsNone(g.prochaine_echeance_ms(T))
        recevoir(g,calendrier(evenements=[evenement()]))
        self.assertEqual(g.prochaine_echeance_ms(T),T+900000)
        self.assertEqual(g.prochaine_echeance_ms(T+900000),T+2700000)

    def test_provenance_fournisseur_preservee_et_nouvelle_connaissance(self):
        g=garde();recevoir(g,calendrier(evenements=[evenement()]))
        table=TableImportance('AUTRE_SOURCE_SYNTHETIQUE','v1',['CALENDAR_IMPORTANCE_HIGH'])
        recevoir(g,calendrier(2,T+60000,[evenement()]),T+60000,table)
        self.assertEqual(g.etat.versions[-1].annonces[0].known_at_ms,T+60000)
