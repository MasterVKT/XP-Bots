"""Catégorie 1, couche 1a : chaque condition C05 et le schéma D-11 exact."""
import unittest
from robot.outils.fondamental import T, commun, message, octets
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.fondamental.c0_types import millisecondes
from xpbots.fondamental.c1a_message import ErreurPermission, decoder_message


class TestMessagePermission(unittest.TestCase):
    def decoder(self, p, reception=T+200, maintenant=T+200, symbole='EURUSD'):
        return decoder_message(octets(p), symbole, reception, maintenant, commun())

    def test_schema_neutre_explicitement_valide(self):
        m = self.decoder(message())
        self.assertEqual((m.symbole, m.sequence, m.direction.value, m.risk_state.value), ('EURUSD', 1, 'ANY', 'ALLOW'))
        self.assertEqual((m.issued_at_ms, m.known_at_ms), (T, T+100))

    def test_toutes_directions_et_risques_connus(self):
        for d in ('ANY', 'LONG_ONLY', 'SHORT_ONLY'):
            for r in ('ALLOW', 'NO_NEW', 'FLATTEN'):
                with self.subTest(d=d,r=r): self.assertEqual(self.decoder(message(direction=d,risk_state=r)).risk_state.value,r)

    def test_cles_exactes_types_et_identifiants(self):
        fautifs = [message(**{k:v}) for k,v in (('schema','v2'),('sequence',True),('sequence',0),('sequence',1.0),
            ('direction','NEUTRAL'),('risk_state','OPEN'),('model_version',''),('input_snapshot_id','  '),
            ('canonical_symbol','GBPUSD'),('issued_at_utc',0))]
        plus = message();plus['surplus']=None;fautifs.append(plus)
        for cle in message():
            p=message();del p[cle];fautifs.append(p)
        for p in fautifs:
            with self.subTest(p=p),self.assertRaises(ErreurPermission) as e:self.decoder(p)
            self.assertEqual(e.exception.detail,'INVALIDE')

    def test_format_utc_exact(self):
        for texte in ('2026-11-09T08:00:00Z','2026-11-09T08:00:00.000+00:00','2026-11-09 08:00:00.000Z',
            '2026-13-09T08:00:00.000Z','2026-11-09T08:00:00.0000Z','2026-11-09T08:00:00.000'):
            with self.subTest(t=texte),self.assertRaises(ErreurPermission): self.decoder(message(issued_at_utc=texte))

    def test_ordre_des_heures_et_reception_locale(self):
        cas=[(message(known_at_utc=instant_vers_iso(T-1)),T+200,T+200),
             (message(valid_from_utc=instant_vers_iso(T-1)),T+200,T+200),
             (message(known_at_utc=instant_vers_iso(T+201)),T+200,T+200),
             (message(valid_from_utc=instant_vers_iso(T+201)),T+200,T+200),
             (message(),T+99,T+200),(message(),T+201,T+200)]
        for p,reception,maintenant in cas:
            with self.subTest(p=p,r=reception),self.assertRaises(ErreurPermission):self.decoder(p,reception,maintenant)
        self.decoder(message(),T+100,T+100)

    def test_duree_maximale_inclusive_et_fin_exclusive(self):
        borne=T+millisecondes(commun().fundamental_max_validity_seconds)
        self.decoder(message(),T+100,borne-1)
        with self.assertRaises(ErreurPermission) as e:self.decoder(message(),T+100,borne)
        self.assertEqual(e.exception.detail,'PERIMEE')
        for fin in (T,T-1,borne+1):
            with self.subTest(fin=fin),self.assertRaises(ErreurPermission) as e:
                self.decoder(message(valid_until_utc=instant_vers_iso(fin)))
            self.assertEqual(e.exception.detail,'INVALIDE')

    def test_json_invalide_doublon_et_non_fini(self):
        for b in (b'[]',b'{}',b'{"sequence":1,"sequence":2}',b'{"sequence":NaN}',b'\xff',b'{"tronque":'):
            with self.subTest(b=b),self.assertRaises(ErreurPermission): decoder_message(b,'EURUSD',T,T,commun())
