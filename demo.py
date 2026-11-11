#!/usr/bin/env python3
"""
Demonstration of the argumentation engine and the grounded direct
argumentation mechanism, using the examples of Weiss (ed.), *Multiagent
Systems* 2nd ed., Chapter 5.

    python3 demo.py            # full walk-through
    python3 demo.py --part 1   # only the argumentation engine
    python3 demo.py --part 2   # only strategic argumentation (+ mini experiment)
    python3 demo.py --no-pause # (default) run straight through; --pause waits for Enter
"""

import argparse
import random

from argumentation import (SEMANTICS, best_responses, check_theorem_53, check_theorem_54, fmt_set,
                           mechanism, utility)
from argumentation.book_examples import (example_5_10, example_5_11, exercise_1, exercise_2, fig_5_1,
                                         fig_5_2, fig_5_3)

PAUSE = False


def banner(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def step(title):
    if PAUSE:
        input("\n[Enter to continue] ")
    print(f"\n--- {title} ---")


def show_framework(name, af, extra=None):
    banner(f"{name}:  {af}")

    step("Item 2/3/4/5: conflict-free, defence, characteristic function, admissible, complete")
    for S in (extra or []):
        adm, comp = af.is_admissible_and_complete(S)
        print(f"  S={fmt_set(S):<18} conflict-free={str(af.is_conflict_free(S)):<5} "
              f"F(S)={fmt_set(af.F(S)):<18} admissible={str(adm):<5} complete={comp}")
    if extra:
        S = extra[-1]
        for a in sorted(af.arguments):
            print(f"    does {fmt_set(S)} defend {a}?  {af.defends(S, a)}")

    step("Item 6A: grounded extension (iterating F from the empty set)")
    for k, s in enumerate(af.grounded_trace(), 1):
        print(f"  F^{k}(∅) = {fmt_set(s)}")
    print(f"  grounded extension = {fmt_set(af.grounded_extension())}")

    step("Item 6B/6C: complete, preferred, stable, semi-stable extensions")
    for sem, exts in af.all_extensions().items():
        print(f"  {sem:<12} {', '.join(fmt_set(e) for e in exts) if exts else '(none)'}")

    step("Item 6D: all legal labellings")
    for k, L in enumerate(af.legal_labellings(), 1):
        print(f"  L{k}: {af.labelling_str(L)}")

    step("Item 6E: acceptance status of every argument")
    sems = list(SEMANTICS)
    print("  " + f"{'arg':<5}" + "".join(f"{s:<22}" for s in sems))
    for a, row in af.acceptance_report(sems).items():
        print("  " + f"{a:<5}" + "".join(f"{row[s]:<22}" for s in sems))


def part1():
    banner("PART 1 -- ARGUMENTATION ENGINE")
    show_framework("Figure 5.1 (Examples 5.5, 5.6, 5.8)", fig_5_1(),
                   extra=[set(), {"a3"}, {"a5"}, {"a3", "a5"}, {"a1", "a3", "a5"}])
    print("\n  Book: admissible = ∅,{α3},{α5},{α3,α5},{α1,α3,α5}; only complete ext. {α1,α3,α5}  ✔")
    show_framework("Figure 5.2 (Examples 5.7, 5.8)", fig_5_2(), extra=[{"a3"}, {"a1", "a3"}])
    print("\n  Book: complete {α3},{α1,α3},{α2,α3}; grounded {α3}; preferred {α1,α3},{α2,α3}  ✔")
    show_framework("Figure 5.3", fig_5_3(), extra=[{"e"}, {"a", "c", "e"}])
    print("\n  Book: grounded extension {a, c, e}  ✔")
    show_framework("Exercise 1", exercise_1(), extra=[{"d"}, {"a", "d"}])
    show_framework("Exercise 2 (odd cycle)", exercise_2(), extra=[{"a"}])
    print("\n  Odd cycle: the only labelling is all-undec, no stable extension exists.")


def show_outcome(att, types, reports, label):
    o = mechanism(att, list(reports.values()))
    us = ", ".join(f"u_{k}={utility(o, types[k])}" for k in types)
    reps = "; ".join(f"{k}:{fmt_set(v)}" for k, v in reports.items())
    print(f"  {label:<26} reports [{reps}] -> outcome {fmt_set(o)}   ({us})")
    return o


def part2():
    banner("PART 2 -- STRATEGIC ARGUMENTATION (grounded direct mechanism)")

    att, types = example_5_10()
    step("Example 5.10 / Figure 5.4:  R = a1->a2, a2->a3, a3->a4, a3->a5")
    print("  types:", "; ".join(f"A_{k}={fmt_set(v)}" for k, v in types.items()))
    show_outcome(att, types, types, "truthful")
    print("  (Book misprint: it writes u_y(o,{α3})=1, u_z(o,{α2})=0 -- the sets are swapped;\n"
          "   correctly u_y(o,{α2})=0 and u_z(o,{α3})=1, as printed above.)")
    show_outcome(att, types, {"x": {"a4", "a5"}, "y": {"a2"}, "z": {"a3"}}, "x hides a1")

    step("Item 2: best response of x when y, z are truthful")
    br = best_responses(att, types, "x", {"y": types["y"], "z": types["z"]})
    for rep, o, u in br["all"]:
        mark = "  <- best" if u == br["best_utility"] else ""
        print(f"    reveal {fmt_set(rep):<16} outcome {fmt_set(o):<18} u_x={u}{mark}")
    print(f"  truthful utility {br['truthful_utility']}, best {br['best_utility']} "
          f"-> truthful is best? {br['truthful_is_best']}")

    step("Item 3: Theorem 5.3 (exhaustive) strategyproofness check")
    r = check_theorem_53(att, types)
    print(f"  strategyproof: {r['strategyproof']}")
    if r["violations"]:
        v = r["violations"][0]
        print(f"  witness: agent {v['agent']}, others reveal {fmt_set(v['others_reveal'])}: "
              f"hiding {fmt_set(v['hidden'])} raises utility {v['truthful_utility']} -> {v['better_utility']}")

    step("Item 4: Theorem 5.4 condition (odd-length path between an agent's own arguments)")
    c = check_theorem_54(att, types)
    print(f"  condition holds: {c['holds']};  violations: "
          + ", ".join(f"{ag}: {a}~>{b}" for ag, a, b in c["violations"]))

    att, types = example_5_11()
    step("Example 5.11 / Figure 5.5: add a6 -> a3, give a6 to x")
    print("  types:", "; ".join(f"A_{k}={fmt_set(v)}" for k, v in types.items()))
    show_outcome(att, types, types, "truthful")
    print(f"  strategyproof (Thm 5.3): {check_theorem_53(att, types)['strategyproof']}")
    c = check_theorem_54(att, types)
    print(f"  Thm 5.4 condition holds: {c['holds']}  (violations "
          + ", ".join(f"{a}~>{b}" for _, a, b in c["violations"]) + ")")
    print("  => the condition is sufficient but NOT necessary.")
    print("  Which argument cancels the indirect self-defeat? (book says α5 -- misprint)")
    for drop in ("a5", "a6"):
        t2 = {k: (v - {drop} if k == "x" else v) for k, v in types.items()}
        print(f"    x without {drop}: strategyproof = {check_theorem_53(att, t2)['strategyproof']}")
    print("  -> removing a6 restores the manipulation, so it is α6 that cancels it.")

    step("Mini experiment (60 random instances; run experiments.py for the full study)")
    from experiments import random_instance
    from argumentation.strategic import analyse_instance
    rng = random.Random(1)
    for p in (0.15, 0.25, 0.35):
        sp = cond = bad = 0
        for _ in range(20):
            n, args, att, types = random_instance(rng, p)
            res = analyse_instance(att, types, arguments=args)
            sp += res["strategyproof"]
            cond += res["cond_walk"]
            bad += res["cond_walk"] and not res["strategyproof"]
        print(f"  p={p}: strategyproof {sp}/20, Thm 5.4 condition {cond}/20, condition-but-manipulable {bad}")


def main():
    global PAUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("1", "2"), help="run only one part")
    ap.add_argument("--pause", action="store_true", help="wait for Enter between steps")
    a = ap.parse_args()
    PAUSE = a.pause
    if a.part in (None, "1"):
        part1()
    if a.part in (None, "2"):
        part2()
    print()


if __name__ == "__main__":
    main()
