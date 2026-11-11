#!/usr/bin/env python3
"""
Build the assignment report:  report/REPORT.md  ->  REPORT.pdf (project root).

    .venv/bin/python report/build_report.py            # figures + PDF
    .venv/bin/python report/build_report.py --no-figs  # PDF only (reuse figures)

Steps
  1. figures/  -- graph drawings computed with the `argumentation` package
                  (book examples, Q3 example instances), run-comparison plot
  2. figures/*.txt -- captured terminal output (unit tests, experiment summary, demo)
  3. REPORT.md -> HTML (python-markdown) -> PDF (WeasyPrint), with report.css

Needs matplotlib, markdown and weasyprint (pip install -r requirements.txt in .venv).
Screenshots of the web demo are made separately by report/screenshots.py.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")
sys.path.insert(0, ROOT)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402

from argumentation import ArgumentationFramework, mechanism, utility  # noqa: E402
from argumentation.book_examples import example_5_10, example_5_11, fig_5_1, fig_5_2, fig_5_3  # noqa: E402

# ---------------------------------------------------------------------- #
# graph drawing
# ---------------------------------------------------------------------- #
LAB_STYLE = {
    "in": ("#dcfce7", "#16a34a", "-"),
    "out": ("#fee2e2", "#dc2626", "--"),
    "undec": ("#eceff3", "#6b7280", "-"),
    None: ("#ffffff", "#475569", "-"),
}
AGENT_COLORS = ["#2563eb", "#d97706", "#9333ea", "#0891b2"]
R = 0.42

# book-like positions (x right, y up)
POS = {
    "fig51": {"a3": (1.5, 4), "a2": (4, 4), "a1": (6.5, 2.6), "a5": (1.5, 1.2), "a4": (4, 1.2)},
    "fig52": {"a2": (1.5, 3), "a1": (4.5, 3), "a3": (4.5, 1)},
    "fig53": {"a": (3, 5.6), "b": (3, 4.1), "c": (1.7, 2.6), "d": (4.3, 2.6), "e": (4.3, 1.1)},
    "ex510": {"a1": (1, 2.5), "a2": (3, 2.5), "a3": (5, 2.5), "a4": (7, 4), "a5": (7, 1)},
    "ex511": {"a1": (1, 2.5), "a2": (3, 2.5), "a3": (5, 2.5), "a4": (7, 4), "a5": (7, 1), "a6": (3, 4.6)},
}


def circle_layout(args):
    n = len(args)
    rad = 2.3 if n > 3 else 1.6
    return {a: (3 + rad * math.cos(math.pi / 2 - 2 * math.pi * k / n),
                3 + rad * math.sin(math.pi / 2 - 2 * math.pi * k / n)) for k, a in enumerate(args)}


def draw_graph(ax, args, attacks, pos, lab=None, agent_of=None, hidden=(), title=None, highlight=()):
    lab = lab or {}
    agent_of = agent_of or {}
    hidden = set(hidden)
    ring = {a: (R * 1.3 if a in agent_of else R) for a in args}
    atts = set(map(tuple, attacks))
    for (x, y) in atts:
        alpha = 0.18 if (x in hidden or y in hidden) else 1.0
        hl = (x, y) in set(highlight)
        color = "#f59e0b" if hl else "#475569"
        lw = 2.4 if hl else 1.3
        (x1, y1), (x2, y2) = pos[x], pos[y]
        if x == y:
            r = ring[x]
            a1, a2 = math.radians(115), math.radians(65)
            p0 = (x1 + r * math.cos(a1), y1 + r * math.sin(a1))
            p3 = (x1 + (r + 0.02) * math.cos(a2), y1 + (r + 0.02) * math.sin(a2))
            path = Path([p0, (x1 - 0.75, y1 + 1.35), (x1 + 0.75, y1 + 1.35), p3],
                        [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
            ax.add_patch(FancyArrowPatch(path=path, arrowstyle="-|>", mutation_scale=11, color=color,
                                         lw=lw, alpha=alpha, zorder=1))
            continue
        d = math.hypot(x2 - x1, y2 - y1) or 1
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        s = (x1 + ux * ring[x], y1 + uy * ring[x])
        e = (x2 - ux * (ring[y] + 0.03), y2 - uy * (ring[y] + 0.03))
        rad = 0.25 if (y, x) in atts else 0.0
        ax.add_patch(FancyArrowPatch(s, e, arrowstyle="-|>", mutation_scale=12, color=color, lw=lw,
                                     alpha=alpha, connectionstyle=f"arc3,rad={rad}", zorder=1,
                                     shrinkA=0, shrinkB=0))
    for a in args:
        x, y = pos[a]
        alpha = 0.25 if a in hidden else 1.0
        fill, edge, ls = LAB_STYLE[lab.get(a)] if a not in hidden else LAB_STYLE[None]
        if a in agent_of:
            ax.add_patch(Circle((x, y), R * 1.22, fill=False, lw=3.2,
                                ec=AGENT_COLORS[agent_of[a] % 4], alpha=alpha, zorder=2))
        ax.add_patch(Circle((x, y), R, fc=fill, ec=edge, lw=2.0, ls=ls, alpha=alpha, zorder=3))
        ax.text(x, y, str(a).replace("a", "α") if re.fullmatch(r"a\d+", str(a)) else str(a),
                ha="center", va="center", fontsize=11, fontweight="bold", alpha=alpha, zorder=4)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 1.0, max(xs) + 1.0)
    ax.set_ylim(min(ys) - 0.9, max(ys) + 1.6)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10.5)


def grounded_labelling(args, attacks):
    af = ArgumentationFramework(args, [e for e in attacks if e[0] in args and e[1] in args])
    return af.extension_to_labelling(af.grounded_extension())


def legend(fig, agents=None, y=0.0):
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", ms=10, mfc=LAB_STYLE[k][0], mec=LAB_STYLE[k][1], mew=2, label=k)
         for k in ("in", "out", "undec")]
    if agents:
        h += [Line2D([], [], marker="o", ls="", ms=12, mfc="none", mec=AGENT_COLORS[i % 4], mew=3,
                     label=f"agent {name}") for i, name in enumerate(agents)]
    fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False, bbox_to_anchor=(0.5, y), fontsize=9)


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", os.path.relpath(os.path.join(FIG, name), ROOT))


# ---------------------------------------------------------------------- #
# figures
# ---------------------------------------------------------------------- #
def fig_book_engine():
    fig = plt.figure(figsize=(11, 6.6))
    gs = fig.add_gridspec(2, 6)
    top = [fig.add_subplot(gs[0, 0:3]), fig.add_subplot(gs[0, 3:6])]
    bottom = [fig.add_subplot(gs[1, 2 * i:2 * i + 2]) for i in range(3)]
    axes = [top, bottom]
    af = fig_5_1()
    draw_graph(axes[0][0], sorted(af.arguments), af.attacks, POS["fig51"],
               af.extension_to_labelling(af.grounded_extension()),
               title="Fig 5.1 — grounded {α1, α3, α5}")
    af3 = fig_5_3()
    draw_graph(axes[0][1], sorted(af3.arguments), af3.attacks, POS["fig53"],
               af3.extension_to_labelling(af3.grounded_extension()), title="Fig 5.3 — grounded {a, c, e}")
    af2 = fig_5_2()
    names = ["L_G (grounded)", "L_1", "L_2"]
    labs = sorted(af2.legal_labellings(), key=lambda L: (sum(v == "in" for v in L.values()), L.get("a1") == "in"))
    for ax, L, nm in zip(axes[1], labs, names):
        ext = sorted(a.replace("a", "α") for a in af2.labelling_to_extension(L))
        draw_graph(ax, sorted(af2.arguments), af2.attacks, POS["fig52"], L,
                   title=f"Fig 5.2 — {nm}: in = {{{', '.join(ext)}}}")
    legend(fig, y=-0.02)
    save(fig, "book_engine.png")


def _agents(types):
    return {a: i for i, (k, v) in enumerate(types.items()) for a in v}


def fig_strategic_book():
    att, types = example_5_10()
    names = list(types)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    rep_t = dict(types)
    rep_l = {"x": {"a4", "a5"}, "y": {"a2"}, "z": {"a3"}}
    for ax, rep, ttl in ((axes[0], rep_t, "truthful"), (axes[1], rep_l, "x hides α1")):
        rev = set().union(*rep.values())
        o = mechanism(att, rep.values())
        u = ", ".join(f"u_{k}={utility(o, types[k])}" for k in names)
        draw_graph(ax, sorted(set().union(*types.values())), att, POS["ex510"],
                   grounded_labelling(rev, att), _agents(types), hidden=set().union(*types.values()) - rev,
                   title=f"Ex 5.10, {ttl}: outcome {{{', '.join(sorted(a.replace('a', 'α') for a in o))}}}\n({u})")
    legend(fig, names, y=-0.06)
    save(fig, "ex510.png")

    att, types = example_5_11()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
    o = mechanism(att, types.values())
    draw_graph(axes[0], sorted(set().union(*types.values())), att, POS["ex511"],
               grounded_labelling(set().union(*types.values()), att), _agents(types),
               title=f"Ex 5.11 truthful: outcome {{α1, α4, α5, α6}}, u_x = {utility(o, types['x'])}\n"
                     "strategyproof although α1 ⇝ α4, α1 ⇝ α5 (odd paths)")
    t2 = {k: (v - {"a6"} if k == "x" else v) for k, v in types.items()}
    rep = {"x": {"a4", "a5"}, "y": {"a2"}, "z": {"a3"}}
    rev = set().union(*rep.values())
    o2 = mechanism(att, rep.values())
    draw_graph(axes[1], sorted(set().union(*types.values())), att, POS["ex511"],
               grounded_labelling(rev, att), _agents(t2), hidden={"a1", "a6"},
               title=f"…without α6, x hides α1 again: u_x {utility(mechanism(att, t2.values()), t2['x'])} → "
                     f"{utility(o2, t2['x'])}\n(α6, not α5, cancels the indirect self-defeat)")
    legend(fig, list(types), y=-0.06)
    save(fig, "ex511.png")


Q3_PICK = [
    ("compensated/source-itself-lost", "p0.15-0645", "Hiding gains nothing on balance (hidden argument itself lost)"),
    ("compensated/other-own-argument-lost", "p0.15-0076", "Hiding loses other own arguments (α6 effect)"),
    ("hiding-never-helps", "p0.15-0069", "Hiding never frees the target"),
    ("victim-never-in", "p0.15-0548", "Target never accepted"),
    ("self-defeat-only", "p0.15-0050", "Only self-attacking arguments"),
]


def _parse_edge(s):
    x, y = s.split("->")
    return (x, y)


def fig_q3_examples():
    """One figure per Q3 reason: truthful report vs. hiding the offending source argument."""
    path = os.path.join(ROOT, "results", "q3_examples.json")
    with open(path) as f:
        q3 = json.load(f)
    meta = []
    for cat, want, label in Q3_PICK:
        exs = q3.get(cat, {}).get("examples") or []
        ex = next((e for e in exs if e["id"] == want), exs[0] if exs else None)
        if ex is None:
            continue
        att = [_parse_edge(s) for s in ex["attacks"]]
        types = {k: set(v) for k, v in ex["types"].items()}
        args = sorted(set().union(*types.values()), key=lambda a: int(a[1:]))
        pos = circle_layout(args)
        ag = _agents(types)
        viol = [v.split(": ") for v in ex["violations_walk"]]
        pairs = [(agt, *vv.split("~>")) for agt, vv in viol]
        proper = [p for p in pairs if p[1] != p[2]] or pairs
        agent, src, dst = proper[0]
        o = mechanism(att, types.values())
        rep = {k: (v - {src} if k == agent else v) for k, v in types.items()}
        o2 = mechanism(att, rep.values())
        u1, u2 = utility(o, types[agent]), utility(o2, types[agent])
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.9))
        draw_graph(axes[0], args, att, pos, grounded_labelling(set(args), att), ag,
                   title=f"truthful: u_{agent} = {u1}")
        rev = set().union(*rep.values())
        draw_graph(axes[1], args, att, pos, grounded_labelling(rev, att), ag, hidden={src},
                   title=f"agent {agent} hides {src.replace('a', 'α')}: u_{agent} = {u2}")
        fig.suptitle(f"{label}   [instance {ex['id']}]", fontsize=11, fontweight="bold", y=1.0)
        legend(fig, list(types), y=-0.05)
        slug = cat.replace("/", "_")
        save(fig, f"q3_{slug}.png")
        meta.append({"category": cat, "label": label, "id": ex["id"], "figure": f"q3_{slug}.png",
                     "types": ex["types"], "attacks": ex["attacks"], "agent": agent, "source": src,
                     "target": dst, "u_truth": u1, "u_hide": u2, "violations": ex["violations_walk"],
                     "truthful_outcome": ex["truthful_outcome"], "detail": ex["diagnosis"]["detail"]})
    with open(os.path.join(FIG, "q3_examples.json"), "w") as f:
        json.dump(meta, f, indent=2)


def fig_compare_runs():
    runs = []
    for d, lab in (("results", "self-attacks allowed (main)"), ("results_no_self_attacks", "no self-attacks")):
        p = os.path.join(ROOT, d, "summary.json")
        if os.path.exists(p):
            with open(p) as f:
                runs.append((lab, json.load(f)))
    if not runs:
        return
    ps = list(runs[0][1]["per_p"])
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.4))
    for ax, key, ttl in ((axes[0], "frac_strategyproof", "fraction strategyproof"),
                         (axes[1], "frac_cond_walk", "fraction satisfying the Thm 5.4 condition")):
        w = 0.36
        for j, (lab, s) in enumerate(runs):
            ys = [s["per_p"][p][key] for p in ps]
            xs = [i + (j - 0.5) * w for i in range(len(ps))]
            ax.bar(xs, ys, w, color=["#2563eb", "#d97706"][j], label=lab)
            for x, y in zip(xs, ys):
                ax.text(x, y + 0.012, f"{100 * y:.1f}%", ha="center", fontsize=8)
        ax.set_xticks(range(len(ps)), [f"p = {p}" for p in ps])
        ax.set_ylim(0, 0.75)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.set_title(ttl, fontsize=10.5, fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.tight_layout()
    save(fig, "compare_runs.png")


# ---------------------------------------------------------------------- #
# captured terminal output
# ---------------------------------------------------------------------- #
def capture_text():
    def write(name, text):
        with open(os.path.join(FIG, name), "w") as f:
            f.write(text.rstrip() + "\n")
        print("wrote", os.path.relpath(os.path.join(FIG, name), ROOT))

    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                       cwd=ROOT, capture_output=True, text=True)
    lines = r.stderr.strip().splitlines()
    tests = [ln for ln in lines if " ... " in ln]
    short = [re.sub(r"^(\w+) \((test_\w+)\.(\w+)\.\w+\)", r"\2.\3.\1", ln) for ln in tests]
    write("tests.txt", "$ python3 -m unittest discover -s tests -v\n" + "\n".join(short) + "\n"
          + "-" * 70 + "\n" + "\n".join(lines[-3:]))

    from experiments import print_summary
    out = []
    for d, cmd in (("results", "python3 experiments.py"),
                   ("results_no_self_attacks", "python3 experiments.py --no-self-attacks --out results_no_self_attacks")):
        with open(os.path.join(ROOT, d, "summary.json")) as f:
            s = json.load(f)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_summary(s)
        out.append(f"$ {cmd}\n" + buf.getvalue().strip())
    write("experiments_main.txt", out[0])
    write("experiments_noself.txt", out[1])

    r = subprocess.run([sys.executable, "demo.py", "--part", "2"], cwd=ROOT, capture_output=True, text=True)
    demo = r.stdout.splitlines()
    end = next((i for i, ln in enumerate(demo) if ln.startswith("--- Mini experiment")), len(demo))
    write("demo_part2.txt", "$ python3 demo.py --part 2\n" + "\n".join(demo[:end]))
    r = subprocess.run([sys.executable, "demo.py", "--part", "1"], cwd=ROOT, capture_output=True, text=True)
    demo = r.stdout.splitlines()
    end = next((i for i, ln in enumerate(demo) if "Figure 5.2" in ln and ln.startswith("Figure")), 60)
    write("demo_part1.txt", "$ python3 demo.py --part 1\n" + "\n".join(demo[:end]).rstrip("=\n"))


# ---------------------------------------------------------------------- #
# Markdown -> HTML -> PDF
# ---------------------------------------------------------------------- #
LIST_ITEM = re.compile(r"\s*(?:[-*+]|\d+\.)\s")


def blank_line_before_lists(md: str) -> str:
    """Python-Markdown needs a blank line before a list that follows a paragraph line."""
    out, fenced = [], False
    for line in md.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        prev = out[-1] if out else ""
        if (not fenced and LIST_ITEM.match(line) and prev.strip() and not LIST_ITEM.match(prev)
                and not prev.lstrip().startswith(("|", "<", "```"))):
            out.append("")
        out.append(line)
    return "\n".join(out)


def build_pdf():
    import markdown
    from weasyprint import HTML

    with open(os.path.join(HERE, "REPORT.md"), encoding="utf-8") as f:
        md = f.read()

    def include(m):
        with open(os.path.join(HERE, m.group(1)), encoding="utf-8") as f:
            return "```text\n" + f.read().rstrip() + "\n```"
    md = re.sub(r"\{\{include:([^}]+)\}\}", include, md)
    md = blank_line_before_lists(md)

    body = markdown.markdown(md, extensions=["tables", "fenced_code", "toc", "sane_lists"],
                             extension_configs={"toc": {"toc_depth": "2-3"}})
    with open(os.path.join(HERE, "report.css"), encoding="utf-8") as f:
        css = f.read()
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>Assignment 3 Report</title>" \
           f"<style>{css}</style></head><body>{body}</body></html>"
    with open(os.path.join(HERE, "REPORT.html"), "w", encoding="utf-8") as f:
        f.write(html)
    out = os.path.join(ROOT, "REPORT.pdf")
    HTML(string=html, base_url=HERE).write_pdf(out)
    print("wrote", os.path.relpath(out, ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-figs", action="store_true", help="skip regenerating figures / captured text")
    a = ap.parse_args()
    os.makedirs(FIG, exist_ok=True)
    if not a.no_figs:
        plt.rcParams.update({"font.size": 10, "savefig.dpi": 200})
        fig_book_engine()
        fig_strategic_book()
        fig_q3_examples()
        fig_compare_runs()
        capture_text()
    build_pdf()


if __name__ == "__main__":
    main()
