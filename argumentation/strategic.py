"""
Part 2 -- Strategic argumentation: the grounded direct argumentation mechanism.

Book: Weiss (ed.), *Multiagent Systems* 2nd ed., Ch. 5, Sec. 5.3-5.4
    Def 5.17  agent type A_i  (the arguments agent i can put forward)
    Def 5.21  grounded direct argumentation mechanism
              g(A°_1, ..., A°_I) = GR(<A°_1 ∪ ... ∪ A°_I, R>)
    Def 5.22  acceptability-maximising preferences: u_i(o, A_i) = |o ∩ A_i|
    Thm 5.3   strategyproof  <=>  ∀i ∀S⊆A_i ∀A_-i :
                  |A_i ∩ GR(A_i ∪ A_-i)| >= |A_i ∩ GR((A_i \\ S) ∪ A_-i)|
    Thm 5.4   sufficient condition: no agent holds α, β with an odd-length
              directed path α ~> β in the full graph.

Agents may only lie by *hiding* arguments: a report A°_i is a subset of A_i,
so "every combination of subsets the other agents could reveal" is the
product over j != i of the power sets of A_j.

Implementation note: for speed (the experiments evaluate tens of thousands of
report profiles) the inner loop uses bitmasks over at most a few dozen
arguments, and memoises the grounded extension per revealed set -- the
mechanism outcome only depends on the *union* of the reports.
"""

from __future__ import annotations

from collections import deque
from itertools import product
from typing import Dict, FrozenSet, Hashable, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .framework import ArgumentationFramework, fmt_set, _sort_key

Argument = Hashable
Attack = Tuple[Argument, Argument]
ArgSet = FrozenSet[Argument]


# ====================================================================== #
# Helpers: power sets
# ====================================================================== #
def subsets(s: Iterable[Argument]) -> List[ArgSet]:
    """All subsets of s (as frozensets), smallest first."""
    items = sorted(s, key=_sort_key)
    out = []
    for mask in range(1 << len(items)):
        out.append(frozenset(items[k] for k in range(len(items)) if mask >> k & 1))
    out.sort(key=lambda x: (len(x), sorted(map(_sort_key, x))))
    return out


# ====================================================================== #
# 1. The mechanism (Def 5.21)
# ====================================================================== #
def mechanism(attacks: Iterable[Attack], reports: Sequence[Iterable[Argument]]) -> ArgSet:
    """
    Grounded direct argumentation mechanism.

    attacks : the global attack (defeat) relation R
    reports : one revealed argument set A°_i per agent

    Returns the grounded extension of the graph induced by the union of the
    revealed arguments (attacks between unrevealed arguments are ignored).
    """
    revealed: Set[Argument] = set()
    for r in reports:
        revealed |= set(r)
    induced = [(x, y) for (x, y) in attacks if x in revealed and y in revealed]
    return ArgumentationFramework(revealed, induced).grounded_extension()


def utility(outcome: Iterable[Argument], A_i: Iterable[Argument]) -> int:
    """Acceptability-maximising utility (Def 5.22): number of i's arguments accepted."""
    return len(set(outcome) & set(A_i))


# ====================================================================== #
# A compiled, bitmask-based game used by the expensive checks
# ====================================================================== #
class ArgumentationGame:
    """
    The (global attack relation, agent types) pair, i.e. a strategic instance.

    attacks : iterable of (x, y) pairs over the full argument set
    types   : list (or dict name->set) of agent types A_i
    """

    def __init__(self, attacks: Iterable[Attack], types, arguments: Optional[Iterable[Argument]] = None):
        if isinstance(types, Mapping):
            self.agent_names = list(types.keys())
            self.types: List[ArgSet] = [frozenset(types[k]) for k in self.agent_names]
        else:
            self.types = [frozenset(t) for t in types]
            self.agent_names = list(range(len(self.types)))
        self.attacks = frozenset(attacks)

        args: Set[Argument] = set(arguments) if arguments is not None else set()
        for t in self.types:
            args |= t
        for (x, y) in self.attacks:
            args.add(x)
            args.add(y)
        self.arguments: List[Argument] = sorted(args, key=_sort_key)
        self.index = {a: k for k, a in enumerate(self.arguments)}
        self.n = len(self.arguments)
        self.full_mask = (1 << self.n) - 1

        # attackers_mask[k] = bitmask of attackers of argument k
        self.attackers_mask = [0] * self.n
        self.succ: List[List[int]] = [[] for _ in range(self.n)]
        for (x, y) in self.attacks:
            self.attackers_mask[self.index[y]] |= 1 << self.index[x]
            self.succ[self.index[x]].append(self.index[y])
        self.type_masks = [self.to_mask(t) for t in self.types]
        self.truthful_mask = 0
        for tm in self.type_masks:
            self.truthful_mask |= tm
        self._gr_cache: Dict[int, int] = {}

    # -- conversion -------------------------------------------------------
    def to_mask(self, s: Iterable[Argument]) -> int:
        m = 0
        for a in s:
            m |= 1 << self.index[a]
        return m

    def to_set(self, m: int) -> ArgSet:
        return frozenset(self.arguments[k] for k in range(self.n) if m >> k & 1)

    def framework(self) -> ArgumentationFramework:
        return ArgumentationFramework(self.arguments, self.attacks)

    @staticmethod
    def submasks(m: int) -> List[int]:
        """All submasks of m (including 0 and m)."""
        res = []
        s = m
        while True:
            res.append(s)
            if s == 0:
                break
            s = (s - 1) & m
        return res

    # -- grounded extension of the induced sub-graph ----------------------
    def grounded_mask(self, revealed: int) -> int:
        """
        Grounded extension of the graph induced by `revealed`, as a bitmask.
        Standard grounded-labelling algorithm: repeatedly label `in` every
        argument all of whose (revealed) attackers are `out`, then label `out`
        everything attacked by an `in` argument. Equals the least fixed point of F.
        """
        hit = self._gr_cache.get(revealed)
        if hit is not None:
            return hit
        IN = 0
        OUT = 0
        undecided = revealed
        changed = True
        while changed:
            changed = False
            new_in = 0
            m = undecided
            while m:
                low = m & -m
                k = low.bit_length() - 1
                if (self.attackers_mask[k] & revealed) & ~OUT == 0:
                    new_in |= low
                m ^= low
            if new_in:
                IN |= new_in
                undecided &= ~new_in
                changed = True
            # out: revealed arguments attacked by something in IN
            new_out = 0
            m = undecided
            while m:
                low = m & -m
                k = low.bit_length() - 1
                if self.attackers_mask[k] & IN:
                    new_out |= low
                m ^= low
            if new_out:
                OUT |= new_out
                undecided &= ~new_out
                changed = True
        self._gr_cache[revealed] = IN
        return IN

    def outcome(self, reports: Sequence[Iterable[Argument]]) -> ArgSet:
        """Mechanism outcome for a profile of reports (sets of arguments)."""
        m = 0
        for r in reports:
            m |= self.to_mask(r)
        return self.to_set(self.grounded_mask(m))

    def utility_mask(self, i: int, revealed: int) -> int:
        return bin(self.grounded_mask(revealed) & self.type_masks[i]).count("1")

    # -- others' report profiles ------------------------------------------
    def others_profiles(self, i: int) -> List[int]:
        """
        Every union of reports the agents j != i could make (each A°_j ⊆ A_j).
        Because the outcome only depends on the union, we enumerate unions;
        with disjoint types this is a bijection with the report profiles.
        """
        others = 0
        for j, tm in enumerate(self.type_masks):
            if j != i:
                others |= tm
        return self.submasks(others)

    def _disjoint(self) -> bool:
        if not hasattr(self, "_disj"):
            seen = 0
            disj = True
            for tm in self.type_masks:
                if seen & tm:
                    disj = False
                seen |= tm
            self._disj = disj
        return self._disj

    def _others_union_profiles(self, i: int) -> List[int]:
        """Unions of others' reports, exact even for overlapping types."""
        if self._disjoint():
            return self.others_profiles(i)
        per_agent = [self.submasks(tm) for j, tm in enumerate(self.type_masks) if j != i]
        unions = set()
        for combo in product(*per_agent):
            u = 0
            for c in combo:
                u |= c
            unions.add(u)
        return sorted(unions)


# ====================================================================== #
# 2. Best response
# ====================================================================== #
def best_responses(attacks: Iterable[Attack], types, i, others_reports) -> Dict[str, object]:
    """
    Enumerate every subset of A_i that agent i could reveal, given fixed
    reports by the others, and return the reports maximising i's utility.

    types          : list or dict of agent types
    i              : agent index (list) or name (dict)
    others_reports : list/dict of the other agents' reports (any entry for i is ignored)

    Returns dict with keys:
        best_utility, best_reports (list of frozensets),
        truthful_utility, truthful_is_best, all (list of (report, outcome, utility))
    """
    game = ArgumentationGame(attacks, types)
    idx = game.agent_names.index(i) if isinstance(types, Mapping) else i
    if isinstance(others_reports, Mapping):
        others = [others_reports[k] for k in game.agent_names if k != game.agent_names[idx]]
    else:
        others = [r for j, r in enumerate(others_reports) if j != idx]
    others_mask = 0
    for r in others:
        others_mask |= game.to_mask(r)

    A_i = game.types[idx]
    table = []
    for rep in subsets(A_i):
        o = game.grounded_mask(others_mask | game.to_mask(rep))
        table.append((rep, game.to_set(o), utility(game.to_set(o), A_i)))
    best = max(u for (_, _, u) in table)
    truthful_u = next(u for (r, _, u) in table if r == A_i)
    return {
        "agent": game.agent_names[idx],
        "best_utility": best,
        "best_reports": [r for (r, _, u) in table if u == best],
        "truthful_utility": truthful_u,
        "truthful_is_best": truthful_u == best,
        "all": table,
    }


# ====================================================================== #
# 3. Theorem 5.3 -- exhaustive strategyproofness check
# ====================================================================== #
def check_theorem_53(attacks: Iterable[Attack], types, game: Optional[ArgumentationGame] = None,
                     find_all: bool = False) -> Dict[str, object]:
    """
    Strategyproofness by Theorem 5.3: for every agent i, every combination of
    subsets the other agents could reveal, revealing all of A_i must be a best
    response (u_i(truth) >= u_i(any A°_i ⊆ A_i)).

    Returns {"strategyproof": bool, "violations": [...]} where each violation
    is a dict (agent, others_reveal, truthful_utility, better_report,
    better_utility, truthful_outcome, better_outcome). With find_all=False the
    search stops at the first violation.
    """
    g = game or ArgumentationGame(attacks, types)
    violations = []
    for i, tm in enumerate(g.type_masks):
        if tm == 0:
            continue
        my_reports = g.submasks(tm)
        for others in g._others_union_profiles(i):
            truth_u = g.utility_mask(i, others | tm)
            # find the best deviation
            best_u, best_rep = truth_u, None
            for rep in my_reports:
                if rep == tm:
                    continue
                u = g.utility_mask(i, others | rep)
                if u > best_u:
                    best_u, best_rep = u, rep
            if best_rep is not None:
                violations.append({
                    "agent": g.agent_names[i],
                    "others_reveal": g.to_set(others),
                    "truthful_utility": truth_u,
                    "truthful_outcome": g.to_set(g.grounded_mask(others | tm)),
                    "better_report": g.to_set(best_rep),
                    "hidden": g.to_set(tm & ~best_rep),
                    "better_utility": best_u,
                    "better_outcome": g.to_set(g.grounded_mask(others | best_rep)),
                })
                if not find_all:
                    return {"strategyproof": False, "violations": violations}
    return {"strategyproof": not violations, "violations": violations}


def is_strategyproof(attacks: Iterable[Attack], types, game: Optional[ArgumentationGame] = None) -> bool:
    """Boolean shortcut for check_theorem_53."""
    return bool(check_theorem_53(attacks, types, game)["strategyproof"])


# ====================================================================== #
# 4. Theorem 5.4 -- graph-theoretic sufficient condition
# ====================================================================== #
def odd_reachable_walk(game: ArgumentationGame, src: int) -> int:
    """
    Bitmask of arguments reachable from `src` by a directed walk of ODD length.

    Cycles are handled by searching the product graph (node, parity): it has
    2n states, each visited at most once, so the search always terminates even
    though walks around cycles can be arbitrarily long. A walk of odd length
    exists iff state (dst, 1) is reachable from (src, 0).
    """
    seen = [[False, False] for _ in range(game.n)]
    seen[src][0] = True
    dq = deque([(src, 0)])
    res = 0
    while dq:
        v, par = dq.popleft()
        for w in game.succ[v]:
            np_ = par ^ 1
            if not seen[w][np_]:
                seen[w][np_] = True
                if np_ == 1:
                    res |= 1 << w
                dq.append((w, np_))
    return res


def odd_walk_witness(game: ArgumentationGame, a: Argument, b: Argument) -> Optional[List[Argument]]:
    """
    A shortest odd-length directed walk a -> ... -> b (list of arguments, a first,
    b last), or None if none exists. Same (node, parity) BFS as
    odd_reachable_walk, with parent pointers to rebuild the walk.
    """
    src, dst = game.index[a], game.index[b]
    parent = {(src, 0): None}
    dq = deque([(src, 0)])
    while dq:
        state = dq.popleft()
        v, par = state
        for w in game.succ[v]:
            nxt = (w, par ^ 1)
            if nxt in parent:
                continue
            parent[nxt] = state
            if nxt == (dst, 1):
                walk = []
                s = nxt
                while s is not None:
                    walk.append(game.arguments[s[0]])
                    s = parent[s]
                return walk[::-1]
            dq.append(nxt)
    return None


def odd_reachable_simple(game: ArgumentationGame, src: int) -> int:
    """
    Bitmask of arguments reachable from `src` by an odd-length *simple* path
    (no repeated vertices; for dst == src: an odd simple cycle through src).
    Exhaustive DFS -- exponential in general but trivial for <= ~12 arguments.
    """
    res = 0

    def dfs(v: int, visited: int, length: int) -> None:
        nonlocal res
        for w in game.succ[v]:
            if w == src:
                if (length + 1) % 2 == 1:
                    res |= 1 << src
                continue
            if visited >> w & 1:
                continue
            if (length + 1) % 2 == 1:
                res |= 1 << w
            dfs(w, visited | (1 << w), length + 1)

    dfs(src, 1 << src, 0)
    return res


def check_theorem_54(attacks: Iterable[Attack], types, path_mode: str = "walk",
                     include_same: bool = True, game: Optional[ArgumentationGame] = None) -> Dict[str, object]:
    """
    Theorem 5.4 condition: no agent i holds α, β ∈ A_i such that there is an
    odd-length directed path from α to β in the FULL graph (all of A).

    path_mode    : "walk"   -- odd-length walk (vertices may repeat; parity BFS),
                   "simple" -- odd-length simple path (exhaustive DFS).
    include_same : also count α = β (self-attack, or odd cycle through α).

    Note that a path of length 1 is a direct attack, so the condition subsumes
    "each type is conflict-free".

    Returns {"holds": bool, "violations": [(agent, α, β), ...]}.
    """
    g = game or ArgumentationGame(attacks, types)
    reach = odd_reachable_walk if path_mode == "walk" else odd_reachable_simple
    if path_mode not in ("walk", "simple"):
        raise ValueError("path_mode must be 'walk' or 'simple'")
    violations = []
    for i, tm in enumerate(g.type_masks):
        m = tm
        while m:
            low = m & -m
            a = low.bit_length() - 1
            m ^= low
            hits = reach(g, a) & tm
            if not include_same:
                hits &= ~(1 << a)
            h = hits
            while h:
                lb = h & -h
                b = lb.bit_length() - 1
                h ^= lb
                violations.append((g.agent_names[i], g.arguments[a], g.arguments[b]))
    return {"holds": not violations, "violations": violations}


def theorem_54_holds(attacks: Iterable[Attack], types, path_mode: str = "walk") -> bool:
    """Boolean shortcut for check_theorem_54."""
    return bool(check_theorem_54(attacks, types, path_mode)["holds"])


# ====================================================================== #
# Diagnostics used by the experiments (why is an instance SP although the
# Theorem 5.4 condition fails?)
# ====================================================================== #
def diagnose_sp_despite_violation(game: ArgumentationGame, violations_walk, violations_simple) -> Dict[str, object]:
    """
    Classify why a strategyproof instance violates the Thm 5.4 condition.

    Categories (first that applies):
      walk-only          the odd connection exists only as a walk through an odd
                         cycle, never as a simple path (the condition is stricter
                         than needed in its walk reading).
      self-defeat-only   every violating pair is (α, α) where α attacks itself
                         directly or via an odd cycle; such α can never be
                         accepted, and hiding it never helps the owner.
      victim-never-in    no victim β of a violating pair is ever accepted in ANY
                         report profile -- there is nothing to gain by hiding.
      hiding-never-helps hiding a source α never turns any of its victims β from
                         not-accepted to accepted (the odd path is always cut or
                         neutralised by some other argument).
      compensated        hiding α can free a victim β, but the agent always loses
                         at least as much elsewhere (e.g. α itself, or another own
                         argument that α was defending -- the α6 effect of Ex. 5.11).
    """
    if not violations_simple:
        return {"category": "walk-only", "detail": "only odd walks, no odd simple paths"}

    pairs = [(game.agent_names.index(ag), game.index[a], game.index[b]) for (ag, a, b) in violations_walk]

    if all(a == b for (_, a, b) in pairs):
        return {"category": "self-defeat-only",
                "detail": "violations are self-defeating arguments only: "
                          + ", ".join(str(game.arguments[a]) for (_, a, _) in pairs)}

    proper = [(i, a, b) for (i, a, b) in pairs if a != b]
    victims = 0
    for (_, _, b) in proper:
        victims |= 1 << b

    # Is any victim ever accepted, in any revealed set?
    ever = 0
    for revealed in game.submasks(game.truthful_mask):
        ever |= game.grounded_mask(revealed) & victims
        if ever == victims:
            break
    if ever == 0:
        return {"category": "victim-never-in",
                "detail": "victims " + fmt_set(game.arguments[b] for (_, _, b) in proper)
                          + " are never accepted in any profile"}

    # Starting from the truthful report, does hiding a source ever free one of
    # its victims?  If yes, strategyproofness means the agent loses at least as
    # much as it gains -- record a witness of what is gained and what is lost.
    witness = None
    for (i, a, b) in proper:
        tm = game.type_masks[i]
        for others in game._others_union_profiles(i):
            with_a = game.grounded_mask(others | tm)
            without = game.grounded_mask(others | (tm & ~(1 << a)))
            if (without >> b & 1) and not (with_a >> b & 1):
                gained = without & ~with_a & tm
                lost = with_a & ~without & tm
                witness = (i, a, b, others, gained, lost)
                break
        if witness:
            break
    if witness is None:
        return {"category": "hiding-never-helps",
                "detail": "hiding a source from the truthful report never reinstates any of its victims "
                          "(the victim stays out/undec because of another attacker, e.g. an "
                          "unattacked or self-attacking argument)"}
    i, a, b, others, gained, lost = witness
    lost_set = game.to_set(lost)
    sub = "source-itself-lost" if lost == (1 << a) else "other-own-argument-lost"
    return {"category": "compensated",
            "subcategory": sub,
            "detail": (f"agent {game.agent_names[i]} hiding {game.arguments[a]} (others reveal "
                       f"{fmt_set(game.to_set(others))}) frees {fmt_set(game.to_set(gained))} "
                       f"but loses {fmt_set(lost_set)}")}


# ====================================================================== #
# Convenience: full analysis of one instance
# ====================================================================== #
def analyse_instance(attacks: Iterable[Attack], types, arguments: Optional[Iterable[Argument]] = None) -> Dict[str, object]:
    g = ArgumentationGame(attacks, types, arguments)
    sp = check_theorem_53(None, None, game=g)
    c_walk = check_theorem_54(None, None, "walk", game=g)
    c_simple = check_theorem_54(None, None, "simple", game=g)
    res = {
        "strategyproof": sp["strategyproof"],
        "counterexample": sp["violations"][0] if sp["violations"] else None,
        "cond_walk": c_walk["holds"],
        "cond_simple": c_simple["holds"],
        "violations_walk": c_walk["violations"],
        "violations_simple": c_simple["violations"],
        "truthful_outcome": g.to_set(g.grounded_mask(g.truthful_mask)),
    }
    if res["strategyproof"] and not res["cond_walk"]:
        res["diagnosis"] = diagnose_sp_despite_violation(g, c_walk["violations"], c_simple["violations"])
    return res
