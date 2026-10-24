"""Run the real-coded GA to tune (a) the fuzzy controller and (b) a fixed-time plan.

Fitness = mean average vehicle delay (s/veh) over the training seeds on the
training scenario (lower is better). Several independent GA runs are made so
that the results can be reported as mean +/- standard deviation.

Usage:  python3 optimise.py [--runs 5] [--pop 30] [--gens 40] [--workers 8]
"""
import argparse
import json
import os
import time
from multiprocessing import Pool

import corridor as C
import controllers as K
import simulator as S
from ga import RealCodedGA

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


# Training sets: list of (scenario, seed) simulations averaged by the fitness.
TRAINING_SETS = {
    "single": [(C.TRAINING_SCENARIO, s) for s in C.TRAINING_SEEDS],
    # extension: one seed each of a light, a moderate and a peak hour
    "mixed": [("offpeak", 1001), ("moderate", 1002), ("peak_build", 1003)],
}


def fitness(task):
    kind, genome, cases = task
    total = 0.0
    for scenario_name, seed in cases:
        ctrl = K.FuzzyController(genome) if kind == "fuzzy" else K.decode_fixed(genome)
        total += S.simulate(C.SCENARIOS[scenario_name], ctrl, seed)["avg_delay"]
    return total / len(cases)


def make_evaluator(pool, kind, cases):
    def evaluate_batch(genomes):
        return pool.map(fitness, [(kind, g, cases) for g in genomes])
    return evaluate_batch


def run_ga(pool, kind, run_id, args):
    bounds = K.FUZZY_BOUNDS if kind == "fuzzy" else K.FIXED_BOUNDS
    seeds_init = [K.HAND_FUZZY] if kind == "fuzzy" else []
    ga = RealCodedGA(bounds, pop_size=args.pop, generations=args.gens,
                     sigma_start=args.sigma, seed=1000 * (1 if kind == "fuzzy" else 2) + run_id,
                     seed_individuals=seeds_init)
    t0 = time.time()

    def log(h):
        if h["generation"] % 5 == 0 or h["generation"] == args.gens:
            print(f"  [{kind} run {run_id}] gen {h['generation']:3d}  best {h['best']:.2f}  "
                  f"mean {h['mean']:.2f}  ({time.time() - t0:.0f}s)", flush=True)

    cases = TRAINING_SETS[args.training]
    best, best_fit, history = ga.run(make_evaluator(pool, kind, cases), log)
    return {"kind": kind, "run": run_id, "best_genome": best, "best_fitness": best_fit,
            "history": history, "seconds": time.time() - t0,
            "settings": {"training": cases, "pop": args.pop, "gens": args.gens, "sigma_start": args.sigma,
                         "crossover": "SBX eta_c=15, pc=0.9", "mutation": "Gaussian, pm=1/n",
                         "selection": "tournament k=3", "elites": 2}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--pop", type=int, default=30)
    ap.add_argument("--gens", type=int, default=40)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--kinds", default="fuzzy,fixed")
    ap.add_argument("--tag", default="")
    ap.add_argument("--training", default="single", choices=sorted(TRAINING_SETS))
    args = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)

    with Pool(args.workers) as pool:
        for kind in args.kinds.split(","):
            runs = [run_ga(pool, kind, r, args) for r in range(args.runs)]
            path = os.path.join(RESULTS, f"ga_{kind}{args.tag}.json")
            with open(path, "w") as f:
                json.dump(runs, f, indent=1)
            fits = [r["best_fitness"] for r in runs]
            print(f"{kind}: best fitness per run {['%.2f' % x for x in fits]} -> {path}")


if __name__ == "__main__":
    main()
