# Assignment 3: Argumentation Engine and Strategic Argumentation

This project has three parts:

1. **Argumentation engine.** It computes the standard extension semantics of abstract argumentation frameworks.
2. **Grounded direct argumentation mechanism.** It checks when agents gain by hiding arguments.
3. **Random-instance experiments.** They test Theorems 5.3 and 5.4.

Definitions, examples and theorem numbers follow Chapter 5 of the course book, *Argumentation among Agents* by I. Rahwan, in G. Weiss (ed.), *Multiagent Systems*, 2nd ed., MIT Press 2013 (`multiagent-systems_compress.pdf`, book pp. 177–206).

---

## 1. Requirements

- Python **3.8 or later** (developed on 3.14).
- **The core code uses the standard library only.** The library, tests, both demos and the experiments run with plain `python3`.
- **Optional packages** (listed in `requirements.txt`) are needed only for the **plots** (`matplotlib`) and for **building the report PDF** (`markdown`, `weasyprint`). Ubuntu blocks system-wide `pip`, so install them into the project's virtual environment:

```bash
python3 -m venv .venv                          # already created in this project
.venv/bin/pip install -r requirements.txt
```

Without matplotlib, `experiments.py` still writes all results and just prints that the plots were skipped.

---

## 2. File structure

```
AutoAssign3/
├── argumentation/                  # the library (all of the assignment's functions)
│   ├── __init__.py                 # re-exports the public API
│   ├── framework.py                # PART 1: the ArgumentationFramework class and all semantics
│   ├── strategic.py                # PART 2: mechanism, best response, Thm 5.3 and Thm 5.4 checks
│   └── book_examples.py            # the book's examples (Fig 5.1-5.5, Ex 5.10/5.11, Exercises 1-2)
│
├── tests/                          # unit tests (35), checked against the book's stated answers
│   ├── test_framework.py           # Part 1 tests + property tests on random graphs
│   └── test_strategic.py           # Part 2 tests (Ex 5.10, 5.11, misprints, cycles, Thm 5.4 ⇒ SP)
│
├── demo.py                         # terminal demonstration: walks through every function on the book examples
├── web_demo.py                     # LIVE browser demonstration (stdlib HTTP server + JSON API over the package)
├── web/                            # front-end of the browser demo (plain HTML/CSS/JS, no libraries, works offline)
│   ├── index.html
│   ├── style.css
│   └── app.js                      # draws + animates the graphs; all results come from the Python API
├── experiments.py                  # the random-instance experiments (Q1, Q2, Q3); also saves plots
├── plots.py                        # matplotlib plots (called by experiments.py; can rebuild plots alone)
│
├── results/                        # experiment output, MAIN run (self-attacks allowed)
│   ├── summary.json                # aggregate numbers per p (Q1 fractions, Q2/Q3 counts)
│   ├── instances.csv               # one row per instance (3000 rows)
│   ├── q2_instances.json           # instances where the condition holds but SP fails (empty)
│   ├── q3_examples.json            # SP-despite-violation instances, by reason, with examples
│   └── plots/                      # 5 PNG plots (created when matplotlib is available)
│
├── results_no_self_attacks/        # the same experiment, but with no a->a attacks (comparison run)
│   └── (same files + plots/)
│
├── report/                         # the report: source, figures and build scripts
│   ├── REPORT.md                   # report source (Markdown)
│   ├── report.css                  # PDF styling
│   ├── build_report.py             # draws figures, captures outputs, builds ../REPORT.pdf
│   ├── screenshots.py              # takes web-demo screenshots with headless Firefox
│   ├── scenes/                     # scripted web-demo scenes used for the screenshots
│   └── figures/                    # generated figures, screenshots and captured terminal output
├── REPORT.pdf                      # the final report
├── requirements.txt                # optional packages (plots + report); the core needs none
├── .venv/                          # virtual environment holding the optional packages
├── README.md                       # this file
├── Argumentation Framework Functions.pdf   # assignment specification
└── multiagent-systems_compress.pdf         # reference book
```

### `results/` vs `results_no_self_attacks/`

The two folders hold the **same experiment with the same seed (42)**. The only difference is how random attacks are drawn:

| Folder | How it is produced | Attack generation |
|---|---|---|
| `results/` | `python3 experiments.py` | Each ordered pair (a, b), **including a = b**, is an attack with probability p. **This is the main run.** |
| `results_no_self_attacks/` | `python3 experiments.py --no-self-attacks --out results_no_self_attacks` | Only pairs with a ≠ b can be attacks. This is the comparison run. |

The spec says "each possible attack" without saying whether self-attacks count, so both runs are reported. A self-attacking argument automatically breaks the Theorem 5.4 condition, because a → a is an odd path of length 1. So self-attacks make the condition much rarer. The comparison run shows that the conclusions (in particular Q2 = 0) do not depend on this choice.

### Plots (`results*/plots/`)

| File | Shows |
|---|---|
| `q1_strategyproof_by_p.png` | fraction strategyproof and fraction satisfying the Thm 5.4 condition, per p (95% CIs) |
| `contingency_by_p.png` | condition × strategyproof for each p; the Q2 segment is empty |
| `q3_reasons.png` | why instances are strategyproof although the condition fails, stacked by p |
| `sp_by_n.png` | fraction strategyproof vs. number of arguments (6/7/8) |
| `sp_vs_attacks.png` | fraction strategyproof vs. number of attacks |

### `instances.csv` columns

`id, p, n, n_attacks, attacks, types, strategyproof, thm54_walk, thm54_simple, truthful_outcome, manipulating_agent, hidden, q3_category`

- `strategyproof`, `thm54_walk` and `thm54_simple` are 0/1.
- For manipulable instances, `manipulating_agent` and `hidden` give one profitable lie.

---

## 3. How to run

Run all commands from the project root (`AutoAssign3/`).

```bash
# Unit tests (35 tests, ~0.1 s)
python3 -m unittest discover -s tests -v

# Demonstration (narrated walk-through of everything)
python3 demo.py              # both parts
python3 demo.py --part 1     # only the argumentation engine
python3 demo.py --part 2     # only strategic argumentation + a mini experiment
python3 demo.py --pause      # wait for Enter between steps (for live presentation)

# Experiments (1000 instances per p, ~1 s); use .venv/bin/python so the plots are saved too
.venv/bin/python experiments.py                          # -> results/ (+ results/plots/)
.venv/bin/python experiments.py --no-self-attacks --out results_no_self_attacks
.venv/bin/python experiments.py --n-instances 5000 --seed 7   # other sizes or seeds
.venv/bin/python plots.py results results_no_self_attacks     # rebuild only the plots

# Report
.venv/bin/python report/screenshots.py                   # web-demo screenshots (needs Firefox)
.venv/bin/python report/build_report.py                  # figures + REPORT.pdf
```

### Live browser demo

```bash
python3 web_demo.py                  # starts http://localhost:8000 and opens your browser
python3 web_demo.py --port 9000 --no-browser
```

Stop it with `Ctrl+C`. The page only draws and animates. Every result it shows is computed by the `argumentation` package through a small JSON API in `web_demo.py`: `/api/analyze`, `/api/mechanism`, `/api/best_response`, `/api/strategic`, `/api/random` and `/api/experiments`. The demo has three tabs.

| Tab | What you can do |
|---|---|
| **1 · Engine** | Pick a book example or build your own graph. In *Edit graph* mode: click empty space to add an argument, click A then B to toggle the attack A→B (A then A makes a self-attack), click an arrow to delete it, and Shift+click an argument to delete it. In *Select S* mode, click arguments to build a set S and see conflict-free, S⁺, F(S), admissible, complete and stable. **▶ Play** animates the grounded construction F¹(∅), F²(∅), … up to the fixed point. Click any extension to colour the graph with it, step or auto-cycle through all legal labellings, and hover a row of the acceptance-status table to highlight that argument. |
| **2 · Strategic** | Load Example 5.10, Example 5.11 or a **random instance** (choose p and whether self-attacks are allowed). Each agent's arguments carry the agent's colour. Untick an argument, or click it on the graph, to *hide* it: it fades out and the mechanism's outcome and utility bars update live. ✕ removes an argument from the instance, which is how you test the α5/α6 misprint. **Best response** lists every report the agent could make; click a row to play it. **Check Theorems 5.3 & 5.4** gives the verdict and, if the instance is manipulable, a witness. **▶ Show manipulation** animates the profitable lie step by step. Click an odd-path violation to trace the walk edge by edge. For instances that are strategyproof despite failing the condition, the Q3 reason is shown. |
| **3 · Experiments** | Charts of the fraction of instances that are strategyproof and that satisfy the Theorem 5.4 condition, for each p and both runs, plus the Q2 count, the Q3 breakdown and the contingency table. Data comes from `results*/summary.json`, so run `experiments.py` first. |

Colours: green = `in`/accepted, red dashed = `out`, grey = `undec`, blue ring = in S, orange dotted ring = in F(S), faded = hidden. Light and dark themes follow the system setting.

`experiments.py` options:

| Option | Meaning | Default |
|---|---|---|
| `--n-instances` | instances generated **per value of p** | 1000 |
| `--seed` | random seed (results are reproducible) | 42 |
| `--no-self-attacks` | forbid a → a attacks | off |
| `--out` | output directory | `results` |
| `--no-plots` | do not save the matplotlib plots | off |

### Using the library directly

```python
from argumentation import ArgumentationFramework, mechanism, check_theorem_53, check_theorem_54

af = ArgumentationFramework({"a", "b", "c"}, {("a", "b"), ("b", "c")})
af.grounded_extension()            # frozenset({'a', 'c'})
af.preferred_extensions()          # [frozenset({'a', 'c'})]
af.legal_labellings()              # [{'a': 'in', 'b': 'out', 'c': 'in'}]
af.acceptance_status("b", "preferred")   # 'rejected'

attacks = {("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a3", "a5")}
types   = {"x": {"a1", "a4", "a5"}, "y": {"a2"}, "z": {"a3"}}
mechanism(attacks, types.values())       # frozenset({'a1', 'a3'})
check_theorem_53(attacks, types)         # {'strategyproof': False, 'violations': [...]}
check_theorem_54(attacks, types)         # {'holds': False, 'violations': [('x','a1','a4'), ...]}
```

---

## 4. Where each spec item is implemented

### Part 1: Argumentation engine (`argumentation/framework.py`)

| Spec item | Function / method | Book definition |
|---|---|---|
| 1. Framework class ⟨A, ⇀⟩ | `ArgumentationFramework(arguments, attacks)`, `restrict(subset)` | Def 5.1 |
| 2. Conflict-free test | `is_conflict_free(S)`: S ∩ S⁺ = ∅ | Def 5.2 |
| 3. Is α defended by S | `defends(S, a)`: α⁻ ⊆ S⁺ | Def 5.2 |
| 4. Characteristic function | `characteristic(S)` (alias `F(S)`) | Def 5.3 |
| 5. Admissible / complete | `is_admissible(S)`, `is_complete(S)`, `is_admissible_and_complete(S)` | Def 5.4, 5.5 |
| 6A. Grounded extension | `grounded_extension()`, `grounded_trace()` (F¹(∅), F²(∅), …) | Def 5.7 |
| 6B. All complete extensions | `complete_extensions()` (cross-checked with `complete_extensions_bruteforce()`) | Def 5.5 |
| 6C. Preferred, stable, semi-stable | `preferred_extensions()`, `stable_extensions()`, `semi_stable_extensions()`, `all_extensions()` | Def 5.7, Table 5.1 |
| 6D. All legal labellings | `legal_labellings()`, `is_legal_labelling(L)` | Def 5.6 |
| 6E. Acceptance status | `acceptance_status(a, semantics)`, `acceptance_report()` | Def 5.8 |

### Part 2: Strategic argumentation (`argumentation/strategic.py`)

| Spec item | Function | Book |
|---|---|---|
| 1. The mechanism | `mechanism(attacks, reports)`: grounded extension of the graph induced by ⋃ reports | Def 5.21 |
| (utility) | `utility(outcome, A_i)` = \|o ∩ Aᵢ\| | Def 5.22 |
| 2. Best responses | `best_responses(attacks, types, i, others_reports)` | |
| 3. Theorem 5.3 check | `check_theorem_53(attacks, types)` / `is_strategyproof(...)` | Thm 5.3 |
| 4. Theorem 5.4 check | `check_theorem_54(attacks, types, path_mode="walk" or "simple")` | Thm 5.4 |
| Experiments helper | `analyse_instance(...)`, `diagnose_sp_despite_violation(...)` | |
| Odd-path witness (used by the web demo) | `odd_walk_witness(game, a, b)`: a shortest odd walk a → … → b | |

---

## 5. How the algorithms work

- **Grounded extension:** apply F repeatedly starting from ∅ until it stops changing (Dung). This is the least fixed point.
- **Legal labellings:** a backtracking search over in/out/undec. Each argument is checked against Def 5.6 as soon as it and all its attackers have labels. Complete extensions are the `in` sets of the legal labellings (Caminada's correspondence). Preferred, stable and semi-stable extensions are then picked out using Table 5.1:
  - preferred: maximal `in`;
  - stable: empty `undec`;
  - semi-stable: maximal S ∪ S⁺.
- **Mechanism and Theorem 5.3:** the outcome depends only on the *union* of the reports. So each instance stores the arguments as bitmasks and caches the grounded extension for each revealed set. For every agent i and every combination of subsets the others could reveal, it checks that revealing all of Aᵢ is a best response. With at most 8 arguments, this is at most 3 × 2⁸ grounded computations per instance.
- **Theorem 5.4 and cycles:** "is there an odd-length path from α to β?" is answered by a breadth-first search over (argument, parity) pairs, where parity records whether the path so far has odd or even length. There are only 2n such states, so the search always ends, even when the graph has cycles. `path_mode="simple"` instead lists simple paths exhaustively, which is fine for at most 8 arguments, so the two readings can be compared.

---

## 6. Design decisions

1. **Self-attacks are allowed** in random instances (main run). A comparison run without them is in `results_no_self_attacks/`.
2. **α = β is included** in the Theorem 5.4 check. A self-attack, or an odd cycle through one of an agent's own arguments, counts as a violation. A direct attack (path length 1) also counts, so the check includes "each type is conflict-free".
3. **Paths and cycles.** The main check uses odd **walks**, where arguments may repeat. This is the safe reading when the graph has cycles. The **simple-path** reading is also computed. The two gave the same answer on every random instance, but `tests/test_strategic.py::test_walk_vs_simple` shows a graph where they differ.
4. **Lying means hiding only** (book Sec. 5.4). Each report Aᵢ° ⊆ Aᵢ, and utility is counted on the agent's *true* type.
5. **Arguments are split at random** among the 3 agents, so an agent may receive no arguments. Such an agent trivially has no profitable lie.
6. **When there are no stable extensions,** for example on an odd cycle, every argument is reported as `rejected` under stable semantics.

---

## 7. Misprints in the book (verified in code)

- **Example 5.10.** The book writes u_y(o, {α3}) = 1 and u_z(o, {α2}) = 0. The argument sets are swapped. With A_y = {α2} and A_z = {α3}, the correct values are **u_y = 0 and u_z = 1**. See `test_truthful_outcome` and `demo.py --part 2`.
- **Discussion after Example 5.11.** The argument that cancels the indirect self-defeat is **α6**, not α5:
  - removing α6 from x's type brings back Example 5.10's manipulation;
  - removing α5 does not.
  See `test_a6_not_a5_cancels_self_defeat`.

---

## 8. Verification against the book

| Example | Book's answer | Reproduced |
|---|---|---|
| Fig 5.1, Ex 5.5 | admissible sets ∅, {α3}, {α5}, {α3,α5}, {α1,α3,α5} | ✔ |
| Fig 5.1, Ex 5.6 | F({α3}) = F({α5}) = {α3,α5}; only complete extension {α1,α3,α5} | ✔ |
| Fig 5.1, grounded | F¹(∅) = {α3,α5}, F²(∅) = {α1,α3,α5} | ✔ |
| Fig 5.2, Ex 5.7, 5.8 | complete {α3}, {α1,α3}, {α2,α3}; grounded {α3}; preferred {α1,α3}, {α2,α3}; 3 labellings | ✔ |
| Fig 5.3 | grounded {a, c, e} | ✔ |
| Ex 5.10 | truthful outcome {α1,α3}; x hides α1 → {α2,α4,α5}, utility 1 → 2; not strategyproof | ✔ |
| Ex 5.11 | outcome {α1,α4,α5,α6}; strategyproof although α1 has odd paths to α4 and α5 | ✔ |
| Exercise 1 (computed) | complete ∅, {d}, {a,d}, {b,d}; grounded ∅; preferred = stable = semi-stable {a,d}, {b,d} | — |
| Exercise 2 (computed) | odd cycle: only the all-undec labelling; grounded = preferred = semi-stable ∅; no stable extension | — |

The tests also check these properties on hundreds of random graphs:
- grounded ⊆ every complete extension;
- stable ⊆ semi-stable ⊆ preferred ⊆ complete;
- maximal admissible sets = preferred extensions;
- the fast mechanism agrees with the engine;
- Theorem 5.4's condition ⇒ strategyproofness (Theorem 5.3).

---

## 9. Experiment results (seed 42, 1000 instances per p, 3 agents, 6–8 arguments)

### Q1: fraction of instances that are strategyproof

| p | SP (self-attacks allowed) | Thm 5.4 condition holds | SP (no self-attacks) | Thm 5.4 condition holds |
|---|---|---|---|---|
| 0.15 | **0.553** | 0.038 | 0.603 | 0.133 |
| 0.25 | **0.256** | 0.002 | 0.309 | 0.019 |
| 0.35 | **0.129** | 0.000 | 0.119 | 0.002 |

Strategyproofness falls quickly as the graph gets denser. The Theorem 5.4 condition is very strict: with about 2–3 arguments per agent, an odd path between two of them appears easily.

### Q2: condition holds but not strategyproof

**0 instances** in both runs, under both the walk and the simple-path reading. This agrees with Theorem 5.4, which says the condition is *sufficient* for strategyproofness. It is a thin test, though: the condition held in only 40 instances in the main run and 154 in the comparison run. `q2_instances.json` is therefore empty.

### Q3: strategyproof although the condition fails

There are **898 instances in the main run and 877 in the no-self-attacks run**, so the condition is far from *necessary*. `diagnose_sp_despite_violation` sorts each one by the first reason that applies. Examples are in `q3_examples.json`.

| Reason | Main run | No self-attacks | Explanation |
|---|---|---|---|
| Hiding gains nothing on balance: the hidden argument itself is lost | 480 | 645 | Hiding α frees its target β, but α was itself accepted, so the agent breaks even (+1, −1) |
| Hiding never frees the target | 225 | 83 | Taking α away never gets β accepted: β stays out or undecided because of another attacker (an unattacked argument, a self-attacker, an odd cycle) |
| Hiding frees the target but loses other own arguments | 78 | 146 | α was also defending other arguments of the agent. Losing them outweighs the gain. This is the α6 effect of Example 5.11 |
| Target never accepted | 63 | 0 | The target β is never accepted in any profile, so there is nothing to gain |
| Only self-attacking arguments | 52 | 3 | The only violations are (α, α) for an α that attacks itself directly or through an odd cycle. Such an α is never accepted, so hiding it never helps |

The **walk** and **simple-path** readings of the condition gave the same answer on every random instance.
