"""Catégorie 1 : registre, cadence, interruptions et reprise C05."""
from dataclasses import FrozenInstanceError, replace
import unittest

from robot.outils.fondamental import T, commun, message, octets
from xpbots.fondamental.c0_types import ErreurFondamental, millisecondes
from xpbots.fondamental.c2_etat_permissions import (EtatPermissions, RegistrePermissions,
    SuiviHeartbeat)
from xpbots.noyau.c0a_temps import instant_vers_iso


class TestEtatPermissions(unittest.TestCase):
    def setUp(self):
        self.r = RegistrePermissions(commun())
        self.p = octets(message())
        self.h = millisecondes(commun().fundamental_expected_heartbeat_seconds)
        self.fin = T + millisecondes(commun().fundamental_max_validity_seconds)

    def recevoir(self, **changements):
        return self.r.recevoir('EURUSD', octets(message(**changements)), T+200)

    def test_absence_et_reception_locale_distincte(self):
        self.assertEqual(self.r.consulter('EURUSD',T).detail,'ABSENTE')
        p=self.recevoir().permission
        self.assertEqual((p.reception_ms,p.message.known_at_ms),(T+200,T+100))
        self.assertEqual(self.r.consulter('EURUSD',T+199).detail,'ABSENTE')
        self.assertIsNone(self.r.consulter('EURUSD',T+200).detail)
        self.assertEqual(RegistrePermissions(commun(),self.r.etat).etat,self.r.etat)

    def test_relecture_ignoree_sans_renouvellement_meme_perimee(self):
        self.recevoir()
        etat=self.r.etat
        self.assertTrue(self.r.recevoir('EURUSD',self.p,self.fin+1).ignoree)
        self.assertEqual(self.r.etat,etat)
        self.assertEqual(self.r.consulter('EURUSD',self.fin).detail,'PERIMEE')

    def test_sequence_inferieure_et_reecriture_sont_rejetees(self):
        self.recevoir(sequence=3)
        etat=self.r.etat
        for changements in ({'sequence':2},{'sequence':3,'direction':'SHORT_ONLY'}):
            self.assertEqual(self.recevoir(**changements).raison,'SEQUENCE_NON_CROISSANTE')
            self.assertEqual(self.r.etat,etat)
        self.assertTrue(self.recevoir(sequence=5).acceptee)

    def test_invalide_ne_detruit_pas_derniere_permission(self):
        self.recevoir()
        etat=self.r.etat
        for p in (b'{}',b'{"a":NaN}',octets(message(sequence=2,risk_state='INCONNU'))):
            self.assertFalse(self.r.recevoir('EURUSD',p,T+300).acceptee)
            self.assertEqual(self.r.etat,etat)
        self.assertIsNone(self.r.consulter('EURUSD',T+300).detail)

    def test_interruption_est_explicite_et_seule_nouvelle_sequence_resout(self):
        self.recevoir()
        self.assertTrue(self.r.interrompre('EURUSD',T+300))
        self.assertFalse(self.r.interrompre('EURUSD',T+301))
        self.assertTrue(self.r.recevoir('EURUSD',self.p,T+400).ignoree)
        self.assertEqual(self.r.consulter('EURUSD',T+500).detail,'INTERRUPTION')
        self.assertTrue(self.r.recevoir('EURUSD',octets(message(sequence=2)),T+500).acceptee)
        self.assertIsNone(self.r.consulter('EURUSD',T+500).detail)
        self.assertEqual(self.r.consulter('EURUSD',T+499).detail,'INTERRUPTION')

    def test_heartbeat_exact_ne_retire_pas_permission(self):
        self.recevoir()
        self.assertEqual(self.r.prochaine_echeance_ms(T+200),T+self.h)
        self.assertEqual(self.r.avancer(T+self.h-1),())
        e,=self.r.avancer(T+self.h)
        self.assertEqual((e.nature,e.echeance_ms,e.nombre),('HEARTBEAT_MANQUE',T+self.h,1))
        self.assertEqual(self.r.avancer(T+self.h),())
        self.assertIsNone(self.r.consulter('EURUSD',T+self.h).detail)

    def test_nouveau_heartbeat_a_echeance_avant_avancer(self):
        self.recevoir()
        p=message(sequence=2,issued_at_utc=instant_vers_iso(T+self.h),
            known_at_utc=instant_vers_iso(T+self.h),valid_from_utc=instant_vers_iso(T+self.h),
            valid_until_utc=instant_vers_iso(self.fin+self.h))
        self.assertTrue(self.r.recevoir('EURUSD',octets(p),T+self.h).acceptee)
        self.assertEqual(self.r.avancer(T+self.h),())
        self.assertEqual(self.r.prochaine_echeance_ms(T+self.h),T+self.h*2)

    def test_saut_de_temps_regroupe_et_expiration_exclusive_unique(self):
        self.recevoir()
        e=self.r.avancer(self.fin)
        self.assertEqual([v.nature for v in e],['HEARTBEAT_MANQUE','PERMISSION_EXPIREE'])
        self.assertEqual(e[0].nombre,(self.fin-1-T)//self.h)
        self.assertEqual(e[1].echeance_ms,self.fin)
        self.assertEqual(self.r.avancer(self.fin+1),())
        self.assertIsNone(self.r.prochaine_echeance_ms(self.fin+1))

    def test_reprise_curseurs_et_alertes_consommees(self):
        self.recevoir()
        self.r.avancer(T+self.h)
        etat=self.r.etat
        repris=RegistrePermissions(commun(),etat)
        self.assertEqual(repris.avancer(T+self.h),())
        self.assertEqual(repris.avancer(self.fin),self.r.avancer(self.fin))
        self.assertEqual(repris.etat,self.r.etat)
        with self.assertRaises(FrozenInstanceError): etat.dernier_ms=0

    def test_reprise_refuse_histoire_future_sequence_et_curseur_forges(self):
        self.recevoir()
        e=self.r.etat
        c=e.curseurs[0]
        faux=(replace(e,dernier_ms=T),replace(e,historique=e.historique*2),
            replace(e,curseurs=()),replace(e,curseurs=(replace(c,sequence=2),)),
            replace(e,curseurs=(replace(c,prochain_ms=c.prochain_ms+self.h),)),
            replace(e,curseurs=(replace(c,expiration_signalee=True),)))
        for etat in faux:
            with self.subTest(etat=etat),self.assertRaises(ErreurFondamental):
                RegistrePermissions(commun(),etat)

    def test_temps_et_types_invalides(self):
        self.recevoir()
        self.r.avancer(T+400)
        for appel in (lambda:self.r.avancer(T+399),lambda:self.r.recevoir('EURUSD',self.p,T+399),
            lambda:self.r.interrompre('EURUSD',T+399),lambda:self.r.consulter('INCONNU',T),
            lambda:EtatPermissions(None),lambda:SuiviHeartbeat('EURUSD',True,T)):
            with self.assertRaises(ErreurFondamental):appel()

    def test_expiration_autre_symbole_non_perdue_par_reception(self):
        self.recevoir()
        p=message('GBPUSD',issued_at_utc=instant_vers_iso(self.fin),
            known_at_utc=instant_vers_iso(self.fin),valid_from_utc=instant_vers_iso(self.fin),
            valid_until_utc=instant_vers_iso(self.fin+self.h))
        self.r.recevoir('GBPUSD',octets(p),self.fin)
        self.assertTrue(any(e.nature=='PERMISSION_EXPIREE' and e.symbole=='EURUSD'
            for e in self.r.avancer(self.fin)))
