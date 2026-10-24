"""Random-number helpers built only on a uniform [0, 1) generator.

The only thing taken from Python is the Mersenne-Twister uniform generator
(random.Random.random). Gaussian draws (Box-Muller) and Poisson draws
(Knuth's multiplication method) are implemented here by hand so that the
soft-computing code does not depend on any library sampling routine.
"""
import math
import random


class RNG:
    def __init__(self, seed):
        self._r = random.Random(seed)
        self._spare = None  # second Box-Muller value

    def uniform(self):
        return self._r.random()

    def uniform_range(self, lo, hi):
        return lo + (hi - lo) * self._r.random()

    def randint(self, lo, hi):
        """Integer in [lo, hi] inclusive."""
        return lo + int(self._r.random() * (hi - lo + 1))

    def gauss(self):
        """Standard normal N(0, 1) via the Box-Muller transform."""
        if self._spare is not None:
            z, self._spare = self._spare, None
            return z
        u1 = self._r.random()
        while u1 <= 1e-12:
            u1 = self._r.random()
        u2 = self._r.random()
        radius = math.sqrt(-2.0 * math.log(u1))
        self._spare = radius * math.sin(2.0 * math.pi * u2)
        return radius * math.cos(2.0 * math.pi * u2)

    def poisson(self, lam):
        """Poisson(lam) count via Knuth's method (fine for lam < ~30)."""
        if lam <= 0.0:
            return 0
        limit = math.exp(-lam)
        k, p = 0, 1.0
        while True:
            p *= self._r.random()
            if p <= limit:
                return k
            k += 1
