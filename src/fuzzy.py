"""Mamdani fuzzy inference system written from first principles.

No fuzzy-logic library is used. The module provides
  * membership functions (left shoulder, triangle, right shoulder),
  * linguistic variables (fuzzification),
  * a Mamdani rule base with min (AND) / min (implication) /
    max (aggregation) and centroid defuzzification,
  * the traffic-signal "switch urgency" controller used in this project.
"""


# ---------------------------------------------------------------- membership functions

def left_shoulder(x, a, b):
    """1 for x <= a, falls linearly to 0 at x = b."""
    if x <= a:
        return 1.0
    if x >= b:
        return 0.0
    return (b - x) / (b - a)


def right_shoulder(x, a, b):
    """0 for x <= a, rises linearly to 1 at x = b."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    return (x - a) / (b - a)


def triangle(x, a, b, c):
    """Triangle with feet a, c and peak b (a == b or b == c allowed)."""
    if x < a or x > c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


class LinguisticVariable:
    """A crisp universe [lo, hi] covered by named fuzzy sets."""

    def __init__(self, name, lo, hi, terms):
        self.name = name
        self.lo = lo
        self.hi = hi
        self.terms = terms  # dict: term name -> membership function of x

    def fuzzify(self, x):
        if x < self.lo:
            x = self.lo
        elif x > self.hi:
            x = self.hi
        return {t: mf(x) for t, mf in self.terms.items()}


def three_term_variable(name, lo, hi, a, b, c, labels=("Low", "Medium", "High")):
    """Low / Medium / High partition defined by three break points a < b < c.

    Low    : 1 up to a, 0 from b
    Medium : triangle (a, b, c)
    High   : 0 up to b, 1 from c
    The three memberships always sum to 1 (a strong fuzzy partition).
    """
    low, med, high = labels
    return LinguisticVariable(name, lo, hi, {
        low: lambda x, a=a, b=b: left_shoulder(x, a, b),
        med: lambda x, a=a, b=b, c=c: triangle(x, a, b, c),
        high: lambda x, b=b, c=c: right_shoulder(x, b, c),
    })


# ---------------------------------------------------------------- Mamdani inference

class MamdaniFIS:
    def __init__(self, inputs, output, rules, resolution=101):
        """
        inputs     : list of LinguisticVariable
        output     : LinguisticVariable (its universe is sampled for the centroid)
        rules      : list of (tuple of input term names, output term name)
        resolution : number of sample points used for centroid defuzzification
        """
        self.inputs = inputs
        self.output = output
        self.rules = rules
        step = (output.hi - output.lo) / (resolution - 1)
        self._ys = [output.lo + k * step for k in range(resolution)]
        self._out_mf = {t: [mf(y) for y in self._ys] for t, mf in output.terms.items()}

    def rule_strengths(self, *xs):
        """Firing strength of every rule (min of its antecedent memberships)."""
        mus = [var.fuzzify(x) for var, x in zip(self.inputs, xs)]
        strengths = []
        for antecedent, _ in self.rules:
            s = 1.0
            for mu, term in zip(mus, antecedent):
                if mu[term] < s:
                    s = mu[term]
            strengths.append(s)
        return strengths

    def aggregate(self, *xs):
        """Aggregated output fuzzy set sampled on the output universe."""
        clip = {t: 0.0 for t in self.output.terms}
        for s, (_, consequent) in zip(self.rule_strengths(*xs), self.rules):
            if s > clip[consequent]:
                clip[consequent] = s  # max over rules sharing a consequent
        agg = [0.0] * len(self._ys)
        for term, level in clip.items():
            if level <= 0.0:
                continue
            mf = self._out_mf[term]
            for k in range(len(agg)):
                v = mf[k] if mf[k] < level else level  # min implication (clipping)
                if v > agg[k]:
                    agg[k] = v                         # max aggregation
        return agg

    def infer(self, *xs):
        """Crisp output by the centroid (centre of gravity) method."""
        agg = self.aggregate(*xs)
        num = 0.0
        den = 0.0
        for y, mu in zip(self._ys, agg):
            num += y * mu
            den += mu
        if den == 0.0:
            return 0.5 * (self.output.lo + self.output.hi)
        return num / den


# ---------------------------------------------------------------- traffic-signal controller FIS

# Rule base (expert knowledge, kept fixed; the EA tunes the membership functions).
# Output = urgency to end the current green.
#                 Red queue:  Low       Medium    High
SIGNAL_RULES = [
    (("Low", "Low"), "Low"),    (("Low", "Medium"), "High"),    (("Low", "High"), "High"),
    (("Medium", "Low"), "Low"), (("Medium", "Medium"), "Medium"), (("Medium", "High"), "High"),
    (("High", "Low"), "Low"),   (("High", "Medium"), "Low"),    (("High", "High"), "Medium"),
]

GREEN_DEMAND_MAX = 20.0  # veh per lane
RED_QUEUE_MAX = 25.0     # veh per lane


def build_signal_fis(g_points, r_points):
    """g_points, r_points: (a, b, c) break points for the two input variables."""
    green = three_term_variable("green_demand", 0.0, GREEN_DEMAND_MAX, *g_points)
    red = three_term_variable("red_queue", 0.0, RED_QUEUE_MAX, *r_points)
    urgency = LinguisticVariable("switch_urgency", 0.0, 1.0, {
        "Low": lambda y: triangle(y, 0.0, 0.0, 0.5),
        "Medium": lambda y: triangle(y, 0.25, 0.5, 0.75),
        "High": lambda y: triangle(y, 0.5, 1.0, 1.0),
    })
    return MamdaniFIS([green, red], urgency, SIGNAL_RULES)
