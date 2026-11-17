"""Journal C09 et reprise du vrai moteur : aucun backend pendant le rejeu."""
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date
from decimal import Decimal as D
import unittest

from robot.points_entree.test_cat1_c1b_session_durable import composition,tick_suivant
from robot.outils.orchestration import C,ticks_courts,composer_bras
from xpbots.app.c1b_session_durable import SessionDurable
from xpbots.infra.c0c_sqlite import DepotSQLite
from xpbots.infra.c0d_journal import JournalFichiers
from xpbots.noyau.c2_journal import serialiser
from xpbots.noyau.c1a_marche import Tick
from xpbots.orchestration.c2_moteur import MoteurDecision
from xpbots.orchestration.c0_contrats import MiseAJourBras
from xpbots.orchestration.c3_codec import serialiser_valeur


class TestJonctionSessionDurable(unittest.TestCase):
    def test_marqueur_reprise_projete_avec_entrees_et_c09_inchanges(self):
        import json
        from xpbots.orchestration.c3_codec import deserialiser_valeur
        with TemporaryDirectory() as root:
            with DepotSQLite(Path(root)/'etat.sqlite',{'fixture':'REPRISE'}) as db:
                j=JournalFichiers(root,'essai_orchestration');ini=serialiser_valeur({'fixture':'REPRISE'})
                m,ports=composition();s=SessionDurable(db,j,ini)
                sortie=tick_suivant(m,ports,ticks_courts()[0]);s.persister(m,sortie)
                cp=m.exporter_checkpoint_journal();avant=tuple(b for _,_,ds,_ in db.evenements() for b in ds)
                SessionDurable(db,j,ini,reprise=cp).persister(m)
                charge=SessionDurable(db,j,ini).charger()
                self.assertEqual(charge['reprises'],(cp,))
                self.assertEqual(tuple(b for _,_,ds,_ in db.evenements() for b in ds),avant)
                enveloppes=[json.loads(b) for b in db.entrees()]
                marqueur=next(e for e in enveloppes if e['type_evenement']=='REPRISE_MOTEUR')
                contenu=json.dumps(marqueur['contenu'],sort_keys=True,separators=(',',':')).encode()
                self.assertEqual(deserialiser_valeur(contenu),cp)
                physique=b''.join(f.read_bytes() for f in sorted(j.dossier.glob('entrees_*.jsonl')))
                self.assertEqual(physique,b''.join(b+b'\n' for b in db.entrees()))

    def test_vraie_preparation_london_confirmee_par_le_commit(self):
        from robot.outils.rejeu import experience_london
        from xpbots.rejeu.squelette import analyser_lignes_ticks,ContratPapier
        from xpbots.app.rejeu_squelette import composer_rejeu_papier
        from xpbots.execution.c4_cycle import NatureCommande
        _,source,_,_=experience_london(date(2026,11,9))
        ticks=tuple(analyser_lignes_ticks(source.lire()))
        facade,p,_=composer_rejeu_papier(C,ticks,{'EURUSD':D('.00001')},
            {'EURUSD':ContratPapier(D(1000),D('.1'),D(1),D('.1'))},
            deploiement='FIXTURE_DURABLE',scenario='TECHNICAL_CONTROL_NEUTRAL')
        m=facade.moteur;sortie=None
        for tick in ticks:
            reponses=p.sur_tick(tick)
            sortie=m.traiter_ticks((p.tick_decision(tick),),mises_a_jour=(('REFERENCE',
                MiseAJourBras(reponses=reponses,observation=p.observation(),base_utc=p.base_utc())),))
            if any(s.lot is not None and s.lot.preparations for _,s in sortie.sorties):break
        else:self.fail('La journee London doit produire une preparation reelle')
        with TemporaryDirectory() as root:
            with DepotSQLite(Path(root)/'etat.sqlite',{'fixture':'PREPARATION_REELLE'}) as db:
                j=JournalFichiers(root,'FIXTURE_DURABLE')
                initialisation=serialiser_valeur({'initialisation':m.initialisation_calculs})
                s=SessionDurable(db,j,initialisation)
                r=s.persister(m,sortie)
                # Régression de la photographie après les milliers de bougies réelles.
                complet=serialiser_valeur(m.exporter_checkpoint())
                leger=serialiser_valeur(s.charger()['checkpoint'])
                self.assertGreater(len(m.entrees),1000)
                self.assertLess(len(leger),len(complet)//4)
                self.assertNotIn(b'TraceStrategie',leger)
                self.assertEqual(s.charger()['checkpoint'],m.exporter_checkpoint_journal())
                self.assertEqual(db.dernier_numero,r.numero)
                self.assertTrue(r.projection_reussie)
                self.assertEqual(len(r.preuves),1)
                suite=m.confirmer_persistance(dict(r.preuves),sortie.instant_ms)
                self.assertEqual(sum(c.nature is NatureCommande.ENTREE for _,b in suite.sorties for c in b.commandes),1)
                # Un gap natif synthétique déclenche ensuite le vrai arrêt global.
                commandes=tuple(c for _,b in suite.sorties for c in b.commandes)
                ack=p.soumettre(commandes);t=sortie.instant_ms
                m.traiter_evenement(t,mises_a_jour=(('REFERENCE',MiseAJourBras(reponses=ack)),))
                for delta,bid,ask in ((250,1.1003,1.1004),(251,.1,.1001)):
                    q=Tick(tick.symbole,tick.symbole_courtier,t+delta,t+delta,tick.numero+delta,bid,ask)
                    reponses=p.sur_tick(q)
                    sortie=m.traiter_ticks((p.tick_decision(q),),mises_a_jour=(('REFERENCE',
                        MiseAJourBras(reponses=reponses,observation=p.observation(),base_utc=p.base_utc())),))
                    p.soumettre(tuple(c for _,b in sortie.sorties for c in b.commandes))
                self.assertTrue(m.exporter_checkpoint().bras[0].coordinateur.reprise.gardes.arret_global)
                s.persister(m,sortie)
                self.assertTrue(any(nature=='GLOBAL' and actif for _,nature,actif,_,_ in db.arrets()))
                restaure=SessionDurable(db,j,initialisation).charger()
                self.assertTrue(dict(restaure['checkpoint'].coordinateurs)['REFERENCE'].reprise.gardes.arret_global)

    def test_journal_c09_projete_identique_aux_sorties_et_reprise_des_entrees(self):
        with TemporaryDirectory() as root:
            with DepotSQLite(Path(root)/'etat.sqlite',{'fixture':'C09'}) as db:
                j=JournalFichiers(root,'essai_orchestration')
                s=SessionDurable(db,j,serialiser_valeur({'fixture':'C09'}))
                m,ports=composition();attendus=[]
                for tick in ticks_courts()[:3]:
                    sortie=tick_suivant(m,ports,tick);attendus.extend(sortie.enregistrements)
                    self.assertTrue(s.persister(m,sortie).projection_reussie)
                recu=s.charger()
                b,p,h,c=composer_bras()
                reprise=MoteurDecision(C,(b,),h,c,scenario_fondamental='TECHNICAL_CONTROL_NEUTRAL')
                # Interdire le seul backend de calcul : les appels archivés suffisent.
                for nom in ('specifications','etat_compte','profit','marge','controler','frais_aller_retour','frais_sortie'):
                    setattr(p,nom,lambda *a,**k:(_ for _ in ()).throw(AssertionError('BACKEND_INTERDIT')))
                rejoues=[]
                for entree in recu['entrees']:rejoues.extend(reprise.rejouer(entree).enregistrements)
                self.assertEqual(tuple(serialiser(e) for e in rejoues),tuple(serialiser(e) for e in attendus))
                self.assertEqual(reprise.exporter_checkpoint(),m.exporter_checkpoint())
                physique=b''.join(p.read_bytes() for p in sorted(j.dossier.glob('decisions_*.jsonl')))
                self.assertEqual(physique,b''.join(serialiser(e).encode()+b'\n' for e in attendus))

    def test_projection_des_deux_bras_dans_le_journal_du_deploiement(self):
        with TemporaryDirectory() as root:
            with DepotSQLite(Path(root)/'etat.sqlite',{'fixture':'PAPER_AB'}) as db:
                j=JournalFichiers(root,'essai_orchestration')
                s=SessionDurable(db,j,serialiser_valeur({'fixture':'PAPER_AB'}))
                m,ports=composition(ab=True);vus=set()
                for tick in ticks_courts()[:2]:
                    sortie=tick_suivant(m,ports,tick)
                    vus.update(e.enveloppe.bras for e in sortie.enregistrements)
                    r=s.persister(m,sortie)
                    self.assertTrue(r.projection_reussie,'Les enveloppes des bras appartiennent au deploiement racine')
                self.assertEqual(vus,{'REFERENCE','IA'})
                self.assertEqual(len(s.charger()['checkpoint'].coordinateurs),2)
