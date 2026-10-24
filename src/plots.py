"""Figures for the report (matplotlib is used ONLY here, for plotting results;
the fuzzy system, GA and simulator do not use it)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

import corridor as C
import controllers as K
from fuzzy import build_signal_fis, left_shoulder, right_shoulder, triangle

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")

COL = {"ga_fuzzy": "#2a78d6", "ga_fixed": "#eb6834", "fuzzy_hand": "#1baf7a", "webster": "#8a8984"}
LAB = {"webster": "Webster fixed-time", "ga_fixed": "GA-tuned fixed-time",
       "fuzzy_hand": "Fuzzy (hand-tuned)", "ga_fuzzy": "GA-tuned fuzzy (proposed)"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"], "font.size": 10,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def save(fig, name):
    fig.savefig(os.path.join(FIG, name))
    plt.close(fig)


# ------------------------------------------------------------------ diagrams

def box(ax, x, y, w, h, text, fc="#eef4fc", ec="#2a78d6", fs=9, round_=True):
    style = "round,pad=0.02,rounding_size=0.08" if round_ else "square,pad=0.02"
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=style, fc=fc, ec=ec, lw=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK, wrap=True)


def arrow(ax, x1, y1, x2, y2, text=None, side="right"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1))
    if text:
        ax.text((x1 + x2) / 2 + (0.08 if side == "right" else -0.08), (y1 + y2) / 2, text,
                fontsize=8, color=INK2, ha="left" if side == "right" else "right", va="center")


def diamond(ax, x, y, w, h, text, fs=8.5):
    ax.add_patch(plt.Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)],
                             fc="#fff4e5", ec="#eb6834", lw=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, color=INK)


def fig_corridor():
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_xlim(-0.6, 8.6)
    ax.set_ylim(-1.95, 1.5)
    ax.axis("off")
    ax.add_patch(Rectangle((-0.5, -0.22), 9.0, 0.44, fc="#d9d8d3", ec="none"))
    xs = [1.0, 4.2, 7.6]
    for i, x in enumerate(xs):
        ax.add_patch(Rectangle((x - 0.13, -1.4), 0.26, 2.8, fc="#d9d8d3", ec="none"))
        ax.add_patch(Rectangle((x - 0.32, -0.32), 0.64, 0.64, fc="#fcfcfb", ec=INK2, lw=1))
        ax.text(x, 0, f"J{i + 1}", ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(x + 0.2, 1.3, "SB", fontsize=8, color=INK2)
        ax.text(x + 0.2, -1.35, "NB", fontsize=8, color=INK2)
    ax.annotate("", xy=(4.0, 0.4), xytext=(1.3, 0.4), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text(2.6, 0.55, f"{C.LINK_LENGTH[0]:.0f} m  ({C.LINK_TT[0]} s)", ha="center", fontsize=8.5)
    ax.annotate("", xy=(7.4, 0.4), xytext=(4.4, 0.4), arrowprops=dict(arrowstyle="<->", color=INK2))
    ax.text(5.9, 0.55, f"{C.LINK_LENGTH[1]:.0f} m  ({C.LINK_TT[1]} s)", ha="center", fontsize=8.5)
    ax.annotate("", xy=(0.6, -0.65), xytext=(-0.5, -0.65), arrowprops=dict(arrowstyle="-|>", color="#2a78d6"))
    ax.text(-0.5, -0.9, "EB entry", fontsize=8, color="#2a78d6")
    ax.annotate("", xy=(8.0, 0.75), xytext=(8.6, 0.75), arrowprops=dict(arrowstyle="-|>", color="#2a78d6"))
    ax.text(7.95, 0.92, "WB entry", fontsize=8, color="#2a78d6")
    ax.text(4.2, -1.85, "Arterial: 2 lanes/direction, 3600 veh/h saturation   |   "
            "Side streets: 1 lane/direction, 1800 veh/h", ha="center", fontsize=8, color=INK2)
    save(fig, "fig_corridor.png")


def fig_architecture():
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    box(ax, 1.7, 4.6, 2.8, 0.8, "Fitness J(x) = mean delay\non training simulations")
    box(ax, 5.6, 4.6, 2.8, 0.8, "Real-coded GA\n(ga.py)", fc="#fff4e5", ec="#eb6834")
    box(ax, 1.7, 2.7, 2.8, 0.9, "Corridor simulator\n(simulator.py)")
    box(ax, 5.6, 2.7, 2.8, 0.9, "Fuzzy controller\n(fuzzy.py, controllers.py)", fc="#e8f7f0", ec="#1baf7a")
    box(ax, 8.7, 2.7, 2.2, 0.9, "Baselines: Webster,\nGA fixed-time")
    box(ax, 1.7, 0.8, 2.8, 0.8, "Demand scenarios, seeds\n(corridor.py)")
    box(ax, 6.6, 0.8, 5.4, 0.8, "Evaluation: 10 unseen seeds x 6 scenarios\n-> tables, figures, demo (evaluate.py)")
    arrow(ax, 3.1, 4.6, 4.2, 4.6)
    ax.text(3.65, 4.75, "J(x)", fontsize=8, color=INK2, ha="center")
    arrow(ax, 5.6, 4.2, 5.6, 3.15, "genome x: break points,\ntheta, min/max green")
    arrow(ax, 4.2, 2.85, 3.1, 2.85)
    arrow(ax, 3.1, 2.55, 4.2, 2.55)
    ax.text(3.65, 3.0, "queues, arrivals", fontsize=7.5, color=INK2, ha="center")
    ax.text(3.65, 2.25, "end green?", fontsize=7.5, color=INK2, ha="center")
    arrow(ax, 1.7, 3.15, 1.7, 4.2, "average delay", side="left")
    arrow(ax, 1.7, 1.2, 1.7, 2.25, "vehicles", side="left")
    arrow(ax, 5.6, 2.25, 5.6, 1.2, "tuned controller")
    arrow(ax, 8.7, 2.25, 8.7, 1.2)
    save(fig, "fig_architecture.png")


def fig_flow_ga():
    fig, ax = plt.subplots(figsize=(4.6, 7.2))
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 12)
    ax.axis("off")
    ys = [11.3, 10.1, 8.9, 7.7, 6.5, 5.3, 4.1, 2.6, 1.0]
    texts = ["Start", "Initialise population P (N=30):\nhand-tuned genome + random genomes",
             "Evaluate fitness: simulate each genome\non 3 training seeds -> mean delay",
             "Tournament selection (k = 3)", "SBX crossover (pc = 0.9, eta_c = 15)",
             "Gaussian mutation (pm = 1/n,\nsigma shrinks 0.15 -> 0.03)",
             "Evaluate children; keep 2 elites\n-> next generation"]
    box(ax, 3, ys[0], 2.0, 0.6, texts[0], fc="#f3f3f1", ec=INK2)
    for y, t in zip(ys[1:7], texts[1:]):
        box(ax, 3, y, 4.8, 0.85, t, fs=8.5)
    diamond(ax, 3, ys[7], 3.6, 1.3, "generation < G (=40)?")
    box(ax, 3, ys[8], 4.4, 0.8, "Return best genome\n(tuned fuzzy controller)", fc="#f3f3f1", ec=INK2)
    for a, b in zip(ys[:7], ys[1:8]):
        arrow(ax, 3, a - 0.43 if a != ys[0] else a - 0.3, 3, b + (0.65 if b == ys[7] else 0.43))
    arrow(ax, 3, ys[7] - 0.65, 3, ys[8] + 0.4, "no")
    ax.annotate("", xy=(5.4, ys[3]), xytext=(4.8, ys[7]),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1, connectionstyle="angle,angleA=0,angleB=90,rad=0"))
    ax.text(5.0, ys[7] + 0.2, "yes", fontsize=8, color=INK2)
    save(fig, "fig_flow_ga.png")


def fig_flow_controller():
    fig, ax = plt.subplots(figsize=(4.8, 7.6))
    ax.set_xlim(0, 6.4)
    ax.set_ylim(0, 12.6)
    ax.axis("off")
    box(ax, 3, 12.0, 3.4, 0.6, "Each second t, junction j\n(current phase p in green)", fc="#f3f3f1", ec=INK2, fs=8)
    diamond(ax, 3, 10.7, 3.4, 1.2, "elapsed < min green?")
    box(ax, 5.6, 10.7, 1.4, 0.6, "hold\ngreen", fs=8)
    diamond(ax, 3, 9.1, 3.4, 1.2, "elapsed >= max green?")
    box(ax, 3, 7.5, 4.6, 0.9, "Measure: G = max (queue + arriving in 7 s) / lanes\n"
        "on green;  R = max queue / lanes on red", fs=8)
    box(ax, 3, 6.1, 4.6, 0.8, "Fuzzify G, R (Low / Medium / High)", fs=8.5, fc="#e8f7f0", ec="#1baf7a")
    box(ax, 3, 4.9, 4.6, 0.8, "Fire 9 rules (min), aggregate (max)", fs=8.5, fc="#e8f7f0", ec="#1baf7a")
    box(ax, 3, 3.7, 4.6, 0.8, "Centroid -> switch urgency u in [0, 1]", fs=8.5, fc="#e8f7f0", ec="#1baf7a")
    diamond(ax, 3, 2.3, 3.0, 1.2, "u > theta ?")
    box(ax, 3, 0.7, 4.6, 0.8, "End green: 3 s amber + 1 s all-red,\nthen next phase green", fs=8.5,
        fc="#fff4e5", ec="#eb6834")
    arrow(ax, 3, 11.7, 3, 11.3)
    arrow(ax, 4.7, 10.7, 4.9, 10.7)
    ax.text(4.72, 11.0, "yes", fontsize=8, color=INK2)
    arrow(ax, 3, 10.1, 3, 9.7, "no")
    arrow(ax, 3, 8.5, 3, 7.95, "no")
    arrow(ax, 3, 7.05, 3, 6.5)
    arrow(ax, 3, 5.7, 3, 5.3)
    arrow(ax, 3, 4.5, 3, 4.1)
    arrow(ax, 3, 3.3, 3, 2.9)
    arrow(ax, 3, 1.7, 3, 1.1, "yes")
    ax.annotate("", xy=(0.5, 0.7), xytext=(1.3, 9.1),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=1.1, connectionstyle="angle,angleA=180,angleB=90,rad=0"))
    arrow(ax, 0.5, 0.7, 0.7, 0.7)
    ax.text(0.15, 9.3, "yes", fontsize=8, color=INK2)
    ax.annotate("", xy=(5.6, 10.4), xytext=(4.5, 2.3),
                arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.1, connectionstyle="angle,angleA=0,angleB=-90,rad=0"))
    ax.text(4.6, 2.5, "no", fontsize=8, color=INK2)
    save(fig, "fig_flow_controller.png")


# ------------------------------------------------------------------ fuzzy system

def mf_lines(points, xmax):
    a, b, c = points
    xs = [xmax * i / 400 for i in range(401)]
    return xs, [left_shoulder(x, a, b) for x in xs], [triangle(x, a, b, c) for x in xs], \
        [right_shoulder(x, b, c) for x in xs]


def fig_mfs(ev):
    hand = K.decode_fuzzy(K.HAND_FUZZY)
    tuned = ev["decoded"]["ga_fuzzy"]
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.4))
    for ax, key, xmax, title in ((axes[0], "g_points", 20, "Input 1: green demand (veh/lane)"),
                                 (axes[1], "r_points", 25, "Input 2: red queue (veh/lane)")):
        for params, ls, alpha in ((hand, "--", 0.55), (tuned, "-", 1.0)):
            xs, lo, me, hi = mf_lines(params[key], xmax)
            for ys, col in ((lo, "#2a78d6"), (me, "#1baf7a"), (hi, "#eb6834")):
                ax.plot(xs, ys, ls, color=col, lw=1.6, alpha=alpha)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(-0.03, 1.05)
        ax.set_ylabel("membership")
    ys = [i / 200 for i in range(201)]
    axes[2].plot(ys, [triangle(y, 0, 0, 0.5) for y in ys], color="#2a78d6", lw=1.6, label="Low")
    axes[2].plot(ys, [triangle(y, 0.25, 0.5, 0.75) for y in ys], color="#1baf7a", lw=1.6, label="Medium")
    axes[2].plot(ys, [triangle(y, 0.5, 1, 1) for y in ys], color="#eb6834", lw=1.6, label="High")
    axes[2].axvline(tuned["theta"], color=INK2, lw=1, ls=":")
    axes[2].text(tuned["theta"], 1.0, f" theta={tuned['theta']:.2f}", fontsize=7.5, color=INK2, va="top")
    axes[2].set_title("Output: switch urgency", fontsize=9)
    axes[0].plot([], [], "k--", alpha=0.55, label="hand-tuned")
    axes[0].plot([], [], "k-", label="GA-tuned")
    axes[0].legend(fontsize=7.5, loc="center right")
    axes[2].legend(fontsize=7.5, loc="center left")
    fig.tight_layout()
    save(fig, "fig_mfs.png")


def fig_surface(ev):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, key, title in ((axes[0], "fuzzy_hand", "Hand-tuned"), (axes[1], "ga_fuzzy", "GA-tuned")):
        p = ev["decoded"][key]
        fis = build_signal_fis(p["g_points"], p["r_points"])
        gs = [i * 0.5 for i in range(41)]
        rs = [i * 0.5 for i in range(51)]
        Z = [[fis.infer(g, r) for g in gs] for r in rs]
        im = ax.imshow(Z, origin="lower", extent=[0, 20, 0, 25], aspect="auto", cmap="Blues", vmin=0, vmax=0.85)
        ax.contour(gs, rs, Z, levels=[p["theta"]], colors=["#eb6834"], linewidths=1.6)
        ax.set_title(f"{title} (orange line: u = theta = {p['theta']:.2f})", fontsize=8.5)
        ax.set_xlabel("green demand G (veh/lane)")
        ax.grid(False)
    axes[0].set_ylabel("red queue R (veh/lane)")
    cb = fig.colorbar(im, ax=axes, shrink=0.9)
    cb.set_label("switch urgency u")
    save(fig, "fig_surface.png")


# ------------------------------------------------------------------ results

def fig_convergence(ev):
    fuzzy = json.load(open(os.path.join(RES, "ga_fuzzy.json")))
    fixed = json.load(open(os.path.join(RES, "ga_fixed.json")))
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    for runs, key in ((fuzzy, "ga_fuzzy"), (fixed, "ga_fixed")):
        for r in runs:
            ax.plot([h["generation"] for h in r["history"]], [h["best"] for h in r["history"]],
                    color=COL[key], lw=0.8, alpha=0.35)
        gens = [h["generation"] for h in runs[0]["history"]]
        mean = [sum(r["history"][g]["best"] for r in runs) / len(runs) for g in range(len(gens))]
        ax.plot(gens, mean, color=COL[key], lw=2.2, label=f"{LAB[key]} (mean of {len(runs)} runs)")
    w = ev["ga_training"]["webster_training"]["mean"]
    ax.axhline(w, color=COL["webster"], lw=1.4, ls="--")
    ax.text(40, w + 0.6, f"Webster fixed-time {w:.1f} s", ha="right", fontsize=8, color=INK2)
    ax.set_ylim(25, max(w + 8, 50))
    ax.set_xlabel("generation")
    ax.set_ylabel("best fitness: mean delay (s/veh)")
    ax.legend(fontsize=8)
    save(fig, "fig_convergence.png")


def fig_delay_bars(ev):
    scen = list(C.SCENARIOS)
    ctrls = ["webster", "ga_fixed", "fuzzy_hand", "ga_fuzzy"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    w = 0.2
    for k, c in enumerate(ctrls):
        xs = [i + (k - 1.5) * w for i in range(len(scen))]
        m = [ev["main"][s][c]["avg_delay"]["mean"] for s in scen]
        sd = [ev["main"][s][c]["avg_delay"]["sd"] for s in scen]
        ax.bar(xs, m, w * 0.92, color=COL[c], label=LAB[c], yerr=sd, error_kw=dict(lw=0.8, ecolor=INK2, capsize=1.5))
        if c == "ga_fuzzy":
            for x, v in zip(xs, m):
                ax.text(x, v + 2.2, f"{v:.0f}", ha="center", fontsize=7, color=INK)
    ax.set_xticks(range(len(scen)))
    short = {"offpeak": "Off-peak", "moderate": "Moderate", "peak": "Peak\n(steady)",
             "peak_build": "Peak build-up\n(training)", "tidal": "Tidal\nshift", "side_surge": "Side-street\nsurge at J3"}
    ax.set_xticklabels([short[s] for s in scen], fontsize=8)
    ax.set_ylabel("average delay (s/veh)")
    ax.legend(fontsize=7.5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.13))
    save(fig, "fig_delay_bars.png")


def fig_seed_strip(ev):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=False)
    for ax, s in zip(axes, ("peak_build", "peak")):
        ctrls = ["webster", "ga_fixed", "fuzzy_hand", "ga_fuzzy"]
        for k, c in enumerate(ctrls):
            ys = ev["main"][s][c]["per_seed_delay"]
            xs = [k + (i - 4.5) * 0.03 for i in range(len(ys))]
            ax.scatter(xs, ys, s=16, color=COL[c], edgecolor="white", linewidth=0.6, zorder=3)
            mean = sum(ys) / len(ys)
            ax.plot([k - 0.25, k + 0.25], [mean, mean], color=INK, lw=1.4)
        web = ev["main"][s]["webster"]["per_seed_delay"]
        fz = ev["main"][s]["ga_fuzzy"]["per_seed_delay"]
        for a, b in zip(web, fz):
            ax.plot([0, 3], [a, b], color=GRID, lw=0.6, zorder=1)
        ax.set_xticks(range(4))
        ax.set_xticklabels(["Webster", "GA fixed", "Fuzzy\nhand", "GA fuzzy"], fontsize=8)
        ax.set_title(C.SCENARIOS[s].label, fontsize=9)
        ax.set_ylabel("average delay (s/veh)")
    save(fig, "fig_seed_strip.png")


def fig_demand_sweep(ev):
    d = ev["demand_sweep"]
    fig, ax = plt.subplots(figsize=(6.0, 3.0))
    for c in ("webster", "ga_fixed", "ga_fuzzy"):
        ax.plot(d["multipliers"], d["delay"][c], "-o", color=COL[c], lw=2, ms=4.5, label=LAB[c])
    ax.axvline(1.0, color=GRID, lw=1)
    ax.set_xlabel("demand multiplier (x moderate scenario)")
    ax.set_ylabel("average delay (s/veh)")
    ax.legend(fontsize=8)
    save(fig, "fig_demand_sweep.png")


def smooth(xs, k=60):
    out, acc = [], 0.0
    for i, x in enumerate(xs):
        acc += x
        if i >= k:
            acc -= xs[i - k]
        out.append(acc / min(i + 1, k))
    return out


def fig_timeseries():
    tr = json.load(open(os.path.join(RES, "traces_peak_build_seed1.json")))
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True)
    for c in ("webster", "ga_fixed", "ga_fuzzy"):
        ys = smooth(tr[c]["total_queued"])
        axes[0].plot([t / 60 for t in range(len(ys))], ys, color=COL[c], lw=1.6,
                     label=f"{LAB[c]} (avg delay {tr[c]['avg_delay']:.1f} s)")
    axes[0].set_ylabel("vehicles queued\n(whole corridor, 60 s mean)")
    axes[0].legend(fontsize=7.5)
    # green durations of the arterial phase at J2
    for c, mk in (("webster", "s"), ("ga_fuzzy", "o")):
        ph = [p[1] for p in tr[c]["phase"]]
        starts, durs, cur, n, t0 = [], [], None, 0, 0
        for t, p in enumerate(ph):
            if p != cur:
                if cur == 0:
                    starts.append(t0 / 60)
                    durs.append(n)
                cur, n, t0 = p, 1, t
            else:
                n += 1
        axes[1].plot(starts, durs, mk, color=COL[c], ms=3.5, label=LAB[c])
    axes[1].set_ylabel("J2 arterial green (s)")
    axes[1].set_xlabel("time (min)")
    axes[1].legend(fontsize=7.5)
    save(fig, "fig_timeseries.png")


def fig_sensitivity(ev):
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.5))
    th = ev["theta_sensitivity"]
    cap = 46
    shown = [min(v, cap) for v in th["delay"]]
    axes[0].plot(th["theta"], shown, "-o", color=COL["ga_fuzzy"], ms=4)
    for x, v in zip(th["theta"], th["delay"]):
        if v > cap:
            axes[0].annotate(f"{v:.0f} s (off scale)", xy=(x, cap), xytext=(x + 0.04, cap - 3),
                             fontsize=7.5, color=INK2, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    axes[0].set_ylim(28, cap + 1)
    axes[0].axvline(th["tuned_theta"], color=INK2, ls=":", lw=1)
    axes[0].set_xlabel("threshold theta")
    axes[0].set_ylabel("avg delay (s/veh)")
    axes[0].set_title("Switch threshold", fontsize=9)
    hz = ev["horizon_sensitivity"]
    axes[1].plot(hz["horizons"], hz["delay"], "-o", color=COL["ga_fuzzy"], ms=4)
    axes[1].set_xlabel("detection horizon (s)")
    axes[1].set_title("Look-ahead horizon", fontsize=9)
    sig = ev.get("sigma_sensitivity")
    if sig:
        xs = list(range(len(sig["sigma"])))
        axes[2].bar(xs, sig["mean"], 0.55, color=COL["ga_fuzzy"], yerr=sig["sd"],
                    error_kw=dict(lw=0.8, ecolor=INK2, capsize=2))
        axes[2].set_xticks(xs)
        axes[2].set_xticklabels([str(s) for s in sig["sigma"]])
        lo = min(sig["mean"]) - 2
        axes[2].set_ylim(lo, max(sig["mean"]) + 1.5)
        axes[2].set_xlabel("initial mutation sigma")
        axes[2].set_title("GA mutation size (training)", fontsize=9)
    fig.tight_layout()
    save(fig, "fig_sensitivity.png")


def main():
    os.makedirs(FIG, exist_ok=True)
    ev = json.load(open(os.path.join(RES, "evaluation.json")))
    fig_corridor()
    fig_architecture()
    fig_flow_ga()
    fig_flow_controller()
    fig_mfs(ev)
    fig_surface(ev)
    fig_convergence(ev)
    fig_delay_bars(ev)
    fig_seed_strip(ev)
    fig_demand_sweep(ev)
    fig_timeseries()
    fig_sensitivity(ev)
    print("figures written to", os.path.abspath(FIG))


if __name__ == "__main__":
    main()
