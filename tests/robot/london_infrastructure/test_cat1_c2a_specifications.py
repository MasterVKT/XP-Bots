"""Contrat propre C04 : SDK doublé, session et noyau réels."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.qualification_mt5 import T,JOUR,frontiere,exports,octets,iso,natif,preuve_qualification
from robot.outils.faux_mt5 import FauxMT5
from xpbots.infra.c0a_types import ErreurInfra,TableHeureServeur,SegmentServeur
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1b_instrument import ProfilCompte,ProfilInstrument


class TestSpecifications(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.sdk,self.session,self.specs=frontiere(self.temp.name)
        self.addCleanup(self.session.fermer)
        self.s,self.f=exports()

    def recevoir(self,t=T,s=None,f=None):
        return self.specs.recevoir_exports(t,seances={'EURUSD.micro':octets(self.s if s is None else s)},
            fermetures=octets(self.f if f is None else f))

    def test_profil_native_zero_connu_frais_swaps_et_horaires(self):
        nouveaux=self.recevoir()
        self.assertEqual(len(nouveaux),2)
        p=self.specs.instrument('EURUSD',T)
        self.assertIsInstance(p,ProfilInstrument)
        self.assertEqual(p.taille_contrat,1000)
        self.assertEqual(p.volume_min, p.volume_pas*10)
        self.assertEqual(p.commission_par_lot_par_cote,0)
        self.assertEqual(p.swap_achat, -p.swap_vente*5)
        self.assertTrue(p.horaires.ouvert_a(T))
        self.assertEqual(p.horaires.prochaine_fermeture_apres(T),T//JOUR*JOUR+23*3600000)
        c=self.specs.compte(T)
        self.assertIsInstance(c,ProfilCompte);self.assertEqual(c.type_compte,'STANDARD')
        self.assertFalse(any(a[0]=='order_send' for a in self.sdk.appels))

    def test_champs_absents_non_finis_et_droits_modifies_ne_valent_pas_zero(self):
        self.recevoir();n=self.sdk.symboles['EURUSD.micro']
        for champ,valeur in (('trade_tick_value',None),('volume_step',float('nan')),('swap_long',None),('digits',True),
                             ('filling_mode',0),('chart_mode',self.sdk.SYMBOL_CHART_MODE_LAST),('currency_base','BTC'),('spread_float',None)):
            with self.subTest(champ=champ):
                self.sdk.symboles['EURUSD.micro']=n._replace(**{champ:valeur})
                self.assertIsInstance(self.specs.instrument('EURUSD',T),RefusExecution)
        self.sdk.symboles['EURUSD.micro']=n._replace(trade_mode=self.sdk.SYMBOL_TRADE_MODE_CLOSEONLY)
        self.assertEqual(self.specs.instrument('EURUSD',T).mode_negociation,'CLOSE_ONLY')

    def test_compte_change_devise_levier_serveur_refuse_sans_login(self):
        self.recevoir();c=self.sdk.compte
        for champ,v in (('currency','EUR'),('leverage',200),('server','AUTRE'),('margin_so_mode',None),('company',None),('login',987654321)):
            self.sdk.compte=c._replace(**{champ:v})
            self.assertIsInstance(self.specs.compte(T),RefusExecution)
        self.assertNotIn('login',repr(self.specs.exporter_etat()))
        self.assertFalse(any(a[0]=='login' for a in self.sdk.appels))

    def test_preuves_externes_strictes_et_datees(self):
        q=preuve_qualification(self.sdk)
        cas=[]
        for niveau,champ,valeur in (('compte','type_compte','CENT'),('compte','assiette_stop_out','EQUITY'),
                ('symbole','commission_nulle_confirmee',False),('symbole','protections_a_l_entree',False),
                ('symbole','commission_par_lot_par_cote',None),('symbole','modes_remplissage',['RETURN'])):
            mod=deepcopy(q);c=mod['compte'] if niveau=='compte' else mod['symboles']['EURUSD.micro'];c[champ]=valeur
            cas.append(mod)
        for mod in cas:
            with self.subTest(preuve=mod):
                if mod['symboles']['EURUSD.micro']['modes_remplissage']==['RETURN']:
                    _,session,specs=frontiere(self.temp.name,qualification=mod)
                    try:
                        specs.recevoir_exports(T,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(self.f))
                        self.assertIsInstance(specs.instrument('EURUSD',T),RefusExecution)
                    finally:session.fermer()
                else:
                    with self.assertRaises(ErreurInfra):frontiere(self.temp.name,qualification=mod)
        self.assertIsInstance(self.specs.compte(q['known_at_utc_ms']-1),RefusExecution)
        self.assertIsInstance(self.specs.compte(q['valid_until_utc_ms']),RefusExecution)

    def test_liaison_non_minimale_et_departage_cout_lexical(self):
        q=preuve_qualification(self.sdk);n=self.sdk.symboles['EURUSD.micro']
        q['symboles']['EURUSD.a']=deepcopy(q['symboles']['EURUSD.micro'])
        self.sdk.symboles['EURUSD.a']=n._replace(name='EURUSD.a',trade_contract_size=100)
        _,session,specs=frontiere(self.temp.name,qualification=q,sdk=self.sdk)
        try:
            specs.recevoir_exports(T,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(self.f))
            self.assertIsInstance(specs.instrument('EURUSD',T),RefusExecution)
            self.sdk.symboles['EURUSD.a']=n._replace(name='EURUSD.a')
            self.assertIsInstance(specs.instrument('EURUSD',T),RefusExecution)
        finally:session.fermer()
        q['symboles']['EURUSD.a']['cout_aller_retour_usd_volume_min']='1'
        autre_sdk,session,specs=frontiere(self.temp.name,qualification=q)
        try:
            autre_sdk.symboles['EURUSD.a']=n._replace(name='EURUSD.a')
            specs.recevoir_exports(T,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(self.f))
            self.assertIsInstance(specs.instrument('EURUSD',T),ProfilInstrument)
        finally:session.fermer()

    def test_doublon_ne_renouvelle_pas_fraicheur_apres_reprise(self):
        self.recevoir();etat=self.specs.exporter_etat()
        self.assertFalse(self.recevoir(T+1000))
        self.assertEqual(self.specs.exporter_etat()['exports'],etat['exports'])
        _,session,specs=frontiere(self.temp.name,etat=etat)
        try:
            self.assertFalse(specs.recevoir_exports(T+7200001,seances={'EURUSD.micro':octets(self.s)},fermetures=octets(self.f)))
            self.assertIsInstance(specs.instrument('EURUSD',T+7200001),RefusExecution)
            self.assertEqual(specs.exporter_etat()['exports'],etat['exports'])
        finally:session.fermer()

    def test_version_reculee_ou_reutilisee_differe_refuse_puis_version_suivante(self):
        self.recevoir();mod=deepcopy(self.s);mod['jours'][2]['negociation'][0]['fin']='22:00:00'
        self.recevoir(T+1000,s=mod)
        self.assertTrue(self.specs.erreurs_exports)
        self.assertIsInstance(self.specs.instrument('EURUSD',T+1000),RefusExecution)
        mod['version']=2;mod['export_serveur']=mod['export_gmt']=natif(T+2000)
        self.recevoir(T+2000,s=mod)
        self.assertIsInstance(self.specs.instrument('EURUSD',T+2000),ProfilInstrument)
        self.recevoir(T+3000,s=self.s)
        self.assertIsInstance(self.specs.instrument('EURUSD',T+3000),RefusExecution)

    def test_absence_invalides_json_jours_intervalles_et_fermetures(self):
        self.recevoir()
        mauvais=[b'{}',b'{"schema":"a","schema":"b"}',octets(dict(self.s,version=True)),
            octets(dict(self.s,jours=self.s['jours'][:6])),octets(dict(self.s,export_gmt=natif(T+1000)))]
        j=deepcopy(self.s);j['jours'][2]['negociation']=[dict(debut='12:00:00',fin='13:00:00'),dict(debut='11:00:00',fin='12:00:00')]
        mauvais.append(octets(j))
        for b in mauvais:
            self.specs.recevoir_exports(T,seances={'EURUSD.micro':b},fermetures=octets(self.f))
            self.assertIsInstance(self.specs.instrument('EURUSD',T),RefusExecution)
        self.specs.recevoir_exports(T,seances={'EURUSD.micro':octets(self.s)},fermetures=None)
        self.assertIsInstance(self.specs.instrument('EURUSD',T),RefusExecution)

    def test_intersection_cotation_negociation_fermeture_connue(self):
        self.s['jours'][2]['cotation']=[dict(debut='08:00:00',fin='12:00:00')]
        self.f['fermetures']=[dict(symbole='EURUSD.micro',debut_utc=iso(T+1800000),fin_utc=iso(T+3600000),
            nature='SEANCE_REDUITE',source='AVIS_SYNTHETIQUE')]
        self.recevoir();h=self.specs.instrument('EURUSD',T).horaires
        self.assertTrue(h.ouvert_a(T));self.assertEqual(h.prochaine_fermeture_apres(T),T+1800000)
        self.assertFalse(h.ouvert_a(T+1800000));self.assertTrue(h.ouvert_a(T+3600000))
        self.assertFalse(h.ouvert_a(T//JOUR*JOUR+13*3600000))

    def test_conversion_offset_qualifie_ambiguite_et_00_00_non_inferes(self):
        self.assertEqual(self.specs.convertir_serveur(natif(T)),T)
        with self.assertRaises(ErreurInfra):self.specs.convertir_serveur('2026.11.1 09:00:00')
        j=deepcopy(self.s);j['jours'][2]['negociation']=[dict(debut='00:00:00',fin='00:00:00')]
        self.recevoir(s=j);self.assertIsInstance(self.specs.instrument('EURUSD',T),RefusExecution)
        table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('DST_SYNTHETIQUE',),
            (SegmentServeur(T-14*JOUR,T,3600),SegmentServeur(T,T+30*JOUR,0)))
        _,session,specs=frontiere(self.temp.name,table=table)
        try:
            with self.assertRaises(ErreurInfra):specs.convertir_serveur(natif(T+1000))
        finally:session.fermer()

    def test_etat_corrompu_ou_configuration_changee_refuse(self):
        self.recevoir();etat=self.specs.exporter_etat()
        for mutation in ('empreinte','reception','version'):
            mod=deepcopy(etat)
            if mutation=='empreinte':mod['configuration_sha256']='0'*64
            if mutation=='reception':mod['exports']['EURUSD.micro']['reception_ms']=T+1
            if mutation=='version':mod['exports']['EURUSD.micro']['version']=True
            with self.assertRaises(ErreurInfra):frontiere(self.temp.name,etat=mod)

    def test_offset_non_nul_et_seance_traversant_minuit_sans_fausse_fermeture(self):
        table=TableHeureServeur('SERVEUR_FIXTURE',2,iso(T-1000),('OFFSET_SYNTHETIQUE',),
            (SegmentServeur(T-14*JOUR,T+30*JOUR,3600),))
        _,session,specs=frontiere(self.temp.name,table=table)
        try:
            s=deepcopy(self.s);s['export_serveur']=natif(T+3600000)
            specs.recevoir_exports(T,seances={'EURUSD.micro':octets(s)},fermetures=octets(self.f))
            p=specs.instrument('EURUSD',T)
            self.assertIsInstance(p,ProfilInstrument)
            self.assertEqual(p.horaires.prochaine_fermeture_apres(T),T//JOUR*JOUR+22*3600000)
            self.assertEqual(specs.convertir_serveur(natif(T+3600000)),T)
        finally:session.fermer()
        s=deepcopy(self.s)
        for j in s['jours']:
            j['cotation']=[dict(debut='00:00:00',fin='24:00:00')]
            j['negociation']=[dict(debut='22:00:00',fin='02:00:00')]
        self.recevoir(s=s)
        h=self.specs.instrument('EURUSD',T).horaires
        soir=T//JOUR*JOUR+23*3600000
        self.assertEqual(h.prochaine_fermeture_apres(soir),T//JOUR*JOUR+JOUR+2*3600000)
