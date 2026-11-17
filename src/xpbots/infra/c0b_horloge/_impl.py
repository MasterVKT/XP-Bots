"""Seule lecture de l’horloge physique pour la coquille du robot."""
import math
import time


class HorlogeSysteme:
    def utc_ms(self):
        return time.time_ns() // 1_000_000

    def monotone_ns(self):
        return time.monotonic_ns()

    def attendre_ms(self, duree):
        if type(duree) not in (int, float) or not math.isfinite(duree) or duree < 0:
            raise ValueError('durée finie positive ou nulle requise')
        time.sleep(duree / 1000)
