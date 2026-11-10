"""Import atomique, intégrité, ordre et absence d'invention."""
from dataclasses import replace
import unittest
from robot.outils.rejeu import T,lot_csv
from xpbots.noyau.c1b_instrument import Intervalle
from xpbots.rejeu.c0a_types import ErreurRejeu
from xpbots.rejeu.c1a_ticks import analyser_lignes_ticks


class TestImport(unittest.TestCase):
    def test_lot_canonique_et_conservation_de_provenance(self):
        l,m=lot_csv();h=analyser_lignes_ticks(l,m)
        self.assertEqual(h.manifeste,m);self.assertEqual(len(tuple(h)),1)
        self.assertEqual((h.ticks[0].bid,h.ticks[0].ask),(1.1,1.1001))
        self.assertEqual(h.ticks[0].instant_reception_ms,h.ticks[0].instant_fournisseur_ms)

    def test_empreinte_exacte_y_compris_fins_de_ligne(self):
        l,m=lot_csv()
        for v in (l[:-1],tuple(x.replace('\n','\r\n') for x in l),l+(l[-1],)):
            with self.subTest(v=v),self.assertRaises(ErreurRejeu):analyser_lignes_ticks(v,m)

    def test_fin_invalide_ne_rend_aucun_prefixe(self):
        l,_=lot_csv();l,m=lot_csv(l+('ligne,invalide\n',))
        with self.assertRaises(ErreurRejeu):analyser_lignes_ticks(l,m)

    def test_ordre_milliseconde_et_sequence_sans_tri(self):
        l,_=lot_csv()
        for ligne in (f'EURUSD,EURUSD,{T},0,1.1,1.1001\n',f'EURUSD,EURUSD,{T-1},1,1.1,1.1001\n'):
            valeurs,m=lot_csv(l+(ligne,))
            with self.assertRaises(ErreurRejeu):analyser_lignes_ticks(valeurs,m)
        valeurs,m=lot_csv(l+(f'EURUSD,EURUSD,{T},1,1.2,1.2001\n',))
        self.assertEqual([t.numero for t in analyser_lignes_ticks(valeurs,m)],[0,1])

    def test_sequence_originale_explicitement_declaree(self):
        l,m=lot_csv();l,m=lot_csv((l[0],l[1].replace(',0,',',,')))
        with self.assertRaises(ErreurRejeu):analyser_lignes_ticks(l,m)
        self.assertEqual(analyser_lignes_ticks(l,replace(m,sequence_origine='ORDRE_ORIGINAL')).ticks[0].numero,0)

    def test_formats_symboles_prix_et_temps_refuses(self):
        l,_=lot_csv()
        for s in ('EURUSD,autre,{t},0,1.1,1.1001','EURUSD,EURUSD,{t},0,NaN,1.1001',
                  'EURUSD,EURUSD,{t},0,1.2,1.1','EURUSD,EURUSD,{t},0,0,1.1',
                  'EURUSD,EURUSD,{t},0,1.1000000000000000001,1.2',
                  'EURUSD,EURUSD,+{t},0,1.1,1.2','EURUSD,EURUSD,{t},٠,1.1,1.2'):
            valeurs,m=lot_csv((l[0],s.format(t=T)+'\n'))
            with self.subTest(s=s),self.assertRaises(ErreurRejeu):analyser_lignes_ticks(valeurs,m)

    def test_aucun_tick_dans_un_trou_ou_zone_non_collectee(self):
        l,m=lot_csv()
        for kw in ({'couverture':(),'trous':(m.intervalle,)}, {'couverture':(Intervalle(T+1,T+3600000),)}):
            with self.subTest(kw=kw),self.assertRaises(ErreurRejeu):analyser_lignes_ticks(l,replace(m,**kw))

    def test_borne_fin_exclue(self):
        l,_=lot_csv();l,m=lot_csv((l[0],f'EURUSD,EURUSD,{T+3600000},0,1.1,1.2\n'))
        with self.assertRaises(ErreurRejeu):analyser_lignes_ticks(l,m)
