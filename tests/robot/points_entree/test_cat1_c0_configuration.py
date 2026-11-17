"""Registres et gabarits : défauts de mode, causalité et configuration vérifiés."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import unittest

from robot.outils.orchestration import C,T
from robot.outils.qualification_mt5 import natif
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.fondamental.c0_types import TableImportance
from xpbots.fondamental.c1b_annonces import GardeAnnonces
from xpbots.app.c0_configuration import (analyser_registre,gabarit_registre,gabarit_fermetures,
                                        parametres_export,ErreurApplication)

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures'/'mql5_exports'


def registre(mode='PAPER'):
    d=gabarit_registre(C)
    d.update(deploiement='FIXTURE_APPLICATION',mode=mode,commit='a'*40,
             liaisons={'EURUSD':'EURUSD.micro'},justifications_liaisons={'EURUSD':'PREUVE_C04_FIXTURE'})
    d['historique']=dict(departs_ticks_utc_ms={'EURUSD':T-86400000},depuis_compte_utc_ms=T-86400000)
    return d


def decision(d,objet,preuves):
    return dict(id=objet,instant_utc=instant_vers_iso(T),objet=objet,responsable='OPERATEUR_FIXTURE',
                commit=d['commit'],empreintes=deepcopy(d['empreintes']),
                preuves={k:dict(chemin='.local/rapports/'+k+'.json',sha256='b'*64) for k in preuves})


class TestConfigurationApplication(unittest.TestCase):
    def test_gabarits_non_executables_et_sans_secret(self):
        d=gabarit_registre(C)
        self.assertEqual(d['mode'],C.ia.parametres['default_evaluation_mode'])
        self.assertEqual(d['empreintes']['technique'],C.technique.empreinte_octets)
        self.assertEqual(d['ingenierie']['boucle_ms'],100)
        with self.assertRaises(ErreurApplication):analyser_registre(d,C,T)
        self.assertFalse(any(m in json.dumps(d).lower() for m in ('password','login','api_key')))
        self.assertEqual(gabarit_fermetures(),dict(schema='xp-fermetures-v1',version=None,date_releve=None,fermetures=[]))

    def test_configuration_protegee_des_mutations_et_meta_exacte(self):
        d=registre();a=analyser_registre(d,C,T)
        d['liaisons']['EURUSD']='MUTATION'
        self.assertEqual(a.liaisons['EURUSD'],'EURUSD.micro')
        with self.assertRaises(TypeError):a.ingenierie['boucle_ms']=1
        m=a.meta;m['empreintes']['technique']='MUTATION'
        self.assertEqual(a.meta['empreintes']['technique'],C.technique.empreinte_octets)

    def test_reel_sans_decision_et_preuves_concordantes_refuse(self):
        d=registre('REEL')
        with self.assertRaisesRegex(ErreurApplication,'DECISION_DEPLOIEMENT'):analyser_registre(d,C,T)
        x=decision(d,'DEPLOIEMENT_REEL',('C10_RESERVE','C10_DEMO'));d['decisions']=[x]
        self.assertEqual(analyser_registre(d,C,T).mode,'REEL')
        x['commit']='c'*40
        with self.assertRaisesRegex(ErreurApplication,'DECISION_DEPLOIEMENT'):analyser_registre(d,C,T)
        # Lecture de qualification autorisée sans émettre ni autoriser d'ordres.
        self.assertEqual(analyser_registre(d,C,T,qualification=True).mode,'REEL')

    def test_neutralite_interdite_sur_les_deux_modes_natifs(self):
        for mode in ('DEMO','REEL'):
            d=registre(mode);d['scenario_fondamental']='TECHNICAL_CONTROL_NEUTRAL'
            with self.assertRaisesRegex(ErreurApplication,'NEUTRALITE_NATIVE'):analyser_registre(d,C,T,qualification=True)

    def test_veto_natif_exige_a13_du_meme_gel_et_du_meme_rapport(self):
        d=registre('DEMO');d['activation_veto']=True
        with self.assertRaisesRegex(ErreurApplication,'A13'):analyser_registre(d,C,T)
        d['statut_a13']=dict(statut='VALIDE',rapport='.local/rapports/A13.json',empreinte='b'*64)
        d['decisions']=[decision(d,'ACTIVATION_VETO_A13',('A13',))]
        self.assertTrue(analyser_registre(d,C,T).registre['activation_veto'])
        d['decisions'][0]['preuves']['A13']['sha256']='c'*64
        with self.assertRaisesRegex(ErreurApplication,'A13'):analyser_registre(d,C,T)

    def test_futur_empreintes_etrangeres_types_et_env_refuses(self):
        mutations=(lambda d:d.update(secret='INTERDIT'),
                   lambda d:d['empreintes'].update(technique='d'*64),
                   lambda d:d['ingenierie'].update(boucle_ms=True),
                   lambda d:d['ingenierie'].update(boucle_ms=101),
                   lambda d:d['historique']['departs_ticks_utc_ms'].update(EURUSD=T+1),
                   lambda d:d['chemins'].update(qualification='.local/.env'),
                   lambda d:d.update(activation_veto=1))
        for muter in mutations:
            d=registre();muter(d)
            with self.subTest(d=d),self.assertRaises(ErreurApplication):analyser_registre(d,C,T)
        d=registre();d['decisions']=[decision(d,'REPRISE',())]
        d['decisions'][0]['instant_utc']=instant_vers_iso(T+1)
        with self.assertRaisesRegex(ErreurApplication,'FUTURE'):analyser_registre(d,C,T)

    def table(self):
        return TableHeureServeur.depuis_document(json.loads((FIXTURES/'heure_serveur.json').read_text(encoding='utf-8')))

    def test_parametres_tsv_horizon_causal_consomme_par_c05(self):
        d=registre();table=self.table();t=1794301200000  # fixture MQL5 du 10 novembre
        b=parametres_export(C,table,d['liaisons'],d['ingenierie'])
        self.assertTrue(b.endswith(b'\n'));self.assertNotIn(b'\r',b);self.assertFalse(b.startswith(b'\xef\xbb\xbf'))
        lignes=[s.split('\t') for s in b.decode('utf-8').splitlines()]
        self.assertEqual(lignes[0],['schema','xp-parametres-export-v1'])
        horizon=int(lignes[3][1]);c=C.technique.commun
        self.assertEqual(horizon,c.news_forward_coverage_seconds+c.news_calendar_max_age_seconds+
                         d['ingenierie']['calendrier_export_ms']//1000)
        cal=json.loads((FIXTURES/'calendrier_v1.json').read_text(encoding='utf-8'))
        cal['fenetre_fin_serveur']=natif(table.serveur_de_utc(t+horizon*1000))
        convertir=lambda s:table.utc_de_serveur(int(datetime.strptime(s,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()*1000))
        g=GardeAnnonces(c,convertir)
        imp=TableImportance('MQL5_FIXTURE','FIXTURE_V1',('CALENDAR_IMPORTANCE_HIGH',))
        self.assertTrue(g.recevoir(json.dumps(cal).encode(),t,imp).acceptee)
        self.assertTrue(g.evaluer('EURUSD',t+d['ingenierie']['calendrier_export_ms']-1).admise)
        self.assertTrue(g.evaluer('EURUSD',t+int(c.news_calendar_max_age_seconds*1000)-1).admise)
        self.assertEqual(g.evaluer('EURUSD',t+int(c.news_calendar_max_age_seconds*1000)+1).detail,'CALENDRIER_PERIME')

    def test_parametres_refusent_injection_et_segments_arrondis(self):
        from dataclasses import replace
        d=registre();table=self.table()
        with self.assertRaises(ErreurApplication):parametres_export(C,table,{'EURUSD':'EURUSD\nsymbole\tAUTRE'},d['ingenierie'])
        table=replace(table,segments=(replace(table.segments[0],debut_utc_ms=table.segments[0].debut_utc_ms+1),))
        with self.assertRaises(ErreurApplication):parametres_export(C,table,d['liaisons'],d['ingenierie'])
