"""Signal controllers: fixed-time plans (Webster / GA-tuned) and the fuzzy controller.

Every controller answers, once per second and per junction,
    signal(t, j, sim) -> (green_phase, seconds_since_green_start)
with green_phase = -1 during the inter-green (amber + all-red).
"""
import corridor as C
from fuzzy import build_signal_fis, GREEN_DEMAND_MAX, RED_QUEUE_MAX


# =========================================================== fixed-time plans

class FixedTimeController:
    """Common cycle, per-junction arterial green and offsets (coordinated plan).

    Cycle layout at junction j, with tau = (t - offset_j) mod C:
        [0, Ga)            arterial green
        [Ga, Ga+I)         inter-green
        [Ga+I, C-I)        side-street green
        [C-I, C)           inter-green
    """

    def __init__(self, cycle, art_green, offsets, name="Fixed-time"):
        self.cycle = cycle
        self.art_green = art_green
        self.offsets = offsets
        self.name = name

    def reset(self, n):
        pass

    def signal(self, t, j, sim):
        c, ga, ig = self.cycle, self.art_green[j], C.INTERGREEN
        tau = (t - self.offsets[j]) % c
        if tau < ga:
            return 0, tau
        if tau < ga + ig:
            return -1, 0
        if tau < c - ig:
            return 1, tau - ga - ig
        return -1, 0

    def describe(self):
        return {"cycle": self.cycle, "arterial_green": self.art_green,
                "side_green": [self.cycle - g - 2 * C.INTERGREEN for g in self.art_green],
                "offsets": self.offsets}


def split_plan(cycle, art_share, offsets, name):
    """Build a plan from a cycle, the arterial share of effective green and offsets."""
    cycle = int(round(cycle))
    eff = cycle - C.LOST_PER_CYCLE
    greens = []
    for s in art_share:
        g_art = int(round(s * eff)) + C.STARTUP_LOST
        g_side = cycle - 2 * C.INTERGREEN - g_art
        if g_side < C.MIN_GREEN:
            g_art = cycle - 2 * C.INTERGREEN - C.MIN_GREEN
        if g_art < C.MIN_GREEN:
            g_art = C.MIN_GREEN
        greens.append(g_art)
    return FixedTimeController(cycle, greens, [int(round(o)) % cycle for o in offsets], name)


def webster_plan(scenario, c_min=40, c_max=150):
    """Webster (1958) optimum cycle and equisaturation splits from the scenario's
    mean flows, with a common cycle and eastbound green-wave offsets."""
    flows = C.approach_flows(scenario.mean_entry_flows())
    L = C.LOST_PER_CYCLE
    cycles, shares, ys = [], [], []
    for j in range(C.N_JUNCTIONS):
        y_art = max(flows[j][C.EB] / (C.LANES[C.EB] * C.SAT_FLOW_PER_LANE),
                    flows[j][C.WB] / (C.LANES[C.WB] * C.SAT_FLOW_PER_LANE))
        y_side = max(flows[j][C.NB] / (C.LANES[C.NB] * C.SAT_FLOW_PER_LANE),
                     flows[j][C.SB] / (C.LANES[C.SB] * C.SAT_FLOW_PER_LANE))
        Y = y_art + y_side
        ys.append((y_art, y_side, Y))
        c0 = (1.5 * L + 5.0) / (1.0 - Y) if Y < 0.95 else c_max
        cycles.append(c0)
        shares.append(y_art / Y)
    cycle = min(c_max, max(c_min, max(cycles)))
    offsets = [0, C.LINK_TT[0], C.LINK_TT[0] + C.LINK_TT[1]]
    plan = split_plan(cycle, shares, offsets, "Webster fixed-time")
    plan.webster_info = {"flows_vph": flows, "flow_ratios": ys, "c0_per_junction": cycles}
    return plan


FIXED_BOUNDS = [(40.0, 150.0), (0.3, 0.85), (0.3, 0.85), (0.3, 0.85), (0.0, 1.0), (0.0, 1.0)]
FIXED_GENE_NAMES = ["cycle", "share_J1", "share_J2", "share_J3", "offset_J2", "offset_J3"]


def decode_fixed(genome, name="GA fixed-time"):
    cycle = int(round(genome[0]))
    return split_plan(cycle, genome[1:4], [0, genome[4] * cycle, genome[5] * cycle], name)


# =========================================================== fuzzy controller

FUZZY_BOUNDS = [
    (0.0, 6.0), (0.5, 7.0), (0.5, 7.0),     # green-demand break points a, b-a, c-b
    (0.0, 8.0), (0.5, 8.5), (0.5, 8.5),     # red-queue break points a, b-a, c-b
    (0.30, 0.80),                           # switch threshold theta (max urgency ~0.83)
    (7.0, 20.0), (25.0, 90.0),              # arterial min / max green (s)
    (7.0, 15.0), (15.0, 60.0),              # side-street min / max green (s)
]
FUZZY_GENE_NAMES = ["g_a", "g_b-a", "g_c-b", "r_a", "r_b-a", "r_c-b", "theta",
                    "gmin_art", "gmax_art", "gmin_side", "gmax_side"]

# Hand-designed starting point (engineering judgement, before any tuning).
HAND_FUZZY = [2.0, 4.0, 6.0, 3.0, 5.0, 7.0, 0.5, 10.0, 60.0, 7.0, 40.0]


def decode_fuzzy(genome):
    g_a = genome[0]
    g_b = g_a + genome[1]
    g_c = g_b + genome[2]
    r_a = genome[3]
    r_b = r_a + genome[4]
    r_c = r_b + genome[5]
    return {
        "g_points": (g_a, g_b, g_c),
        "r_points": (r_a, r_b, r_c),
        "theta": genome[6],
        "min_green": (genome[7], genome[9]),
        "max_green": (genome[8], genome[10]),
    }


class _JunctionState:
    __slots__ = ("phase", "in_green", "elapsed", "ig_left")

    def __init__(self):
        self.phase = 0
        self.in_green = True
        self.elapsed = 0
        self.ig_left = 0


class FuzzyController:
    """Per-junction Mamdani controller that decides, every second after the
    minimum green, whether to end the current green.

    Inputs (per lane, so 2-lane arterial and 1-lane side streets compare fairly)
      green_demand : max over green approaches of (queue + vehicles arriving
                     within the detection horizon) / lanes
      red_queue    : max over red approaches of queue / lanes
    Output
      switch_urgency in [0, 1]; the green ends when urgency > theta,
      or when the maximum green is reached.
    """

    def __init__(self, genome, name="Fuzzy"):
        self.genome = list(genome)
        self.params = decode_fuzzy(genome)
        self.fis = build_signal_fis(self.params["g_points"], self.params["r_points"])
        self.name = name
        self._cache = {}
        self.decisions = 0

    def reset(self, n):
        self.state = [_JunctionState() for _ in range(n)]

    def urgency(self, g, r):
        g = min(g, GREEN_DEMAND_MAX)
        r = min(r, RED_QUEUE_MAX)
        key = (int(round(g * 2)), int(round(r * 2)))  # inputs are multiples of 0.5
        u = self._cache.get(key)
        if u is None:
            u = self.fis.infer(key[0] / 2.0, key[1] / 2.0)
            self._cache[key] = u
        return u

    def _inputs(self, t, j, phase, sim):
        g = 0.0
        for a in C.PHASE_APPROACHES[phase]:
            d = (sim.queue_len(j, a) + sim.approaching(j, a, t)) / C.LANES[a]
            if d > g:
                g = d
        r = 0.0
        for a in C.PHASE_APPROACHES[1 - phase]:
            d = sim.queue_len(j, a) / C.LANES[a]
            if d > r:
                r = d
        return g, r

    def signal(self, t, j, sim):
        s = self.state[j]
        p = self.params
        if s.in_green:
            if s.elapsed >= p["min_green"][s.phase]:
                end = s.elapsed >= p["max_green"][s.phase]
                if not end:
                    g, r = self._inputs(t, j, s.phase, sim)
                    self.decisions += 1
                    end = self.urgency(g, r) > p["theta"]
                if end:
                    s.in_green = False
                    s.ig_left = C.INTERGREEN
            if s.in_green:
                out = (s.phase, s.elapsed)
                s.elapsed += 1
                return out
        s.ig_left -= 1
        if s.ig_left == 0:
            s.phase = 1 - s.phase
            s.in_green = True
            s.elapsed = 0
        return -1, 0
