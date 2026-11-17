"""Contrat de lecture native, activé seulement sur le poste qualifié 13.1."""
from datetime import datetime,timedelta,timezone
import unittest
from robot.outils.contrats_mt5 import MT5_ACTIF,RAISON,sdk_contrat,registre_contrat
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c0b_horloge import HorlogeSysteme
from xpbots.infra.c1_session import SessionMT5
from xpbots.infra.c2b_flux import FluxMT5


class TestContratFluxPoste(unittest.TestCase):
    @unittest.skipUnless(MT5_ACTIF,RAISON)
    def test_occurrences_recentes_concordent_au_tableau_natif(self):
        r=registre_contrat();i=r['ingenierie'];table=TableHeureServeur.depuis_document(r['table_heure_serveur'])
        with sdk_contrat() as sdk:
            session=SessionMT5(sdk,'DEMO')
            try:
                session.attacher();t=HorlogeSysteme().utc_ms();depart=t-i['fenetre_contrat_ticks_ms']
                source=FluxMT5(session,table,r['liaisons'],{s:depart for s in r['liaisons']},
                    taille_lot=i['taille_lot_ticks'],max_ticks_lot=i['max_ticks_lot'],
                    historique_complet={s:r['qualification_mt5']['symboles'][b]['historique_ticks_complet'] for s,b in r['liaisons'].items()},
                    convention_ticks=r['qualification_mt5']['convention_ticks'])
                lot=source.lire(t)
                self.assertTrue(lot.ticks,'13.1 exige un intervalle recent contenant des ticks')
                for s,b in r['liaisons'].items():
                    utc=r['qualification_mt5']['convention_ticks']=='UTC'
                    raw=depart if utc else table.serveur_de_utc(depart)
                    seconde=timedelta(seconds=1)//timedelta(milliseconds=1)
                    date=datetime.fromtimestamp(0,timezone.utc)+timedelta(milliseconds=raw//seconde*seconde)
                    natifs=sdk.copy_ticks_from(b,date,i['max_ticks_lot'],sdk.COPY_TICKS_ALL)
                    self.assertIsNotNone(natifs)
                    natifs=[v for v in natifs if int(v['time_msc'])>=raw]
                    normalises=[v for v in lot.ticks if v.symbole==s]
                    self.assertTrue(normalises);self.assertGreaterEqual(len(natifs),len(normalises))
                    for a,n in zip(normalises,natifs):
                        self.assertEqual((a.instant_fournisseur_ms,a.bid,a.ask,a.drapeaux),
                            (int(n['time_msc']) if utc else table.utc_de_serveur(int(n['time_msc'])),
                             float(n['bid']),float(n['ask']),int(n['flags'])))
            finally:session.fermer()
