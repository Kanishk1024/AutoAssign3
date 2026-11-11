#!/usr/bin/env python3
"""
Plots for the strategic-argumentation experiments (needs matplotlib).

Called automatically at the end of `experiments.py`; can also rebuild the
plots of an existing results folder without re-running the experiment:

    python plots.py results
    python plots.py results_no_self_attacks

Writes <folder>/plots/*.png:
    q1_strategyproof_by_p.png   fraction strategyproof / condition-holds per p (95% Wilson CI)
    contingency_by_p.png        condition x strategyproof, 100%-stacked per p
    q3_reasons.png              why instances are SP although the condition fails
    sp_by_n.png                 fraction strategyproof vs number of arguments
    sp_vs_attacks.png           fraction strategyproof vs number of attacks
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, GREEN, RED, GREY, PURPLE = "#2563eb", "#d97706", "#16a34a", "#dc2626", "#9ca3af", "#9333ea"
P_COLORS = {"0.15": "#60a5fa", "0.25": "#2563eb", "0.35": "#1e3a8a"}

Q3_LABELS = {
    "compensated/source-itself-lost": "Hiding gains nothing on balance\n(hidden argument itself lost)",
    "compensated/other-own-argument-lost": "Hiding loses other own arguments\n(α6 effect, Ex. 5.11)",
    "hiding-never-helps": "Hiding never frees the target",
    "victim-never-in": "Target never accepted",
    "self-defeat-only": "Only self-attacking arguments",
    "walk-only": "Odd walk only (no simple path)",
}


def _style():
    plt.rcParams.update({
        "figure.dpi": 100, "savefig.dpi": 200, "savefig.bbox": "tight",
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
        "legend.frameon": False,
    })


def wilson(k: int, n: int, z: float = 1.96):
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 0.0
    phat = k / n
    den = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / den
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------------- #
# data normalisation (from memory or from instances.csv)
# ---------------------------------------------------------------------- #
def rows_from_instances(all_instances):
    from experiments import cat_of
    return [{"p": str(i["p"]), "n": i["n"], "n_attacks": len(i["attacks"]),
             "sp": bool(i["res"]["strategyproof"]), "cond": bool(i["res"]["cond_walk"]),
             "q3": cat_of(i["res"])} for i in all_instances]


def rows_from_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({"p": str(float(r["p"])), "n": int(r["n"]), "n_attacks": int(r["n_attacks"]),
                         "sp": r["strategyproof"] == "1", "cond": r["thm54_walk"] == "1",
                         "q3": r["q3_category"]})
    return rows


# ---------------------------------------------------------------------- #
# individual plots
# ---------------------------------------------------------------------- #
def plot_q1(rows, title_suffix, path):
    ps = sorted({r["p"] for r in rows}, key=float)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    w = 0.36
    for j, (key, label, color) in enumerate((("sp", "strategyproof (Thm 5.3)", BLUE),
                                             ("cond", "Thm 5.4 condition holds", ORANGE))):
        xs, ys, lo, hi = [], [], [], []
        for i, p in enumerate(ps):
            grp = [r for r in rows if r["p"] == p]
            k = sum(r[key] for r in grp)
            a, b = wilson(k, len(grp))
            xs.append(i + (j - 0.5) * w)
            ys.append(k / len(grp))
            lo.append(k / len(grp) - a)
            hi.append(b - k / len(grp))
        bars = ax.bar(xs, ys, w, color=color, label=label, yerr=[lo, hi], capsize=3,
                      error_kw={"elinewidth": 1, "ecolor": "#334155"})
        for x, y, e in zip(xs, ys, hi):
            ax.text(x, y + e + 0.015, f"{100 * y:.1f}%", ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(range(len(ps)), [f"p = {p}" for p in ps])
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel("fraction of instances")
    ax.set_title(f"Q1 · Strategyproof instances per attack probability{title_suffix}")
    ax.legend(loc="upper right")
    fig.savefig(path)
    plt.close(fig)


def plot_contingency(rows, title_suffix, path):
    ps = sorted({r["p"] for r in rows}, key=float)
    cats = [("cond ∧ SP", lambda r: r["cond"] and r["sp"], GREEN),
            ("cond ∧ ¬SP  (Q2)", lambda r: r["cond"] and not r["sp"], RED),
            ("¬cond ∧ SP  (Q3)", lambda r: (not r["cond"]) and r["sp"], BLUE),
            ("¬cond ∧ ¬SP", lambda r: (not r["cond"]) and not r["sp"], GREY)]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    left = [0.0] * len(ps)
    for label, f, color in cats:
        vals = []
        for p in ps:
            grp = [r for r in rows if r["p"] == p]
            vals.append(sum(1 for r in grp if f(r)) / len(grp))
        ax.barh(range(len(ps)), vals, left=left, color=color, label=label, height=0.6)
        for i, (l, v) in enumerate(zip(left, vals)):
            if v >= 0.05:
                ax.text(l + v / 2, i, f"{100 * v:.1f}%", ha="center", va="center", color="white", fontsize=8.5)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(range(len(ps)), [f"p = {p}" for p in ps])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Theorem 5.4 condition × strategyproofness{title_suffix}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=4, fontsize=8.5)
    fig.savefig(path)
    plt.close(fig)


def plot_q3(rows, title_suffix, path):
    q3 = [r for r in rows if r["q3"]]
    ps = sorted({r["p"] for r in rows}, key=float)
    tot = Counter(r["q3"] for r in q3)
    cats = [c for c, _ in tot.most_common()]
    fig, ax = plt.subplots(figsize=(6.4, 0.55 * len(cats) + 1.4))
    left = [0] * len(cats)
    for p in ps:
        cnt = Counter(r["q3"] for r in q3 if r["p"] == p)
        vals = [cnt[c] for c in cats]
        ax.barh(range(len(cats)), vals, left=left, color=P_COLORS.get(p, BLUE), label=f"p = {p}", height=0.62)
        left = [l + v for l, v in zip(left, vals)]
    for i, c in enumerate(cats):
        ax.text(left[i] + max(left) * 0.01, i, str(tot[c]), va="center", fontsize=9)
    ax.set_yticks(range(len(cats)), [Q3_LABELS.get(c, c) for c in cats], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, max(left) * 1.12 if left else 1)
    ax.set_xlabel("instances")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Q3 · Strategyproof although the condition fails ({len(q3)}){title_suffix}")
    ax.legend(loc="lower right")
    fig.savefig(path)
    plt.close(fig)


def plot_by_n(rows, title_suffix, path):
    ps = sorted({r["p"] for r in rows}, key=float)
    ns = sorted({r["n"] for r in rows})
    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    for p in ps:
        ys, lo, hi = [], [], []
        for n in ns:
            grp = [r for r in rows if r["p"] == p and r["n"] == n]
            k = sum(r["sp"] for r in grp)
            a, b = wilson(k, len(grp))
            y = k / len(grp) if grp else 0
            ys.append(y); lo.append(y - a); hi.append(b - y)
        ax.errorbar(ns, ys, yerr=[lo, hi], marker="o", capsize=3, color=P_COLORS.get(p, BLUE), label=f"p = {p}")
    ax.set_xticks(ns)
    ax.set_xlabel("number of arguments n")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel("fraction strategyproof")
    ax.set_title(f"Strategyproofness vs. graph size{title_suffix}")
    ax.legend()
    fig.savefig(path)
    plt.close(fig)


def plot_by_attacks(rows, title_suffix, path):
    by = defaultdict(list)
    for r in rows:
        by[r["n_attacks"]].append(r["sp"])
    xs = sorted(by)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax2 = ax.twinx()
    ax2.bar(xs, [len(by[x]) for x in xs], color=GREY, alpha=0.35, width=0.8, label="instances")
    ax2.set_ylabel("number of instances", color="#6b7280")
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    keep = [x for x in xs if len(by[x]) >= 10]
    ys = [sum(by[x]) / len(by[x]) for x in keep]
    ax.plot(keep, ys, marker="o", color=BLUE, label="fraction strategyproof (≥10 instances)")
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax.set_ylim(0, 1.02)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("number of attacks in the instance")
    ax.set_ylabel("fraction strategyproof")
    ax.set_title(f"Strategyproofness vs. number of attacks{title_suffix}")
    ax.legend(loc="upper right")
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------------- #
def make_plots(rows, outdir, label=""):
    """Write all plots for one results folder; returns list of file paths."""
    _style()
    pdir = os.path.join(outdir, "plots")
    os.makedirs(pdir, exist_ok=True)
    suffix = f"\n({label})" if label else ""
    jobs = [("q1_strategyproof_by_p.png", plot_q1), ("contingency_by_p.png", plot_contingency),
            ("q3_reasons.png", plot_q3), ("sp_by_n.png", plot_by_n), ("sp_vs_attacks.png", plot_by_attacks)]
    out = []
    for name, fn in jobs:
        path = os.path.join(pdir, name)
        fn(rows, suffix, path)
        out.append(path)
    return out


def label_for(outdir):
    try:
        with open(os.path.join(outdir, "summary.json")) as f:
            cfg = json.load(f)["config"]
        return "self-attacks allowed" if cfg.get("self_attacks", True) else "no self-attacks"
    except OSError:
        return ""


def main():
    folders = sys.argv[1:] or ["results"]
    for d in folders:
        rows = rows_from_csv(os.path.join(d, "instances.csv"))
        for p in make_plots(rows, d, label_for(d)):
            print("wrote", p)


if __name__ == "__main__":
    main()
