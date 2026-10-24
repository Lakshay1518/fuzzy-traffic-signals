import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fuzzy import (left_shoulder, right_shoulder, triangle, three_term_variable,
                   build_signal_fis, MamdaniFIS, LinguisticVariable)
from controllers import HAND_FUZZY, decode_fuzzy


class MembershipFunctionTests(unittest.TestCase):
    def test_triangle_values(self):
        self.assertEqual(triangle(2, 2, 5, 8), 0.0)
        self.assertEqual(triangle(5, 2, 5, 8), 1.0)
        self.assertAlmostEqual(triangle(3.5, 2, 5, 8), 0.5)
        self.assertAlmostEqual(triangle(6.5, 2, 5, 8), 0.5)
        self.assertEqual(triangle(9, 2, 5, 8), 0.0)

    def test_degenerate_triangle_peak_at_edge(self):
        self.assertEqual(triangle(0.0, 0.0, 0.0, 0.5), 1.0)
        self.assertAlmostEqual(triangle(0.25, 0.0, 0.0, 0.5), 0.5)
        self.assertEqual(triangle(1.0, 0.5, 1.0, 1.0), 1.0)

    def test_shoulders(self):
        self.assertEqual(left_shoulder(1, 2, 6), 1.0)
        self.assertAlmostEqual(left_shoulder(4, 2, 6), 0.5)
        self.assertEqual(left_shoulder(7, 2, 6), 0.0)
        self.assertEqual(right_shoulder(1, 2, 6), 0.0)
        self.assertAlmostEqual(right_shoulder(4, 2, 6), 0.5)
        self.assertEqual(right_shoulder(7, 2, 6), 1.0)

    def test_three_term_partition_sums_to_one(self):
        var = three_term_variable("x", 0, 20, 2.0, 6.0, 12.0)
        for i in range(0, 201):
            mu = var.fuzzify(i / 10.0)
            self.assertAlmostEqual(sum(mu.values()), 1.0, places=9)

    def test_fuzzify_clamps_outside_universe(self):
        var = three_term_variable("x", 0, 20, 2.0, 6.0, 12.0)
        self.assertEqual(var.fuzzify(-5)["Low"], 1.0)
        self.assertEqual(var.fuzzify(99)["High"], 1.0)


class InferenceTests(unittest.TestCase):
    def setUp(self):
        p = decode_fuzzy(HAND_FUZZY)
        self.fis = build_signal_fis(p["g_points"], p["r_points"])

    def test_centroid_of_single_symmetric_set(self):
        out = LinguisticVariable("y", 0, 1, {"M": lambda y: triangle(y, 0.25, 0.5, 0.75)})
        inp = LinguisticVariable("x", 0, 1, {"A": lambda x: 1.0})
        fis = MamdaniFIS([inp], out, [(("A",), "M")])
        self.assertAlmostEqual(fis.infer(0.3), 0.5, places=6)

    def test_output_in_universe(self):
        for g in range(0, 21):
            for r in range(0, 26):
                u = self.fis.infer(g, r)
                self.assertGreaterEqual(u, 0.0)
                self.assertLessEqual(u, 1.0)

    def test_rule_strengths_use_min(self):
        # g=4 is Low 0.5 / Medium 0.5 ; r=0 is fully Low
        s = self.fis.rule_strengths(4.0, 0.0)
        self.assertAlmostEqual(s[0], 0.5)   # Low & Low
        self.assertAlmostEqual(s[3], 0.5)   # Medium & Low
        self.assertAlmostEqual(s[6], 0.0)   # High & Low

    # Classical Mamdani (max aggregation + centroid) is only approximately
    # monotone: where an input crosses from one set to the next, two rules with
    # the same consequent both fire at ~0.5, so max() dips. Measured worst-case
    # drawdown on a 0.1-step grid: 0.036 (red axis), 0.055 (green axis).
    WOBBLE = 0.06

    def test_monotone_in_red_queue(self):
        """More vehicles waiting on red never (materially) lowers the urgency to switch."""
        for g in (0, 4, 8, 12, 16):
            self.assertGreater(self.fis.infer(g, 25), self.fis.infer(g, 0))
            peak = -1.0
            for r in range(0, 26):
                u = self.fis.infer(g, r)
                self.assertGreaterEqual(u, peak - self.WOBBLE)
                peak = max(peak, u)

    def test_monotone_in_green_demand(self):
        """More demand on green never (materially) raises the urgency to switch."""
        for r in (5, 10, 15, 20):
            self.assertLess(self.fis.infer(20, r), self.fis.infer(0, r))
            low = 2.0
            for g in range(0, 21):
                u = self.fis.infer(g, r)
                self.assertLessEqual(u, low + self.WOBBLE)
                low = min(low, u)

    def test_extreme_cases(self):
        self.assertGreater(self.fis.infer(0, 25), 0.75)   # empty green, long red queue -> switch
        self.assertLess(self.fis.infer(20, 0), 0.25)      # busy green, no one waiting -> hold


if __name__ == "__main__":
    unittest.main()
