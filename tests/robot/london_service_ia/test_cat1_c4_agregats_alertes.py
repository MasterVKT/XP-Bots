"""Fichiers réels A11, validation amont réelle et alertes sur stderr local."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import tempfile
import unittest
from unittest.mock import patch
from xpbots.infra.c0d_journal import ecrire_atomique
from xpbots.service_ia.c0_types import canonique,decoder,ErreurService
from xpbots.service_ia.c4_service import ServiceIA
from .support import ressources,Horloge


class EntreesSortiesA11(unittest.TestCase):
    def ouvrir(self,p,h):
        return ServiceIA(ressources(),p/'ia.db',p/'context.json',horloge=h,agregats=p/'agregats.json')

    def fichier(self,p,h,**kw):
        # La fixture amont est un agrégat anonymisé calculé par du code.
        r=ressources();zone=ZoneInfo(r.configuration.technique.commun.session_timezone)
        m=dict(item_id='metric-1',period=datetime.fromtimestamp(h.t/1000,timezone.utc).astimezone(zone).date().isoformat(),
            strategy=r.configuration.technique.commun.simultaneous_strategy_priority[0],
            symbol=r.configuration.technique.commun.universe_priority[0],arm='REFERENCE',net_pnl='-1.25',
            trade_count=1,equity_drawdown='0.02',ai_cost_usd='0',known_at_ms=h.t,
            dimensions=dict(range_width_atr_h1='1.25',new_signal_after_veto=False),
            refusals=dict(AI_CONTEXT_VETO=1),data_gaps=0)
        v=dict(schema='xp-code-aggregates-v1',metriques=[m],decisions=[])
        v.update(kw);ecrire_atomique(p/'agregats.json',canonique(v));return v

    def test_import_idempotent_durable_et_absence_de_donnees_inventees(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stderr(StringIO()):
            p=Path(tmp);h=Horloge();v=self.fichier(p,h)
            with self.ouvrir(p,h) as s:
                s.collecter();s.collecter()
                self.assertEqual(s.depot.transaction(lambda t:list(t['experiment_metrics'].values())),v['metriques'])
                self.assertEqual(s.depot.transaction(lambda t:len(t['candidate_decisions'])),0)
            with self.ouvrir(p,h) as s:
                s.collecter()
                self.assertEqual(s.depot.transaction(lambda t:len(t['experiment_metrics'])),1)

    def test_futur_ou_reecriture_refuses_atomiquement_sans_bloquer_rss(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stderr(StringIO()):
            p=Path(tmp);h=Horloge();v=self.fichier(p,h)
            with self.ouvrir(p,h) as s:
                s.collecter()
                autre=dict(v['metriques'][0],item_id='nouveau')
                faux=dict(v['metriques'][0],net_pnl='999')
                self.fichier(p,h,metriques=[autre,faux]);resultat=s.collecter()
                self.assertTrue(resultat)  # Les trois sources ont encore été visitées.
                self.assertEqual(s.depot.transaction(lambda t:list(t['experiment_metrics'].values())),v['metriques'])
                self.fichier(p,h,metriques=[dict(autre,known_at_ms=h.t+1)])
                s.collecter();self.assertEqual(s.depot.transaction(lambda t:len(t['experiment_metrics'])),1)
                self.assertEqual(s.depot.transaction(lambda t:t['alerts']['agregats']['code']),'AGREGATS_INDISPONIBLES')

    def test_fichier_malforme_et_secret_synthetique_jamais_affiches(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);h=Horloge();(p/'agregats.json').write_text('SECRET_FABRIQUE',encoding='utf-8')
            sortie=StringIO()
            with redirect_stderr(sortie),self.ouvrir(p,h) as s:
                s.collecter();self.assertTrue(s.heartbeat().publie)
            lignes=[decoder(l.encode()) for l in sortie.getvalue().splitlines()]
            self.assertIn('AGREGATS_INDISPONIBLES',{v['code'] for v in lignes})
            self.assertNotIn('SECRET_FABRIQUE',sortie.getvalue());self.assertNotIn(str(p),sortie.getvalue())

    def test_alertes_affichees_une_fois_et_publication_en_panne_signalee(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);h=Horloge();self.fichier(p,h);sortie=StringIO()
            with redirect_stderr(sortie),self.ouvrir(p,h) as s:
                s.heartbeat();initial=sortie.getvalue();self.assertTrue(initial)
                s.heartbeat();self.assertEqual(sortie.getvalue(),initial)
                # Seule la primitive de remplacement du système de fichiers est doublée.
                with patch('os.replace',side_effect=OSError('ERREUR_OS_FABRIQUEE')):
                    self.assertFalse(s.heartbeat().publie)
                self.assertIn('PUBLICATION_SNAPSHOT_INDISPONIBLE',sortie.getvalue())
                self.assertNotIn('ERREUR_OS_FABRIQUEE',sortie.getvalue())
            apres=StringIO()
            with redirect_stderr(apres),self.ouvrir(p,h) as s:s.heartbeat()
            self.assertEqual(apres.getvalue(),'')

    def test_env_et_sorties_refusees_comme_entree(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for entree in (p/'.env',p/'.env.local',p/'ia.db',p/'context.json',p/'service_identity.json'):
                with self.subTest(entree=entree.name),self.assertRaises(ErreurService):
                    ServiceIA(ressources(),p/'ia.db',p/'context.json',agregats=entree)
