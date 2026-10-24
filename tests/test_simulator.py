import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import corridor as C
import controllers as K
import simulator as S


class AlwaysPhase:
    """Test controller: one phase permanently green at every junction."""

    def __init__(self, phase):
        self.phase = phase

    def reset(self, n):
        pass

    def signal(self, t, j, sim):
        return self.phase, t


def isolated_scenario(q_eb, q_nb, duration=3600):
    """Only J1 eastbound and J1 northbound carry traffic."""
    return C.Scenario("iso", "isolated J1", q_eb, 0, [(q_nb, 0), (0, 0), (0, 0)], duration=duration)


class ConservationAndBasics(unittest.TestCase):
    def test_vehicle_conservation(self):
        sc = C.SCENARIOS["peak"]
        sim = S.CorridorSim(sc, seed=3)
        res = sim.run(K.webster_plan(sc))
        self.assertEqual(res["vehicles"], res["exited"] + res["residual_queued"] + res["in_transit"])

    def test_zero_demand_zero_delay(self):
        sc = C.Scenario("empty", "empty", 0, 0, [(0, 0)] * 3, duration=600)
        res = S.simulate(sc, K.webster_plan(C.SCENARIOS["moderate"]), seed=1)
        self.assertEqual(res["vehicles"], 0)
        self.assertEqual(res["avg_delay"], 0.0)

    def test_same_seed_is_deterministic(self):
        sc = C.SCENARIOS["moderate"]
        a = S.simulate(sc, K.FuzzyController(K.HAND_FUZZY), seed=5)
        b = S.simulate(sc, K.FuzzyController(K.HAND_FUZZY), seed=5)
        self.assertEqual(a["avg_delay"], b["avg_delay"])
        self.assertEqual(a["exited"], b["exited"])

    def test_common_random_numbers_across_controllers(self):
        sc = C.SCENARIOS["moderate"]
        a = S.simulate(sc, K.webster_plan(sc), seed=8)
        b = S.simulate(sc, K.FuzzyController(K.HAND_FUZZY), seed=8)
        self.assertEqual(a["vehicles"], b["vehicles"])

    def test_red_approaches_never_discharge(self):
        sc = C.SCENARIOS["moderate"]
        res = S.simulate(sc, AlwaysPhase(0), seed=2)
        for j in range(C.N_JUNCTIONS):
            self.assertEqual(res["served"][j][C.NB], 0)
            self.assertEqual(res["served"][j][C.SB], 0)

    def test_discharge_never_exceeds_saturation_flow(self):
        # 3000 veh/h offered to J1 eastbound with permanent green; 2 lanes -> 3600 veh/h max
        sc = isolated_scenario(3000, 0, duration=1800)
        sim = S.CorridorSim(sc, seed=4)
        res = sim.run(AlwaysPhase(0))
        cap = C.SAT_RATE[C.EB] * (sc.duration - C.STARTUP_LOST)
        self.assertLessEqual(res["served"][0][C.EB], cap)

    def test_oversaturated_side_street_builds_queue(self):
        sc = isolated_scenario(0, 1000, duration=1800)   # 1000 veh/h on a 1-lane approach
        plan = K.FixedTimeController(60, [40, 40, 40], [0, 0, 0])  # side gets 12 s of 60 s
        res = S.simulate(sc, plan, seed=6)
        self.assertGreater(res["residual_queued"], 100)

    def test_link_storage_respected(self):
        sc = C.SCENARIOS["peak"]
        # J1 and J2 always arterial green, J3 always side green -> EB link J2-J3 fills up
        class Starve:
            def reset(self, n):
                pass

            def signal(self, t, j, sim):
                return (1 if j == 2 else 0), t
        res = S.simulate(sc, Starve(), seed=1)
        for i in range(len(C.LINK_STORAGE)):
            self.assertLessEqual(res["max_link_occupancy"][i], C.LINK_STORAGE[i])
        self.assertGreater(res["blocked_seconds"], 0)


class ControllerTimingTests(unittest.TestCase):
    def test_fixed_time_cycle_structure(self):
        plan = K.FixedTimeController(60, [30, 30, 30], [0, 10, 20])
        greens0 = [plan.signal(t, 0, None)[0] for t in range(60)]
        self.assertEqual(greens0.count(0), 30)
        self.assertEqual(greens0.count(-1), 2 * C.INTERGREEN)
        self.assertEqual(greens0.count(1), 60 - 30 - 2 * C.INTERGREEN)
        # offset: junction 1 starts its arterial green 10 s later
        self.assertEqual(plan.signal(10, 1, None), (0, 0))
        self.assertEqual(plan.signal(9, 1, None)[0], -1)

    def test_webster_plan_is_valid(self):
        for name, sc in C.SCENARIOS.items():
            plan = K.webster_plan(sc)
            self.assertTrue(40 <= plan.cycle <= 150, name)
            for g in plan.art_green:
                self.assertGreaterEqual(g, C.MIN_GREEN)
                self.assertGreaterEqual(plan.cycle - g - 2 * C.INTERGREEN, C.MIN_GREEN)

    def test_fuzzy_respects_min_max_green_and_intergreen(self):
        sc = C.SCENARIOS["peak_build"]
        ctrl = K.FuzzyController(K.HAND_FUZZY)
        res = S.simulate(sc, ctrl, seed=2, record=True)
        p = ctrl.params
        for j in range(C.N_JUNCTIONS):
            seq = [ph[j] for ph in res["trace"]["phase"]]
            runs, cur, n = [], seq[0], 0
            for x in seq:
                if x == cur:
                    n += 1
                else:
                    runs.append((cur, n))
                    cur, n = x, 1
            for k, (phase, length) in enumerate(runs):
                if phase == -1:
                    self.assertEqual(length, C.INTERGREEN)
                elif k > 0:   # the first green may be cut by t = 0
                    self.assertGreaterEqual(length, int(p["min_green"][phase]))
                    self.assertLessEqual(length, int(p["max_green"][phase]) + 1)
            # phases alternate
            greens = [ph for ph, _ in runs if ph >= 0]
            for a, b in zip(greens, greens[1:]):
                self.assertNotEqual(a, b)


class WebsterValidation(unittest.TestCase):
    """The simulator's queueing delay at an isolated fixed-time approach should
    agree with Webster's (1958) delay formula for random arrivals."""

    @staticmethod
    def webster_delay(q, s, c, g):
        lam = g / c
        x = q / (lam * s)
        d1 = c * (1 - lam) ** 2 / (2 * (1 - lam * x))
        d2 = x * x / (2 * q * (1 - x))
        d3 = 0.65 * (c / (q * q)) ** (1.0 / 3.0) * x ** (2 + 5 * lam)
        return d1 + d2 - d3

    def check(self, q_vph, cycle, art_green, seeds=8, tol=0.12):
        sc = isolated_scenario(q_vph, 0, duration=7200)
        plan = K.FixedTimeController(cycle, [art_green] * 3, [0, 0, 0])
        total, n = 0, 0
        for seed in range(1, seeds + 1):
            res = S.simulate(sc, plan, seed)
            total += res["served_delay"][0][C.EB]
            n += res["served"][0][C.EB]
        sim_d = total / n
        g_eff = art_green - C.STARTUP_LOST
        web = self.webster_delay(q_vph / 3600.0, C.SAT_RATE[C.EB], cycle, g_eff)
        self.assertAlmostEqual(sim_d, web, delta=tol * web,
                               msg=f"sim {sim_d:.2f} s vs Webster {web:.2f} s")
        return sim_d, web

    def test_moderate_saturation(self):
        self.check(1200, 60, 32)   # x ~ 0.67

    def test_high_saturation(self):
        self.check(1500, 80, 42)   # x ~ 0.83


if __name__ == "__main__":
    unittest.main()
