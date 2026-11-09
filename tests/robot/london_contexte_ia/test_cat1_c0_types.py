"""Catégorie 1, couche 0 : représentation, paramètres réels et valeurs immuables A10."""
from dataclasses import FrozenInstanceError,replace
from decimal import Decimal
import unittest

from robot.outils.configuration import configuration_figee
from robot.outils.contexte_ia import T,parametres,snapshot,octets
from xpbots.contexte_ia.c0_types import (ErreurContexte,PolitiqueVeto,SnapshotIA,SnapshotRecu,Veto,VetoConnu,
    canonique,charger_parametres,decoder_objet,empreinte,en_ms,entier,instant,sha256_hex,texte,utc)


def veto(**changements):
    return replace(Veto('v1',('EURUSD',),T,T+60000,'i1','FOURNISSEUR_TEST'),**changements)


def valeur_snapshot(**changements):
    return replace(SnapshotIA(1,T,parametres().empreinte_integration,(veto(),),'a'*64,b'{}'),**changements)


class TestTypesContexte(unittest.TestCase):
    def test_parametres_charges_sans_seuil_recopie(self):
        c=configuration_figee();p=charger_parametres(c)
        self.assertEqual(p.max_octets,c.ia.parametres['snapshot_max_bytes'])
        self.assertEqual(p.age_max_ms,en_ms(c.ia.parametres['snapshot_max_age_seconds']))
        self.assertEqual(p.empreinte_integration,c.ia.empreinte_canonique)
        self.assertEqual(p.symboles,c.technique.commun.universe_priority)
        self.assertEqual(p.fournisseurs,{v['id'] for v in c.ia.parametres['providers']})
        with self.assertRaises(ErreurContexte):charger_parametres({})

    def test_json_canonique_utf8_exact(self):
        self.assertEqual(canonique({'z':1,'a':'é'}),'{"a":"é","z":1}'.encode('utf-8'))
        self.assertEqual(empreinte({'a':1,'b':2}),empreinte({'b':2,'a':1}))
        self.assertEqual(decoder_objet(octets(snapshot())),snapshot())
        for v in (float('nan'),float('inf'),{'x':Decimal('1')},{'x':'\ud800'}):
            with self.subTest(v=repr(v)),self.assertRaises(ErreurContexte):canonique(v)

    def test_json_duplique_non_fini_tronque_et_utf8_refuses(self):
        for b in (b'{"a":1,"a":2}',b'{"x":{"a":1,"a":2}}',b'{"x":NaN}',b'{"x":1e999}',
            b'[]',b'null',b'{} {}',b'\xff',b'\xef\xbb\xbf{}','{}'):
            with self.subTest(b=b),self.assertRaises(ErreurContexte):decoder_objet(b)

    def test_scalaires_stricts(self):
        self.assertEqual(en_ms(3),3000)
        for v in (True,-1,1.0,'1'):
            with self.assertRaises(ErreurContexte):entier(v)
            with self.assertRaises(ErreurContexte):instant(v)
        for v in ('','  ',None,'\ud800'):
            with self.assertRaises(ErreurContexte):texte(v)
        for v in ('a'*63,'G'*64,None):
            with self.assertRaises(ErreurContexte):sha256_hex(v)

    def test_utc_noyau_et_precision(self):
        self.assertEqual(utc('2026-11-09T08:00:00Z'),T)
        self.assertEqual(utc('2026-11-09T08:00:00.001+00:00'),T+1)
        for v in ('2026-11-09T08:00:00','2026-11-09T08:00:00+01:00','2026-11-09T08:00:00.000001Z'):
            with self.assertRaises(ErreurContexte):utc(v)

    def test_veto_immuable_et_intervalle_positif(self):
        liste=['EURUSD'];v=veto(symboles=liste);liste.append('GBPUSD')
        self.assertEqual(v.symboles,('EURUSD',))
        with self.assertRaises(FrozenInstanceError):v.item_id='autre'
        for c in ({'event_id':'id avec espace'},{'symboles':[]},{'symboles':['EURUSD','EURUSD']},
            {'valid_until_ms':T},{'valid_from_ms':True},{'reason_code':'INCONNU'},{'item_id':''}):
            with self.subTest(c=c),self.assertRaises(ErreurContexte):veto(**c)

    def test_snapshot_conserve_octets_et_types(self):
        s=valeur_snapshot();self.assertEqual(s.octets,b'{}')
        with self.assertRaises(FrozenInstanceError):s.sequence=2
        for c in ({'sequence':True},{'sequence':0},{'vetos':[{}]},{'empreinte_payload':'non'},{'octets':'{}'}):
            with self.assertRaises(ErreurContexte):valeur_snapshot(**c)

    def test_preuve_et_reception_distincte(self):
        s=valeur_snapshot();r=SnapshotRecu(s,T+100)
        v=VetoConnu(s.vetos[0],T+100,r)
        self.assertEqual(v.connu_ms-v.veto.valid_from_ms,100)
        for appel in (lambda:SnapshotRecu(s,T-1),lambda:VetoConnu(v.veto,T,r),
            lambda:VetoConnu(veto(event_id='autre'),T+100,r)):
            with self.assertRaises(ErreurContexte):appel()

    def test_politique_trois_booleens(self):
        self.assertTrue(PolitiqueVeto(True).bras_ia)
        for valeurs in ((1,False,False),(True,'false',False),(True,False,None)):
            with self.assertRaises(ErreurContexte):PolitiqueVeto(*valeurs)

    def test_collections_et_parametres_invalides(self):
        p=parametres()
        for c in ({'max_octets':True},{'age_max_ms':-1},{'fournisseurs':[]},
            {'symboles':['EURUSD','EURUSD']},{'symboles':[[]]},{'fournisseurs':[{}]},
            {'validation_financiere_requise':1}):
            with self.assertRaises(ErreurContexte):replace(p,**c)
        with self.assertRaises(ErreurContexte):veto(symboles='EURUSD')
