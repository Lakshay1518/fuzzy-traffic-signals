import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ga import RealCodedGA
from rng import RNG


def sphere(x):
    return sum((v - 1.0) ** 2 for v in x)


def rastrigin(x):
    import math
    return 10 * len(x) + sum(v * v - 10 * math.cos(2 * math.pi * v) for v in x)


class RNGTests(unittest.TestCase):
    def test_gauss_moments(self):
        r = RNG(7)
        xs = [r.gauss() for _ in range(40000)]
        mean = sum(xs) / len(xs)
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        self.assertAlmostEqual(mean, 0.0, delta=0.03)
        self.assertAlmostEqual(var, 1.0, delta=0.03)

    def test_poisson_mean_and_variance(self):
        r = RNG(11)
        for lam in (0.1, 0.5, 2.0):
            xs = [r.poisson(lam) for _ in range(40000)]
            mean = sum(xs) / len(xs)
            var = sum((x - mean) ** 2 for x in xs) / len(xs)
            self.assertAlmostEqual(mean, lam, delta=0.05 * max(1, lam))
            self.assertAlmostEqual(var, lam, delta=0.08 * max(1, lam))

    def test_randint_inclusive(self):
        r = RNG(3)
        seen = {r.randint(0, 4) for _ in range(2000)}
        self.assertEqual(seen, {0, 1, 2, 3, 4})


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.bounds = [(-5.0, 5.0)] * 6
        self.ga = RealCodedGA(self.bounds, seed=1)

    def test_sbx_children_within_bounds(self):
        for _ in range(500):
            p1 = self.ga.random_individual()
            p2 = self.ga.random_individual()
            for c in self.ga.sbx(p1, p2):
                for v, (lo, hi) in zip(c, self.bounds):
                    self.assertTrue(lo <= v <= hi)

    def test_sbx_preserves_mean_before_clamping(self):
        ga = RealCodedGA([(-1e9, 1e9)] * 4, seed=2, crossover_rate=1.0)
        p1, p2 = [1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]
        c1, c2 = ga.sbx(p1, p2)
        for a, b, x, y in zip(p1, p2, c1, c2):
            self.assertAlmostEqual(a + b, x + y, places=9)

    def test_mutation_within_bounds(self):
        for _ in range(500):
            m = self.ga.mutate(self.ga.random_individual(), 0.5)
            for v, (lo, hi) in zip(m, self.bounds):
                self.assertTrue(lo <= v <= hi)


class GATests(unittest.TestCase):
    @staticmethod
    def batch(f):
        return lambda genomes: [f(g) for g in genomes]

    def test_converges_on_sphere(self):
        ga = RealCodedGA([(-5.0, 5.0)] * 5, pop_size=40, generations=80, seed=5)
        best, fit, _ = ga.run(self.batch(sphere))
        self.assertLess(fit, 1e-2)
        for v in best:
            self.assertAlmostEqual(v, 1.0, delta=0.1)

    def test_improves_on_rastrigin(self):
        ga = RealCodedGA([(-5.12, 5.12)] * 4, pop_size=40, generations=80, seed=9)
        _, fit, hist = ga.run(self.batch(rastrigin))
        self.assertLess(fit, hist[0]["best"])
        self.assertLess(fit, 2.5)

    def test_elitism_best_never_worsens(self):
        ga = RealCodedGA([(-5.0, 5.0)] * 5, pop_size=20, generations=30, seed=13)
        _, _, hist = ga.run(self.batch(sphere))
        bests = [h["best"] for h in hist]
        for a, b in zip(bests, bests[1:]):
            self.assertLessEqual(b, a)

    def test_same_seed_same_result(self):
        r1 = RealCodedGA([(-5.0, 5.0)] * 3, pop_size=10, generations=10, seed=21).run(self.batch(sphere))
        r2 = RealCodedGA([(-5.0, 5.0)] * 3, pop_size=10, generations=10, seed=21).run(self.batch(sphere))
        self.assertEqual(r1[0], r2[0])

    def test_seed_individual_kept_when_best(self):
        ga = RealCodedGA([(-5.0, 5.0)] * 3, pop_size=10, generations=5, seed=4,
                         seed_individuals=[[1.0, 1.0, 1.0]])
        best, fit, _ = ga.run(self.batch(sphere))
        self.assertEqual(fit, 0.0)


if __name__ == "__main__":
    unittest.main()
