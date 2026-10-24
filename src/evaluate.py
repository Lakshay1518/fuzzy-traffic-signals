"""Evaluate all controllers on unseen test seeds and every scenario.

Produces results/evaluation.json, results/tables.md and demo traces.
Usage: python3 evaluate.py [--workers 8]
"""
import argparse
import json
import math
import os
import time
from multiprocessing import Pool

import corridor as C
import controllers as K
import simulator as S

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")
T_CRIT_9 = 2.262  # two-sided 5 % critical value of Student's t, 9 degrees of freedom

CONTROLLERS = ["webster", "ga_fixed", "fuzzy_hand", "ga_fuzzy"]
LABELS = {"webster": "Webster fixed-time", "ga_fixed": "GA-tuned fixed-time",
          "fuzzy_hand": "Fuzzy (hand-tuned)", "ga_fuzzy": "GA-tuned fuzzy (proposed)"}
METRICS = ["avg_delay", "avg_stops", "avg_delay_arterial_origin", "avg_delay_side_origin",
           "residual_queued", "exited"]


def load_best(kind):
    runs = json.load(open(os.path.join(RESULTS, f"ga_{kind}.json")))
    best = min(runs, key=lambda r: r["best_fitness"])
    return best["best_genome"], runs


def make_controller(name, scenario, genomes):
    if name == "webster":
        return K.webster_plan(scenario)
    if name == "ga_fixed":
        return K.decode_fixed(genomes["fixed"])
    if name == "fuzzy_hand":
        return K.FuzzyController(K.HAND_FUZZY)
    if name == "ga_fuzzy":
        return K.FuzzyController(genomes["fuzzy"])
    if name == "ga_fuzzy_mixed":
        return K.FuzzyController(genomes["fuzzy_mixed"])
    if name == "ga_fixed_mixed":
        return K.decode_fixed(genomes["fixed_mixed"])
    if name.startswith("fuzzy_genome:"):
        return K.FuzzyController(genomes["extra"][int(name.split(":")[1])])
    raise ValueError(name)


def scenario_by_spec(spec):
    if isinstance(spec, str):
        return C.SCENARIOS[spec]
    _, m = spec  # ("scaled", multiplier) of the moderate scenario
    return C.Scenario(f"moderate_x{m:.2f}", f"Moderate x {m:.2f}", 1500 * m, 1300 * m,
                      [(nb * m, sb * m) for nb, sb in C._MOD_SIDE])


def job(task):
    ctrl_name, spec, seed, genomes, horizon = task
    sc = scenario_by_spec(spec)
    res = S.simulate(sc, make_controller(ctrl_name, sc, genomes), seed, horizon=horizon)
    return {k: res[k] for k in METRICS}


def stats(xs):
    n = len(xs)
    mean = sum(xs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return {"mean": mean, "sd": sd, "min": min(xs), "max": max(xs), "n": n}


def paired(a, b):
    """Paired comparison of b against a (negative diff = b better)."""
    d = [y - x for x, y in zip(a, b)]
    s = stats(d)
    t = s["mean"] / (s["sd"] / math.sqrt(s["n"])) if s["sd"] > 0 else float("-inf")
    return {"mean_diff": s["mean"], "sd_diff": s["sd"], "t": t,
            "significant_5pct": abs(t) > T_CRIT_9, "wins": sum(1 for x in d if x < 0)}


def record_trace(scenario_name, ctrl_name, genomes, seed=1):
    sc = C.SCENARIOS[scenario_name]
    ctrl = make_controller(ctrl_name, sc, genomes)
    res = S.simulate(sc, ctrl, seed, record=True)
    tr = res["trace"]
    return {"phase": tr["phase"], "queues": tr["queues"], "total_queued": tr["total_queued"],
            "avg_delay": res["avg_delay"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args()
    t0 = time.time()

    fuzzy_best, fuzzy_runs = load_best("fuzzy")
    fixed_best, fixed_runs = load_best("fixed")
    genomes = {"fuzzy": fuzzy_best, "fixed": fixed_best,
               "extra": [r["best_genome"] for r in fuzzy_runs]}
    out = {"genomes": {"ga_fuzzy": fuzzy_best, "ga_fixed": fixed_best, "fuzzy_hand": K.HAND_FUZZY},
           "decoded": {"ga_fuzzy": K.decode_fuzzy(fuzzy_best), "fuzzy_hand": K.decode_fuzzy(K.HAND_FUZZY),
                       "ga_fixed": K.decode_fixed(fixed_best).describe()},
           "webster_plans": {n: K.webster_plan(sc).describe() for n, sc in C.SCENARIOS.items()},
           "test_seeds": list(C.TEST_SEEDS)}

    with Pool(args.workers) as pool:
        # ---- 1. main comparison
        tasks = [(c, s, seed, genomes, C.DETECTION_HORIZON)
                 for s in C.SCENARIOS for c in CONTROLLERS for seed in C.TEST_SEEDS]
        flat = pool.map(job, tasks)
        raw = {}
        for (c, s, seed, _, _), r in zip(tasks, flat):
            raw.setdefault(s, {}).setdefault(c, []).append(r)
        main_tab = {}
        for s in C.SCENARIOS:
            main_tab[s] = {}
            for c in CONTROLLERS:
                main_tab[s][c] = {m: stats([r[m] for r in raw[s][c]]) for m in METRICS}
                main_tab[s][c]["per_seed_delay"] = [r["avg_delay"] for r in raw[s][c]]
            web = main_tab[s]["webster"]["per_seed_delay"]
            for c in CONTROLLERS[1:]:
                main_tab[s][c]["vs_webster"] = paired(web, main_tab[s][c]["per_seed_delay"])
                main_tab[s][c]["improvement_pct"] = 100.0 * (1 - main_tab[s][c]["avg_delay"]["mean"]
                                                             / main_tab[s]["webster"]["avg_delay"]["mean"])
            main_tab[s]["ga_fuzzy"]["vs_ga_fixed"] = paired(main_tab[s]["ga_fixed"]["per_seed_delay"],
                                                            main_tab[s]["ga_fuzzy"]["per_seed_delay"])
        out["main"] = main_tab
        print(f"main comparison done ({time.time() - t0:.0f}s)", flush=True)

        # ---- 2. robustness of the GA: every run's best genome on the test seeds
        rob = {}
        for s in ("peak_build", "peak", "moderate"):
            per_run = []
            for i in range(len(fuzzy_runs)):
                rs = pool.map(job, [(f"fuzzy_genome:{i}", s, seed, genomes, C.DETECTION_HORIZON)
                                    for seed in C.TEST_SEEDS])
                per_run.append(sum(r["avg_delay"] for r in rs) / len(rs))
            rob[s] = {"per_run_test_delay": per_run, "summary": stats(per_run)}
        out["ga_run_robustness"] = rob
        out["ga_training"] = {
            "fuzzy": {"per_run_best": [r["best_fitness"] for r in fuzzy_runs],
                      "summary": stats([r["best_fitness"] for r in fuzzy_runs]),
                      "seconds": [r["seconds"] for r in fuzzy_runs],
                      "evaluations": fuzzy_runs[0]["history"][-1]["evaluations"]},
            "fixed": {"per_run_best": [r["best_fitness"] for r in fixed_runs],
                      "summary": stats([r["best_fitness"] for r in fixed_runs]),
                      "seconds": [r["seconds"] for r in fixed_runs]},
            "webster_training": stats([job(("webster", C.TRAINING_SCENARIO, sd, genomes, C.DETECTION_HORIZON))["avg_delay"]
                                       for sd in C.TRAINING_SEEDS]),
            "hand_fuzzy_training": stats([job(("fuzzy_hand", C.TRAINING_SCENARIO, sd, genomes, C.DETECTION_HORIZON))["avg_delay"]
                                          for sd in C.TRAINING_SEEDS]),
        }
        print(f"robustness done ({time.time() - t0:.0f}s)", flush=True)

        # ---- 3. demand sweep
        sweep = {}
        mults = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]
        seeds = C.TEST_SEEDS[:5]
        for c in ("webster", "ga_fixed", "ga_fuzzy"):
            sweep[c] = []
            for m in mults:
                rs = pool.map(job, [(c, ("scaled", m), sd, genomes, C.DETECTION_HORIZON) for sd in seeds])
                sweep[c].append(sum(r["avg_delay"] for r in rs) / len(rs))
        out["demand_sweep"] = {"multipliers": mults, "delay": sweep, "seeds": list(seeds)}

        # ---- 4. detection-horizon sensitivity (GA fuzzy, peak_build)
        hs = [0, 3, 7, 12, 20]
        out["horizon_sensitivity"] = {"horizons": hs, "delay": [
            stats([r["avg_delay"] for r in pool.map(job, [("ga_fuzzy", "peak_build", sd, genomes, h)
                                                          for sd in C.TEST_SEEDS])])["mean"] for h in hs]}
        print(f"sweeps done ({time.time() - t0:.0f}s)", flush=True)

        # ---- 4b. extension: controllers trained on a mixture of light/moderate/peak hours
        if os.path.exists(os.path.join(RESULTS, "ga_fuzzy_mixed.json")):
            genomes["fuzzy_mixed"], fz_mixed_runs = load_best("fuzzy_mixed")
            genomes["fixed_mixed"], fx_mixed_runs = load_best("fixed_mixed")
            mixed = {"genomes": {"ga_fuzzy_mixed": genomes["fuzzy_mixed"], "ga_fixed_mixed": genomes["fixed_mixed"]},
                     "decoded": {"ga_fuzzy_mixed": K.decode_fuzzy(genomes["fuzzy_mixed"]),
                                 "ga_fixed_mixed": K.decode_fixed(genomes["fixed_mixed"]).describe()},
                     "training_fitness": {"fuzzy": [r["best_fitness"] for r in fz_mixed_runs],
                                          "fixed": [r["best_fitness"] for r in fx_mixed_runs]},
                     "scenarios": {}}
            for s in C.SCENARIOS:
                web = main_tab[s]["webster"]["per_seed_delay"]
                mixed["scenarios"][s] = {}
                for c in ("ga_fuzzy_mixed", "ga_fixed_mixed"):
                    rs = pool.map(job, [(c, s, sd, genomes, C.DETECTION_HORIZON) for sd in C.TEST_SEEDS])
                    per = [r["avg_delay"] for r in rs]
                    mixed["scenarios"][s][c] = {"avg_delay": stats(per), "vs_webster": paired(web, per),
                                                "improvement_pct": 100.0 * (1 - stats(per)["mean"]
                                                                            / main_tab[s]["webster"]["avg_delay"]["mean"])}
            out["mixed_training"] = mixed
            print(f"mixed-training evaluation done ({time.time() - t0:.0f}s)", flush=True)

    # ---- 5. threshold sensitivity (theta), serial, peak_build
    theta_vals = [0.4, 0.5, 0.6, 0.7, 0.75, 0.8]
    th = []
    for v in theta_vals:
        g = list(fuzzy_best)
        g[6] = v
        th.append(stats([S.simulate(C.SCENARIOS["peak_build"], K.FuzzyController(g), sd)["avg_delay"]
                         for sd in C.TEST_SEEDS[:5]])["mean"])
    out["theta_sensitivity"] = {"theta": theta_vals, "delay": th, "tuned_theta": fuzzy_best[6]}

    # ---- 6. inference timing (uncached), real-time feasibility
    ctrl = K.FuzzyController(fuzzy_best)
    n = 0
    t1 = time.perf_counter()
    for g in range(0, 41):
        for r in range(0, 51):
            ctrl.fis.infer(g / 2.0, r / 2.0)
            n += 1
    out["inference_ms"] = 1000.0 * (time.perf_counter() - t1) / n

    # ---- 7. GA mutation-size sensitivity (training fitness of separate runs)
    sig = {"sigma": [], "mean": [], "sd": [], "runs": []}
    for value, tag in ((0.05, "_sigma0.05"), (0.15, ""), (0.30, "_sigma0.30")):
        path = os.path.join(RESULTS, f"ga_fuzzy{tag}.json")
        if os.path.exists(path):
            fits = [r["best_fitness"] for r in json.load(open(path))]
            s = stats(fits)
            sig["sigma"].append(value)
            sig["mean"].append(s["mean"])
            sig["sd"].append(s["sd"])
            sig["runs"].append(len(fits))
    out["sigma_sensitivity"] = sig

    # ---- 8. traces for plots and the live demo
    out_traces = {c: record_trace("peak_build", c, genomes) for c in ("webster", "ga_fixed", "ga_fuzzy")}
    with open(os.path.join(RESULTS, "traces_peak_build_seed1.json"), "w") as f:
        json.dump(out_traces, f)

    with open(os.path.join(RESULTS, "evaluation.json"), "w") as f:
        json.dump(out, f, indent=1)
    write_tables(out)
    print(f"all done in {time.time() - t0:.0f}s")


def write_tables(out):
    lines = ["# Test results (10 unseen seeds per scenario)\n",
             "| Scenario | Controller | Avg delay (s/veh) | sd | Stops/veh | Side-origin delay | Improvement vs Webster | Paired t | Wins/10 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s, sc in C.SCENARIOS.items():
        for c in CONTROLLERS:
            r = out["main"][s][c]
            imp = f"{r['improvement_pct']:+.1f} %" if "improvement_pct" in r else "-"
            pt = f"{r['vs_webster']['t']:.2f}" if "vs_webster" in r else "-"
            wins = str(r["vs_webster"]["wins"]) if "vs_webster" in r else "-"
            lines.append(f"| {sc.label} | {LABELS[c]} | {r['avg_delay']['mean']:.2f} | {r['avg_delay']['sd']:.2f} | "
                         f"{r['avg_stops']['mean']:.2f} | {r['avg_delay_side_origin']['mean']:.2f} | {imp} | {pt} | {wins} |")
    with open(os.path.join(RESULTS, "tables.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
