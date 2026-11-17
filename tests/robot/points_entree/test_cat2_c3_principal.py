"""Commandes sur les vrais blocs ; seules les frontières SDK et horloge sont doublées."""
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch
import gzip,json,os,unittest
from robot.outils.boucle_directe import HarnaisDirect
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.assemblage_mt5 import parametres,installer_controles
from robot.outils.qualification_mt5 import iso
from robot.outils.orchestration import C
from robot.points_entree.test_cat1_c0_configuration import registre
from robot.points_entree.test_cat1_c1c_rejeu import demande_fixture
from robot.points_entree.test_cat1_c3_principal import appeler
from xpbots.app.c1a_livre_papier import TYPES_PAPIER
from xpbots.app.c1c_cli_rejeu import encoder_rejeu
from xpbots.orchestration.c3_codec import deserialiser_valeur


class TestJonctionPrincipal(HarnaisDirect,unittest.TestCase):
    def preparer(self,mode='PAPER'):
        self.sdk=FauxMT5(self.commun,instant_ms=self.temps);table,q,_=parametres(self.sdk)
        dossier=self.commun/'Files';installer_controles(dossier,t=self.temps)
        p=patch.dict(os.environ,{'XPBOTS_COMMON_FILES_DIR':str(dossier)});p.start();self.addCleanup(p.stop)
        d=registre(mode);d['chemins'].update(racine=str(self.root),qualification=str(self.root/'qualification.json'),table_heure=str(self.root/'table.json'))
        self.registre=self.root/'registre.json';self.registre.write_text(json.dumps(d),encoding='utf-8')
        (self.root/'qualification.json').write_text(json.dumps(q),encoding='utf-8')
        doc=dict(schema='xp-heure-serveur-v1',serveur=table.serveur,version=table.version,date_releve=table.date_releve,
            mesures=list(table.mesures),segments=[dict(debut_utc=iso(s.debut_utc_ms),fin_utc=iso(s.fin_utc_ms),
                decalage_secondes=s.decalage_secondes) for s in table.segments])
        (self.root/'table.json').write_text(json.dumps(doc),encoding='utf-8');self.sdk.appels.clear()
        return d

    def test_qualification_et_parametres_export_par_les_controleurs_reels(self):
        d=self.preparer('DEMO');tsv=self.root/'parametres.tsv';rapport=self.root/'c04.json'
        self.assertEqual(appeler(['parametres-export','--registre',self.registre,'--sortie',tsv],sdk=self.sdk)[0],0)
        self.assertTrue(tsv.read_bytes().startswith(b'schema\txp-parametres-export-v1\n'))
        self.assertFalse(self.sdk.appels)
        code,s,e=appeler(['qualifier','--registre',self.registre,'--sortie',rapport],sdk=self.sdk)
        self.assertEqual(code,0,(s,e));r=json.loads(rapport.read_bytes())
        self.assertEqual(r['conclusion'],'LECTURES_C04_COMPLETES');self.assertFalse(r['autorisation_execution'])
        self.assertFalse(self.sdk.attache)
        self.assertFalse(any(n in ('order_send','order_check') for n,*_ in self.sdk.appels))

    def test_direct_paper_capital_cf_archive_et_commande_incident_identique(self):
        self.preparer();self.sdk.compte=self.sdk.compte._replace(balance=1000.,equity=1000.,margin_free=1000.)
        archive=self.root/'incident.json';rapport=self.root/'rapport_incident.json'
        code,s,e=appeler(['direct','--registre',self.registre,'--archive-incident',archive,'--max-iterations','3'],sdk=self.sdk)
        self.assertEqual(code,0,(s,e));self.assertFalse(self.sdk.attache)
        d=deserialiser_valeur(archive.read_bytes(),types_supplementaires=TYPES_PAPIER)
        ini=deserialiser_valeur(d['session']['initialisation'],types_supplementaires=TYPES_PAPIER)
        self.assertEqual(ini['composition']['initiales']['REFERENCE']['observation'].compte.solde,D(str(C.technique.commun.initial_equity_usd)))
        g=dict(d['session']['checkpoint'].coordinateurs)['REFERENCE'].reprise.gardes
        self.assertEqual(g.base_quotidienne,D(str(C.technique.commun.initial_equity_usd)))
        code,s,e=appeler(['incident','--archive',archive,'--sortie',rapport])
        self.assertEqual(code,0,(s,e));self.assertEqual(json.loads(rapport.read_bytes())['statut'],'IDENTIQUE')
        self.assertFalse(any(n=='order_send' for n,*_ in self.sdk.appels))

    def test_rejeu_gzip_et_rapports_c10_non_valides_sans_sdk(self):
        self.preparer();d,lignes=demande_fixture();demande=self.root/'demande.json';ticks=self.root/'ticks.csv.gz'
        demande.write_bytes(encoder_rejeu(d));ticks.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0))
        archive=self.root/'archive.json';rapport=self.root/'rapport.json';synthese=self.root/'synthese.json'
        code,s,e=appeler(['rejeu','--registre',self.registre,'--demande',demande,'--ticks',ticks,'--archive',archive,'--rapport',rapport])
        self.assertEqual(code,0,(s,e));r=json.loads(rapport.read_bytes())
        self.assertEqual(r['schema'],'xp-dossier-validation-v1');self.assertEqual(r['rapport']['statut'],'NON_VALIDE')
        code,s,e=appeler(['rapports','--registre',self.registre,'--archives',archive,'--sortie',synthese])
        self.assertEqual(code,0,(s,e));self.assertEqual(json.loads(synthese.read_bytes()),r)
        self.assertFalse(self.sdk.appels)
