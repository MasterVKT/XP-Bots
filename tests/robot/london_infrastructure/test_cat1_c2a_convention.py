"""La preuve S01 distingue explicitement le flux SDK des exports serveur D12."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from robot.outils.qualification_mt5 import T,preuve_qualification,frontiere
from robot.outils.faux_mt5 import FauxMT5
from xpbots.infra.c0a_types import ErreurInfra


class TestConventionTicksQualifiee(unittest.TestCase):
    def test_convention_absente_inconnue_ou_non_textuelle_refuse_avant_utilisation(self):
        with TemporaryDirectory() as racine:
            sdk=FauxMT5(Path(racine).resolve(),instant_ms=T)
            for v in ('ABSENTE','INCONNUE',None,False):
                q=preuve_qualification(sdk)
                if v=='ABSENTE':q.pop('convention_ticks')
                else:q['convention_ticks']=v
                with self.subTest(v=v),self.assertRaises(ErreurInfra):frontiere(racine,sdk=sdk,qualification=q)
            self.assertFalse(any(n in ('copy_ticks_from','order_send') for n,*_ in sdk.appels))

    def test_choix_explicite_copie_et_valide_aux_seuls_instants_qualifies(self):
        with TemporaryDirectory() as racine:
            sdk=FauxMT5(Path(racine).resolve(),instant_ms=T)
            for mode in ('UTC','SERVEUR_S01'):
                q=preuve_qualification(sdk);q['convention_ticks']=mode
                _,session,specs=frontiere(racine,sdk=sdk,qualification=q)
                try:
                    q['convention_ticks']='INCONNUE'
                    self.assertEqual(specs.convention_ticks(T),mode)
                    with self.assertRaises(ErreurInfra):specs.convention_ticks(q['known_at_utc_ms']-1)
                    with self.assertRaises(ErreurInfra):specs.convention_ticks(q['valid_until_utc_ms'])
                finally:session.fermer()
