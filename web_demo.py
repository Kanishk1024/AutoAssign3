#!/usr/bin/env python3
"""
Live browser demonstration.

    python3 web_demo.py                 # serves http://localhost:8000 and opens the browser
    python3 web_demo.py --port 9000 --no-browser

A tiny standard-library HTTP server. Every result shown in the browser is
computed by the `argumentation` package (the submitted code) through the JSON
API below; the page in web/ only draws and animates it.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from argumentation import (ArgumentationFramework, ArgumentationGame, best_responses, check_theorem_53,
                           check_theorem_54, mechanism, utility)
from argumentation.book_examples import FRAMEWORKS, example_5_10, example_5_11
from argumentation.framework import _sort_key
from argumentation.strategic import analyse_instance, odd_walk_witness
from experiments import random_instance

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")


# ---------------------------------------------------------------------- #
# JSON helpers
# ---------------------------------------------------------------------- #
def srt(xs):
    return sorted(xs, key=_sort_key)


def parse_graph(body):
    args = [str(a) for a in body.get("args", [])]
    if len(args) != len(set(args)):
        raise ValueError("duplicate argument names")
    if len(args) > 14:
        raise ValueError("at most 14 arguments in the demo")
    attacks = [(str(x), str(y)) for x, y in body.get("attacks", [])]
    return args, attacks


def parse_types(body):
    types = {str(k): [str(a) for a in v] for k, v in body.get("types", {}).items()}
    return types


# ---------------------------------------------------------------------- #
# API
# ---------------------------------------------------------------------- #
def api_examples(_body):
    engine = []
    for name, f in FRAMEWORKS.items():
        af = f()
        engine.append({"name": name, "args": srt(af.arguments),
                       "attacks": sorted(af.attacks, key=lambda e: (_sort_key(e[0]), _sort_key(e[1])))})
    strategic = []
    for name, f in (("Example 5.10 (Fig 5.4)", example_5_10), ("Example 5.11 (Fig 5.5)", example_5_11)):
        att, types = f()
        args = srt(set().union(*types.values()))
        strategic.append({"name": name, "args": args, "attacks": sorted(att),
                          "types": {k: srt(v) for k, v in types.items()}})
    return {"engine": engine, "strategic": strategic}


def api_analyze(body):
    args, attacks = parse_graph(body)
    af = ArgumentationFramework(args, attacks)
    out = {
        "grounded_trace": [srt(s) for s in af.grounded_trace()],
        "grounded": srt(af.grounded_extension()),
        "extensions": {sem: [srt(e) for e in exts] for sem, exts in af.all_extensions().items()},
        "labellings": af.legal_labellings(),
        "status": af.acceptance_report(),
    }
    if "S" in body and body["S"] is not None:
        S = [str(a) for a in body["S"]]
        adm, comp = af.is_admissible_and_complete(S)
        out["S"] = {
            "S": srt(S),
            "conflict_free": af.is_conflict_free(S),
            "S_plus": srt(af.plus(S)),
            "F": srt(af.F(S)),
            "defends": {a: af.defends(S, a) for a in srt(af.arguments)},
            "admissible": adm,
            "complete": comp,
            "stable": af.is_stable(S),
        }
    return out


def api_mechanism(body):
    _, attacks = parse_graph(body)
    types = parse_types(body)
    reports = {k: [str(a) for a in v] for k, v in body.get("reports", {}).items()}
    for k, r in reports.items():
        if not set(r) <= set(types.get(k, [])):
            raise ValueError(f"agent {k} may only reveal its own arguments")
    o = mechanism(attacks, list(reports.values()))
    revealed = set().union(*map(set, reports.values())) if reports else set()
    lab = ArgumentationFramework(revealed, [(x, y) for x, y in attacks if x in revealed and y in revealed])
    G = lab.grounded_extension()
    return {
        "outcome": srt(o),
        "labelling": lab.extension_to_labelling(G),
        "utilities": {k: utility(o, v) for k, v in types.items()},
    }


def api_best_response(body):
    _, attacks = parse_graph(body)
    types = parse_types(body)
    agent = str(body["agent"])
    others = {k: v for k, v in body.get("reports", types).items() if k != agent}
    br = best_responses(attacks, {k: set(v) for k, v in types.items()}, agent,
                        {k: set(v) for k, v in others.items()})
    return {
        "agent": agent,
        "best_utility": br["best_utility"],
        "truthful_utility": br["truthful_utility"],
        "truthful_is_best": br["truthful_is_best"],
        "table": [{"report": srt(r), "outcome": srt(o), "utility": u} for r, o, u in br["all"]],
    }


def api_strategic(body):
    args, attacks = parse_graph(body)
    types = parse_types(body)
    tset = {k: set(v) for k, v in types.items()}
    g = ArgumentationGame(attacks, tset, arguments=args)
    sp = check_theorem_53(None, None, game=g)
    c_walk = check_theorem_54(None, None, "walk", game=g)
    c_simple = check_theorem_54(None, None, "simple", game=g)
    res = analyse_instance(attacks, tset, arguments=args)
    viol = []
    simple_set = set(c_simple["violations"])
    for (ag, a, b) in c_walk["violations"]:
        viol.append({"agent": ag, "from": a, "to": b, "walk": odd_walk_witness(g, a, b),
                     "simple_path_too": (ag, a, b) in simple_set})
    witness = None
    if sp["violations"]:
        v = sp["violations"][0]
        witness = {k: (srt(v[k]) if isinstance(v[k], frozenset) else v[k]) for k in v}
    return {
        "strategyproof": sp["strategyproof"],
        "witness": witness,
        "cond_walk": c_walk["holds"],
        "cond_simple": c_simple["holds"],
        "violations": viol,
        "diagnosis": res.get("diagnosis"),
    }


def api_random(body):
    p = float(body.get("p", 0.25))
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    rng = random.Random(body.get("seed"))
    n, args, attacks, types = random_instance(rng, p, bool(body.get("self_attacks", True)))
    return {"name": f"Random instance (p={p})", "args": args, "attacks": attacks,
            "types": {k: srt(v) for k, v in types.items()}}


def api_experiments(_body):
    out = {}
    for key, d in (("self_attacks", "results"), ("no_self_attacks", "results_no_self_attacks")):
        path = os.path.join(ROOT, d, "summary.json")
        if os.path.exists(path):
            with open(path) as f:
                out[key] = json.load(f)
    if not out:
        raise ValueError("no results found -- run `python3 experiments.py` first")
    return out


ROUTES = {
    ("GET", "/api/examples"): api_examples,
    ("GET", "/api/experiments"): api_experiments,
    ("POST", "/api/analyze"): api_analyze,
    ("POST", "/api/mechanism"): api_mechanism,
    ("POST", "/api/best_response"): api_best_response,
    ("POST", "/api/strategic"): api_strategic,
    ("POST", "/api/random"): api_random,
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send_json(self, obj, status=HTTPStatus.OK):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self, method):
        path = self.path.split("?", 1)[0]
        fn = ROUTES.get((method, path))
        if fn is None:
            if method == "GET":
                return super().do_GET()
            return self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        try:
            body = {}
            if method == "POST":
                n = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(n) or b"{}")
            self._send_json(fn(body))
        except (ValueError, KeyError, TypeError) as e:
            self._send_json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def main():
    ap = argparse.ArgumentParser(description="Live browser demo of the argumentation engine")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://localhost:{a.port}/"
    print(f"Argumentation demo running at {url}   (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
