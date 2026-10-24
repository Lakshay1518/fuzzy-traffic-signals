"""Geometry, signal timing constants and demand scenarios of the test corridor.

A stylised east-west urban arterial with three signalised junctions
J1, J2, J3 (J2 is the busiest cross street):

        N3            N2            N1      (side streets: 1 lane each way)
  W ----J1---350 m---J2---400 m---J3---- E  (arterial: 2 lanes each way)

Every junction runs two phases: phase 0 = arterial (EB + WB),
phase 1 = side street (NB + SB).
All values below are typical design values (see report, Chapter 4); the
demand is synthetic and is not field data from a real corridor.
"""

N_JUNCTIONS = 3
EB, WB, NB, SB = 0, 1, 2, 3
APPROACH_NAMES = ("EB", "WB", "NB", "SB")
PHASE_OF = (0, 0, 1, 1)                 # approach -> phase that serves it
PHASE_APPROACHES = ((EB, WB), (NB, SB))

LANES = (2, 2, 1, 1)                    # per approach
SAT_FLOW_PER_LANE = 1800.0              # veh/h/lane (base saturation flow)
SAT_RATE = tuple(l * SAT_FLOW_PER_LANE / 3600.0 for l in LANES)  # veh/s

LINK_LENGTH = (350.0, 400.0)            # m, J1-J2 and J2-J3
FREE_SPEED = 50.0 / 3.6                 # m/s (50 km/h)
LINK_TT = tuple(int(round(L / FREE_SPEED)) for L in LINK_LENGTH)  # 25 s, 29 s
JAM_SPACING = 7.0                       # m per queued car
LINK_STORAGE = tuple(int(2 * L / JAM_SPACING) for L in LINK_LENGTH)  # veh (2 lanes)

AMBER = 3
ALL_RED = 1
INTERGREEN = AMBER + ALL_RED            # s, no discharge
STARTUP_LOST = 2                        # s at the start of every green
LOST_PER_PHASE = INTERGREEN + STARTUP_LOST
LOST_PER_CYCLE = 2 * LOST_PER_PHASE     # 12 s
MIN_GREEN = 7

ARTERIAL_THROUGH = 0.85                 # rest turn off into side streets
SIDE_TO_EB = 0.15                       # side-street vehicles turning onto the arterial
SIDE_TO_WB = 0.15

DETECTION_HORIZON = 7                   # s of look-ahead (advance detector ~100 m upstream)
DURATION = 3600                         # s


class Scenario:
    """Entry demand streams; each has a base flow (veh/h) and a piecewise-linear
    multiplier profile [(t, m), ...] over the simulation horizon."""

    def __init__(self, name, label, eb, wb, side, profiles=None, duration=DURATION):
        self.name = name
        self.label = label
        self.duration = duration
        flat = [(0, 1.0), (duration, 1.0)]
        profiles = profiles or {}
        # stream key: (junction, approach)
        self.streams = [((0, EB), eb, profiles.get((0, EB), profiles.get("all", flat))),
                        ((2, WB), wb, profiles.get((2, WB), profiles.get("all", flat)))]
        for j, (nb, sb) in enumerate(side):
            self.streams.append(((j, NB), nb, profiles.get((j, NB), profiles.get("all", flat))))
            self.streams.append(((j, SB), sb, profiles.get((j, SB), profiles.get("all", flat))))

    @staticmethod
    def multiplier(profile, t):
        for (t0, m0), (t1, m1) in zip(profile, profile[1:]):
            if t0 <= t <= t1:
                if t1 == t0:
                    return m1
                return m0 + (m1 - m0) * (t - t0) / (t1 - t0)
        return profile[-1][1]

    def flow(self, stream, t):
        _, base, profile = stream
        return base * self.multiplier(profile, t)

    def mean_entry_flows(self):
        """Time-averaged flow (veh/h) of every entry stream."""
        out = {}
        for s in self.streams:
            total = sum(self.flow(s, t) for t in range(self.duration))
            out[s[0]] = total / self.duration
        return out


def approach_flows(entry):
    """Propagate mean entry flows through the corridor (turning fractions)
    and return flows[j][a] in veh/h arriving at every approach."""
    f = [[0.0] * 4 for _ in range(N_JUNCTIONS)]
    for j in range(N_JUNCTIONS):
        f[j][NB] = entry.get((j, NB), 0.0)
        f[j][SB] = entry.get((j, SB), 0.0)
    f[0][EB] = entry.get((0, EB), 0.0)
    for j in range(1, N_JUNCTIONS):
        f[j][EB] = ARTERIAL_THROUGH * f[j - 1][EB] + SIDE_TO_EB * (f[j - 1][NB] + f[j - 1][SB])
    f[N_JUNCTIONS - 1][WB] = entry.get((N_JUNCTIONS - 1, WB), 0.0)
    for j in range(N_JUNCTIONS - 2, -1, -1):
        f[j][WB] = ARTERIAL_THROUGH * f[j + 1][WB] + SIDE_TO_WB * (f[j + 1][NB] + f[j + 1][SB])
    return f


# ------------------------------------------------------------------ scenarios

_MOD_SIDE = [(330, 300), (420, 390), (320, 280)]


def _scaled(side, k):
    return [(nb * k, sb * k) for nb, sb in side]


SCENARIOS = {
    "offpeak": Scenario("offpeak", "Off-peak (light, steady)",
                        900, 800, [(180, 160), (240, 220), (170, 150)]),
    "moderate": Scenario("moderate", "Moderate (steady)", 1500, 1300, _MOD_SIDE),
    "peak": Scenario("peak", "Peak (congested, steady)",
                     1900, 1650, [(400, 370), (500, 470), (390, 350)]),
    "peak_build": Scenario("peak_build", "Peak build-up and decay (training)", 1500, 1300, _MOD_SIDE,
                           profiles={"all": [(0, 0.85), (1200, 1.3), (2400, 1.3), (3600, 0.85)]}),
    "tidal": Scenario("tidal", "Tidal shift EB to WB", 1500, 1300, _MOD_SIDE,
                      profiles={(0, EB): [(0, 1.3), (3600, 0.7)],
                                (2, WB): [(0, 0.7), (3600, 1.45)]}),
    "side_surge": Scenario("side_surge", "Side-street surge at J3", 1500, 1300, _MOD_SIDE,
                           profiles={(2, NB): [(0, 1), (1200, 1), (1260, 2.0), (2400, 2.0), (2460, 1), (3600, 1)],
                                     (2, SB): [(0, 1), (1200, 1), (1260, 2.0), (2400, 2.0), (2460, 1), (3600, 1)]}),
}

TRAINING_SCENARIO = "peak_build"
TRAINING_SEEDS = (1001, 1002, 1003)
TEST_SEEDS = tuple(range(1, 11))
