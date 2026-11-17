"""Checkpoint régulier sans duplication des histoires de stratégies."""
from dataclasses import replace
import unittest
from robot.outils.orchestration import ticks_courts
from robot.outils.pilote_orchestration import duo,piloter
from xpbots.orchestration.c0_contrats import ErreurOrchestration


class TestCheckpointJournal(unittest.TestCase):
    def test_etats_courants_identiques_au_checkpoint_complet_sans_bras(self):
        ticks=ticks_courts();m,ports,_,_,_=duo(ticks);piloter(ticks,m,ports)
        cp=m.exporter_checkpoint_journal();complet=m.exporter_checkpoint();cp.verifier()
        self.assertEqual((cp.signature,cp.instant_ms,cp.numero_entrees,cp.empreinte_journal),
                         (complet.signature,complet.instant_ms,complet.numero_entrees,complet.empreinte_journal))
        self.assertEqual(cp.flux,complet.flux)
        self.assertEqual(cp.coordinateurs,tuple((b.nom,b.coordinateur) for b in complet.bras))
        self.assertEqual(cp.fondamental,complet.fondamental)
        self.assertEqual(cp.ia,('xp-verification-ia-v1',complet.ia.dernier_ms,None,()))
        self.assertFalse(hasattr(cp,'bras'));self.assertFalse(hasattr(cp,'entrees'))

    def test_sceau_compteur_bras_et_instant_alteres_refuses(self):
        m,_,_,_,_=duo(ticks_courts());cp=m.exporter_checkpoint_journal()
        for mauvais in (replace(cp,instant_ms=cp.instant_ms+1),replace(cp,numero_entrees=True),
                        replace(cp,coordinateurs=()),replace(cp,coordinateurs=(cp.coordinateurs[0],)*2),
                        replace(cp,ia=m.exporter_checkpoint().ia)):
            with self.subTest(mauvais=mauvais),self.assertRaises(ErreurOrchestration):mauvais.verifier()

    def test_receptions_anciennes_ne_sont_pas_repropagees_dans_le_checkpoint_regulier(self):
        from robot.outils.checkpoints_controles import controles_repetes
        from xpbots.orchestration.c0_contrats import EntreeMoteur,ReceptionExterne
        m,ports,_=controles_repetes();cp=m.exporter_checkpoint_journal();complet=m.exporter_checkpoint()
        self.assertGreater(len(complet.fondamental.permissions.historique),200)
        self.assertGreater(len(complet.fondamental.calendrier.versions),200)
        self.assertGreater(len(complet.ia.scelles),200)
        self.assertEqual(len(cp.fondamental[3]),1);self.assertEqual(len(cp.fondamental[4]),1)
        self.assertEqual(cp.fondamental[6][0],300)
        self.assertEqual(len(cp.ia[3]),1)
        self.assertLess(len(repr(cp)),len(repr(complet))//4)
        # L'interruption ne fait perdre ni la dernière permission ni le curseur d'identité.
        t=cp.instant_ms+1
        for p in ports.values():p.avancer_au(t)
        m.traiter(EntreeMoteur(t,301,receptions=(ReceptionExterne('INTERRUPTION',b'','EURUSD'),)))
        suivant=m.exporter_checkpoint_journal()
        self.assertNotEqual(cp.fondamental[3],suivant.fondamental[3])
        self.assertEqual(cp.fondamental[4],suivant.fondamental[4])
