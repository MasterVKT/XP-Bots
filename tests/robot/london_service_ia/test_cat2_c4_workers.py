"""Trois vrais threads ; seule l'horloge externe pilote les échéances simulées."""
import tempfile
import threading
import unittest
from .support import document
from .support_service import composer


class HorlogeCadence:
    def __init__(self):self.t=document().collecte_ms;self.condition=threading.Condition()
    def maintenant_ms(self):
        with self.condition:return self.t
    def avancer(self,ms):
        with self.condition:self.t+=ms;self.condition.notify_all()
    def attendre(self,s):self.avancer(round(s*1000))
    def attendre_arret(self,stop,s):
        with self.condition:
            fin=self.t+round(s*1000)
            while self.t<fin and not stop.is_set():self.condition.wait(.01)


def attendre_condition(cond):
    for _ in range(300):
        if cond():return True
        threading.Event().wait(.01)
    return False


class WorkersPhysiques(unittest.TestCase):
    def test_heartbeat_progresse_pendant_inference_et_arret_libere_threads(self):
        h=HorlogeCadence()
        with tempfile.TemporaryDirectory() as tmp:
            s,o,h,p=composer(tmp,h=h);entre=threading.Event();liberer=threading.Event()
            o.bloquer=lambda:(entre.set(),liberer.wait())
            try:
                s.demarrer()
                self.assertTrue(attendre_condition(lambda:bool(s.depot.selectionner_jobs())))
                h.avancer(1000);self.assertTrue(entre.wait(3))
                self.assertTrue(attendre_condition(lambda:(p/'context.json').exists()))
                premiere=s.depot.transaction(lambda t:t['schedule_state']['snapshot_sequence']['sequence'])
                h.avancer(s.r.p['snapshot_heartbeat_seconds']*1000)
                self.assertTrue(attendre_condition(lambda:s.depot.transaction(lambda t:t['schedule_state']['snapshot_sequence']['sequence'])>premiere))
                self.assertTrue(s.etat()['en_marche']);self.assertFalse(liberer.is_set())
            finally:
                liberer.set();s.arreter()
            self.assertFalse(s.etat()['en_marche'])
            self.assertFalse(any(t.name.startswith('xpbots-ia-') for t in threading.enumerate()))
            s.fermer()
