#!/usr/bin/env python3
"""
Experiments for the grounded direct argumentation mechanism.

For every p in {0.15, 0.25, 0.35} generate N random instances (default 1000):
    * n ~ Uniform{6, 7, 8} arguments,
    * each ordered pair (a, b) -- self-attacks included unless --no-self-attacks --
      is an attack with probability p,
    * each argument is given to one of 3 agents uniformly at random.
For each instance record
    * strategyproof?             (exhaustive Theorem 5.3 check)
    * Theorem 5.4 condition?     (odd walk -- primary; odd simple path -- secondary)
and report
    Q1  fraction strategyproof per p
    Q2  instances that satisfy the Thm 5.4 condition but are NOT strategyproof
    Q3  instances that are strategyproof although the condition fails (+ why)

Outputs: results/instances.csv, results/summary.json, results/q2_instances.json,
results/q3_examples.json, results/plots/*.png (if matplotlib is installed),
and a printed summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import time
from collections import Counter, defaultdict

from argumentation.framework import fmt_set
from argumentation.strategic import analyse_instance

PS = (0.15, 0.25, 0.35)
N_AGENTS = 3
AGENT_NAMES = ("A", "B", "C")


def random_instance(rng: random.Random, p: float, self_attacks: bool = True):
    n = rng.choice((6, 7, 8))
    args = [f"a{k}" for k in range(1, n + 1)]
    attacks = sorted((x, y) for x in args for y in args
                     if (self_attacks or x != y) and rng.random() < p)
    types = {name: set() for name in AGENT_NAMES}
    for a in args:
        types[rng.choice(AGENT_NAMES)].add(a)
    return n, args, attacks, types


def cat_of(res):
    """Q3 category label, e.g. 'compensated/source-itself-lost' ('' if not a Q3 instance)."""
    d = res.get("diagnosis")
    if not d:
        return ""
    return d["category"] + ("/" + d["subcategory"] if d.get("subcategory") else "")


def edges_str(attacks):
    return " ".join(f"{x}->{y}" for x, y in attacks)


def types_str(types):
    return "; ".join(f"{k}={fmt_set(v)}" for k, v in types.items())


def describe(inst):
    """JSON-friendly description of an instance + its analysis."""
    d = {
        "id": inst["id"], "p": inst["p"], "n": inst["n"],
        "attacks": [f"{x}->{y}" for x, y in inst["attacks"]],
        "types": {k: sorted(v, key=lambda s: int(s[1:])) for k, v in inst["types"].items()},
        "strategyproof": inst["res"]["strategyproof"],
        "cond_walk": inst["res"]["cond_walk"],
        "cond_simple": inst["res"]["cond_simple"],
        "truthful_outcome": fmt_set(inst["res"]["truthful_outcome"]),
        "violations_walk": [f"{ag}: {a}~>{b}" for (ag, a, b) in inst["res"]["violations_walk"]],
        "violations_simple": [f"{ag}: {a}~>{b}" for (ag, a, b) in inst["res"]["violations_simple"]],
    }
    ce = inst["res"]["counterexample"]
    if ce:
        d["manipulation"] = {
            "agent": ce["agent"],
            "others_reveal": fmt_set(ce["others_reveal"]),
            "hidden": fmt_set(ce["hidden"]),
            "truthful_outcome": fmt_set(ce["truthful_outcome"]),
            "truthful_utility": ce["truthful_utility"],
            "manipulated_outcome": fmt_set(ce["better_outcome"]),
            "manipulated_utility": ce["better_utility"],
        }
    if "diagnosis" in inst["res"]:
        d["diagnosis"] = inst["res"]["diagnosis"]
    return d


def run(n_instances: int, seed: int, self_attacks: bool, outdir: str, quiet: bool = False,
        plots: bool = True):
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    all_instances = []
    t0 = time.time()
    for p in PS:
        for k in range(n_instances):
            n, args, attacks, types = random_instance(rng, p, self_attacks)
            res = analyse_instance(attacks, types, arguments=args)
            all_instances.append({"id": f"p{p}-{k:04d}", "p": p, "n": n, "attacks": attacks,
                                  "types": types, "res": res})
        if not quiet:
            print(f"  p={p}: {n_instances} instances done ({time.time() - t0:.1f}s)")

    # ---------------- CSV of every instance ----------------
    with open(os.path.join(outdir, "instances.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "p", "n", "n_attacks", "attacks", "types", "strategyproof",
                    "thm54_walk", "thm54_simple", "truthful_outcome", "manipulating_agent",
                    "hidden", "q3_category"])
        for inst in all_instances:
            r = inst["res"]
            ce = r["counterexample"]
            w.writerow([inst["id"], inst["p"], inst["n"], len(inst["attacks"]),
                        edges_str(inst["attacks"]), types_str(inst["types"]),
                        int(r["strategyproof"]), int(r["cond_walk"]), int(r["cond_simple"]),
                        fmt_set(r["truthful_outcome"]),
                        ce["agent"] if ce else "", fmt_set(ce["hidden"]) if ce else "",
                        cat_of(r)])

    # ---------------- aggregate ----------------
    summary = {"config": {"instances_per_p": n_instances, "seed": seed, "self_attacks": self_attacks,
                          "agents": N_AGENTS, "n_args": [6, 7, 8], "p_values": list(PS)},
               "per_p": {}, "per_p_n": {}}
    q2_walk, q2_simple, q3 = [], [], []
    for p in PS:
        insts = [i for i in all_instances if i["p"] == p]
        N = len(insts)
        sp = sum(i["res"]["strategyproof"] for i in insts)
        cw = sum(i["res"]["cond_walk"] for i in insts)
        cs = sum(i["res"]["cond_simple"] for i in insts)
        both = Counter((i["res"]["cond_walk"], i["res"]["strategyproof"]) for i in insts)
        q2w = [i for i in insts if i["res"]["cond_walk"] and not i["res"]["strategyproof"]]
        q2s = [i for i in insts if i["res"]["cond_simple"] and not i["res"]["strategyproof"]]
        q3p = [i for i in insts if i["res"]["strategyproof"] and not i["res"]["cond_walk"]]
        q2_walk += q2w
        q2_simple += q2s
        q3 += q3p
        cats = Counter(cat_of(i["res"]) for i in q3p)
        summary["per_p"][str(p)] = {
            "instances": N,
            "strategyproof": sp, "frac_strategyproof": round(sp / N, 4),
            "cond_walk": cw, "frac_cond_walk": round(cw / N, 4),
            "cond_simple": cs, "frac_cond_simple": round(cs / N, 4),
            "cond_and_sp": both[(True, True)], "cond_not_sp": both[(True, False)],
            "notcond_sp": both[(False, True)], "notcond_not_sp": both[(False, False)],
            "q2_walk_count": len(q2w), "q2_simple_count": len(q2s),
            "q3_count": len(q3p), "q3_categories": dict(cats),
            "mean_attacks": round(sum(len(i["attacks"]) for i in insts) / N, 2),
        }
        per_n = defaultdict(lambda: [0, 0])
        for i in insts:
            per_n[i["n"]][0] += 1
            per_n[i["n"]][1] += i["res"]["strategyproof"]
        summary["per_p_n"][str(p)] = {str(n): {"instances": a, "strategyproof": b,
                                               "frac": round(b / a, 4)}
                                      for n, (a, b) in sorted(per_n.items())}
    summary["total"] = {
        "instances": len(all_instances),
        "q2_walk_count": len(q2_walk),
        "q2_simple_count": len(q2_simple),
        "q3_count": len(q3),
        "q3_categories": dict(Counter(cat_of(i["res"]) for i in q3)),
        "runtime_sec": round(time.time() - t0, 1),
    }

    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(outdir, "q2_instances.json"), "w") as f:
        json.dump({"walk_reading": [describe(i) for i in q2_walk],
                   "simple_path_reading": [describe(i) for i in q2_simple]}, f, indent=2)
    # Q3: keep up to 5 examples per category (smallest first) + all ids
    by_cat = defaultdict(list)
    for i in q3:
        by_cat[cat_of(i["res"])].append(i)
    q3_out = {}
    for cat, lst in by_cat.items():
        lst.sort(key=lambda i: (i["n"], len(i["attacks"])))
        q3_out[cat] = {"count": len(lst), "examples": [describe(i) for i in lst[:5]],
                       "ids": [i["id"] for i in lst]}
    with open(os.path.join(outdir, "q3_examples.json"), "w") as f:
        json.dump(q3_out, f, indent=2)

    if not quiet:
        print_summary(summary)
    if plots:
        save_plots(all_instances, outdir, self_attacks, quiet)
    return summary, all_instances


def save_plots(all_instances, outdir, self_attacks, quiet=False):
    """Save matplotlib plots into <outdir>/plots/ (skipped if matplotlib is not installed)."""
    try:
        from plots import make_plots, rows_from_instances
    except ImportError:
        if not quiet:
            print("\n(matplotlib not installed -- plots skipped; use .venv/bin/python or "
                  "`pip install matplotlib`)")
        return []
    label = "self-attacks allowed" if self_attacks else "no self-attacks"
    paths = make_plots(rows_from_instances(all_instances), outdir, label)
    if not quiet:
        print(f"\nplots saved to {os.path.join(outdir, 'plots')}/: "
              + ", ".join(os.path.basename(p) for p in paths))
    return paths


def print_summary(summary):
    print()
    print("Q1 -- fraction of instances that are strategyproof")
    print(f"{'p':>6} {'N':>6} {'SP':>6} {'frac SP':>8} {'cond(walk)':>11} {'cond(simple)':>13}")
    for p, s in summary["per_p"].items():
        print(f"{p:>6} {s['instances']:>6} {s['strategyproof']:>6} {s['frac_strategyproof']:>8.3f}"
              f" {s['frac_cond_walk']:>11.3f} {s['frac_cond_simple']:>13.3f}")
    print()
    print("Contingency (Thm 5.4 condition [walk] x strategyproof)")
    print(f"{'p':>6} {'cond&SP':>8} {'cond&!SP':>9} {'!cond&SP':>9} {'!cond&!SP':>10}")
    for p, s in summary["per_p"].items():
        print(f"{p:>6} {s['cond_and_sp']:>8} {s['cond_not_sp']:>9} {s['notcond_sp']:>9} {s['notcond_not_sp']:>10}")
    t = summary["total"]
    print()
    print(f"Q2 -- condition holds but NOT strategyproof: walk reading = {t['q2_walk_count']}, "
          f"simple-path reading = {t['q2_simple_count']}")
    print(f"Q3 -- strategyproof although condition fails: {t['q3_count']}")
    for cat, c in sorted(t["q3_categories"].items(), key=lambda kv: -kv[1]):
        print(f"       {cat:<20} {c}")
    print(f"\n(total {t['instances']} instances, {t['runtime_sec']}s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-instances", type=int, default=1000, help="instances per value of p (default 1000)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-self-attacks", action="store_true", help="forbid attacks a->a")
    ap.add_argument("--out", default="results", help="output directory")
    ap.add_argument("--no-plots", action="store_true", help="do not save matplotlib plots")
    a = ap.parse_args()
    print(f"Running {a.n_instances} instances per p, seed={a.seed}, self-attacks={not a.no_self_attacks}")
    run(a.n_instances, a.seed, not a.no_self_attacks, a.out, plots=not a.no_plots)


if __name__ == "__main__":
    main()
