"""Discrete-time (1 s) mesoscopic simulator of the three-junction corridor.

Model
  * Poisson vehicle arrivals at the 8 entry approaches (pre-generated from the
    seed, so every controller sees exactly the same vehicles: common random
    numbers).
  * Point (vertical) queues at every stop line, served FIFO at the saturation
    flow while the approach has effective green (green minus start-up lost time).
  * Vehicles leaving J1/J2/J3 either exit or travel to the next junction with
    a fixed free-flow link travel time.
  * Spill-back: a vehicle cannot enter a link whose storage (transit + queue)
    is full, which blocks its approach for that second.
  * Delay of a vehicle = total time spent waiting in stop-line queues.
    Vehicles still queued at the end are charged their waiting time so far.
"""
from collections import deque

import corridor as C
from rng import RNG


class Vehicle:
    __slots__ = ("t_gen", "delay", "stops", "u", "side_origin")

    def __init__(self, t_gen, u, side_origin):
        self.t_gen = t_gen
        self.delay = 0
        self.stops = 0
        self.u = u
        self.side_origin = side_origin


def generate_arrivals(scenario, seed):
    rng = RNG(seed)
    arrivals = {}
    for stream in scenario.streams:
        key = stream[0]
        side = key[1] in (C.NB, C.SB)
        lst = []
        for t in range(scenario.duration):
            k = rng.poisson(scenario.flow(stream, t) / 3600.0)
            for _ in range(k):
                u = tuple(rng.uniform() for _ in range(C.N_JUNCTIONS))
                lst.append(Vehicle(t, u, side))
        arrivals[key] = lst
    return arrivals


class CorridorSim:
    def __init__(self, scenario, seed, horizon=C.DETECTION_HORIZON):
        self.scenario = scenario
        self.horizon = horizon
        self.T = scenario.duration
        self.entry = generate_arrivals(scenario, seed)
        self.entry_ptr = {k: 0 for k in self.entry}
        self.vehicles = [v for lst in self.entry.values() for v in lst]
        nj = C.N_JUNCTIONS
        self.queues = [[deque() for _ in range(4)] for _ in range(nj)]
        self.credit = [[0.0] * 4 for _ in range(nj)]
        self.link_eb = [deque() for _ in range(nj - 1)]  # J(i) -> J(i+1): (arrival_time, vehicle)
        self.link_wb = [deque() for _ in range(nj - 1)]  # J(i+1) -> J(i)
        self.exited = 0
        self.served = [[0] * 4 for _ in range(nj)]
        self.served_delay = [[0] * 4 for _ in range(nj)]
        self.max_queue = [[0] * 4 for _ in range(nj)]
        self.max_link_occupancy = [0] * (nj - 1)
        self.blocked_seconds = 0

    # ------------------------------------------------------------ sensors
    def queue_len(self, j, a):
        return len(self.queues[j][a])

    def approaching(self, j, a, t):
        """Vehicles that will join approach (j, a) within the next `horizon` s."""
        limit = t + self.horizon
        key = (j, a)
        if key in self.entry:
            lst, i, n = self.entry[key], self.entry_ptr[key], 0
            while i < len(lst) and lst[i].t_gen <= limit:
                n += 1
                i += 1
            return n
        link = self.link_eb[j - 1] if a == C.EB else self.link_wb[j]
        n = 0
        for arr, _ in link:
            if arr > limit:
                break
            n += 1
        return n

    # ------------------------------------------------------------ helpers
    def _destination(self, v, j, a):
        """Return ('eb', link), ('wb', link) or None (exit) for a discharged vehicle."""
        u = v.u[j]
        last = C.N_JUNCTIONS - 1
        if a == C.EB:
            go_eb, go_wb = u < C.ARTERIAL_THROUGH, False
        elif a == C.WB:
            go_eb, go_wb = False, u < C.ARTERIAL_THROUGH
        else:
            go_eb = u < C.SIDE_TO_EB
            go_wb = (not go_eb) and u < C.SIDE_TO_EB + C.SIDE_TO_WB
        if go_eb and j < last:
            return ("eb", j)
        if go_wb and j > 0:
            return ("wb", j - 1)
        return None

    def _link_full(self, dest):
        kind, i = dest
        if kind == "eb":
            occ = len(self.link_eb[i]) + len(self.queues[i + 1][C.EB])
        else:
            occ = len(self.link_wb[i]) + len(self.queues[i][C.WB])
        return occ >= C.LINK_STORAGE[i]

    # ------------------------------------------------------------ main loop
    def run(self, controller, record=False):
        controller.reset(C.N_JUNCTIONS)
        nj = C.N_JUNCTIONS
        trace = {"phase": [], "queues": [], "total_queued": []} if record else None

        for t in range(self.T):
            # 1. arrivals from outside the corridor
            for key, lst in self.entry.items():
                i = self.entry_ptr[key]
                q = self.queues[key[0]][key[1]]
                while i < len(lst) and lst[i].t_gen == t:
                    q.append((lst[i], t))
                    i += 1
                self.entry_ptr[key] = i
            # 2. arrivals from upstream links
            for i in range(nj - 1):
                dq = self.link_eb[i]
                while dq and dq[0][0] == t:
                    self.queues[i + 1][C.EB].append((dq.popleft()[1], t))
                dq = self.link_wb[i]
                while dq and dq[0][0] == t:
                    self.queues[i][C.WB].append((dq.popleft()[1], t))

            # 3. signals and discharge
            phases = []
            for j in range(nj):
                green, since = controller.signal(t, j, self)
                phases.append(green)
                for a in range(4):
                    if green < 0 or C.PHASE_OF[a] != green or since < C.STARTUP_LOST:
                        self.credit[j][a] = 0.0
                        continue
                    q = self.queues[j][a]
                    self.credit[j][a] += C.SAT_RATE[a]
                    while self.credit[j][a] >= 1.0 and q:
                        v, t_join = q[0]
                        dest = self._destination(v, j, a)
                        if dest is not None and self._link_full(dest):
                            self.blocked_seconds += 1
                            break
                        q.popleft()
                        self.credit[j][a] -= 1.0
                        wait = t - t_join
                        v.delay += wait
                        if wait > 0:
                            v.stops += 1
                        self.served[j][a] += 1
                        self.served_delay[j][a] += wait
                        if dest is None:
                            self.exited += 1
                        elif dest[0] == "eb":
                            self.link_eb[dest[1]].append((t + C.LINK_TT[dest[1]], v))
                        else:
                            self.link_wb[dest[1]].append((t + C.LINK_TT[dest[1]], v))
                    if self.credit[j][a] > 1.0:  # no stored-up bursts (empty or blocked)
                        self.credit[j][a] = 1.0

            # 4. statistics
            for j in range(nj):
                for a in range(4):
                    n = len(self.queues[j][a])
                    if n > self.max_queue[j][a]:
                        self.max_queue[j][a] = n
            for i in range(nj - 1):
                occ = max(len(self.link_eb[i]) + len(self.queues[i + 1][C.EB]),
                          len(self.link_wb[i]) + len(self.queues[i][C.WB]))
                if occ > self.max_link_occupancy[i]:
                    self.max_link_occupancy[i] = occ
            if record:
                qs = [[len(self.queues[j][a]) for a in range(4)] for j in range(nj)]
                trace["phase"].append(phases)
                trace["queues"].append(qs)
                trace["total_queued"].append(sum(sum(r) for r in qs))

        return self._results(trace)

    def _results(self, trace):
        residual_queued = 0
        for j in range(C.N_JUNCTIONS):
            for a in range(4):
                for v, t_join in self.queues[j][a]:
                    v.delay += self.T - t_join
                    residual_queued += 1
        in_transit = sum(len(d) for d in self.link_eb) + sum(len(d) for d in self.link_wb)
        n = len(self.vehicles)
        side = [v for v in self.vehicles if v.side_origin]
        art = [v for v in self.vehicles if not v.side_origin]
        res = {
            "vehicles": n,
            "avg_delay": sum(v.delay for v in self.vehicles) / n if n else 0.0,
            "avg_stops": sum(v.stops for v in self.vehicles) / n if n else 0.0,
            "avg_delay_arterial_origin": sum(v.delay for v in art) / len(art) if art else 0.0,
            "avg_delay_side_origin": sum(v.delay for v in side) / len(side) if side else 0.0,
            "exited": self.exited,
            "residual_queued": residual_queued,
            "in_transit": in_transit,
            "max_queue": self.max_queue,
            "max_link_occupancy": self.max_link_occupancy,
            "served": self.served,
            "served_delay": self.served_delay,
            "blocked_seconds": self.blocked_seconds,
        }
        if trace is not None:
            res["trace"] = trace
        return res


def simulate(scenario, controller, seed, record=False, horizon=C.DETECTION_HORIZON):
    return CorridorSim(scenario, seed, horizon).run(controller, record)
