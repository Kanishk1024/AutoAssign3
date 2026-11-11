"""
Part 1 -- Argumentation Engine.

Abstract argumentation frameworks <A, ->> following Chapter 5 ("Argumentation
among Agents", I. Rahwan) of Weiss (ed.), *Multiagent Systems*, 2nd ed.

Definitions implemented (book numbering):
    Def 5.1  argumentation framework
    Def 5.2  conflict-free sets, defence
    Def 5.3  characteristic function F
    Def 5.4  admissible sets
    Def 5.5  complete extensions
    Def 5.6  legal labellings (in / out / undec)
    Def 5.7  grounded, preferred, stable, semi-stable extensions (+ Table 5.1)
    Def 5.8  skeptical / credulous acceptance, rejection
"""

from __future__ import annotations

from itertools import combinations
from typing import Dict, FrozenSet, Hashable, Iterable, List, Optional, Set, Tuple

Argument = Hashable
Attack = Tuple[Argument, Argument]
ArgSet = FrozenSet[Argument]
Labelling = Dict[Argument, str]

IN, OUT, UNDEC = "in", "out", "undec"

SEMANTICS = ("grounded", "complete", "preferred", "stable", "semi-stable")

SKEPTICAL = "skeptically accepted"
CREDULOUS = "credulously accepted"
REJECTED = "rejected"


def _sort_key(x):
    """Natural-ish ordering so that a2 < a10 and mixed types do not crash."""
    s = str(x)
    head = s.rstrip("0123456789")
    tail = s[len(head):]
    return (head, int(tail) if tail else -1, s)


def fmt_set(s: Iterable[Argument]) -> str:
    """Pretty-print a set of arguments: {a1, a3}."""
    return "{" + ", ".join(str(a) for a in sorted(s, key=_sort_key)) + "}"


class ArgumentationFramework:
    """
    An argumentation framework <A, ->> (Def 5.1): a finite set of arguments A
    and a defeat/attack relation -> subset of A x A.

    >>> af = ArgumentationFramework({"a", "b"}, {("a", "b")})
    >>> af.grounded_extension() == frozenset({"a"})
    True
    """

    # ------------------------------------------------------------------ #
    # 1. Construction
    # ------------------------------------------------------------------ #
    def __init__(self, arguments: Iterable[Argument], attacks: Iterable[Attack] = ()):
        self.arguments: ArgSet = frozenset(arguments)
        atts = set()
        for (x, y) in attacks:
            if x not in self.arguments or y not in self.arguments:
                raise ValueError(f"attack ({x}, {y}) mentions an unknown argument")
            atts.add((x, y))
        self.attacks: FrozenSet[Attack] = frozenset(atts)

        # attackers[a] = a^-   ;   attacked_by[a] = {a}^+
        self.attackers: Dict[Argument, ArgSet] = {}
        self.attacked_by: Dict[Argument, ArgSet] = {}
        tmp_in: Dict[Argument, Set[Argument]] = {a: set() for a in self.arguments}
        tmp_out: Dict[Argument, Set[Argument]] = {a: set() for a in self.arguments}
        for (x, y) in self.attacks:
            tmp_in[y].add(x)
            tmp_out[x].add(y)
        for a in self.arguments:
            self.attackers[a] = frozenset(tmp_in[a])
            self.attacked_by[a] = frozenset(tmp_out[a])

        self._cache: Dict[str, object] = {}

    def __repr__(self) -> str:
        atts = ", ".join(f"{x}->{y}" for (x, y) in sorted(self.attacks, key=lambda e: (_sort_key(e[0]), _sort_key(e[1]))))
        return f"ArgumentationFramework(A={fmt_set(self.arguments)}, attacks=[{atts}])"

    def attacks_arg(self, x: Argument, y: Argument) -> bool:
        """x -> y ?"""
        return (x, y) in self.attacks

    def restrict(self, subset: Iterable[Argument]) -> "ArgumentationFramework":
        """Sub-framework induced by `subset` (used by the mechanism in Part 2)."""
        sub = frozenset(subset) & self.arguments
        return ArgumentationFramework(sub, [(x, y) for (x, y) in self.attacks if x in sub and y in sub])

    def _check(self, S: Iterable[Argument]) -> ArgSet:
        S = frozenset(S)
        unknown = S - self.arguments
        if unknown:
            raise ValueError(f"unknown arguments {fmt_set(unknown)}")
        return S

    # ------------------------------------------------------------------ #
    # S+  (arguments defeated by S)
    # ------------------------------------------------------------------ #
    def plus(self, S: Iterable[Argument]) -> ArgSet:
        """S+ = { b | a -> b for some a in S }."""
        S = self._check(S)
        out: Set[Argument] = set()
        for a in S:
            out |= self.attacked_by[a]
        return frozenset(out)

    def minus(self, a: Argument) -> ArgSet:
        """a- = { b | b -> a }."""
        return self.attackers[a]

    # ------------------------------------------------------------------ #
    # 2. Conflict-freeness (Def 5.2)
    # ------------------------------------------------------------------ #
    def is_conflict_free(self, S: Iterable[Argument]) -> bool:
        """S is conflict-free iff S ∩ S+ = ∅ (no member attacks a member, itself included)."""
        S = self._check(S)
        return not (S & self.plus(S))

    # ------------------------------------------------------------------ #
    # 3. Defence (Def 5.2)
    # ------------------------------------------------------------------ #
    def defends(self, S: Iterable[Argument], a: Argument) -> bool:
        """S defends a (a is acceptable w.r.t. S) iff a- ⊆ S+."""
        S = self._check(S)
        if a not in self.arguments:
            raise ValueError(f"unknown argument {a}")
        return self.attackers[a] <= self.plus(S)

    # ------------------------------------------------------------------ #
    # 4. Characteristic function (Def 5.3)
    # ------------------------------------------------------------------ #
    def characteristic(self, S: Iterable[Argument]) -> ArgSet:
        """F(S) = { a ∈ A | S defends a }."""
        S = self._check(S)
        Sp = self.plus(S)
        return frozenset(a for a in self.arguments if self.attackers[a] <= Sp)

    F = characteristic  # short alias, as in the book

    # ------------------------------------------------------------------ #
    # 5. Admissible / complete (Def 5.4, 5.5)
    # ------------------------------------------------------------------ #
    def is_admissible(self, S: Iterable[Argument]) -> bool:
        """S is admissible iff S is conflict-free and S ⊆ F(S)."""
        S = self._check(S)
        return self.is_conflict_free(S) and S <= self.characteristic(S)

    def is_complete(self, S: Iterable[Argument]) -> bool:
        """S is a complete extension iff S is conflict-free and S = F(S)."""
        S = self._check(S)
        return self.is_conflict_free(S) and S == self.characteristic(S)

    def is_admissible_and_complete(self, S: Iterable[Argument]) -> Tuple[bool, bool]:
        """Item 5 of the assignment: returns (admissible?, complete?)."""
        return self.is_admissible(S), self.is_complete(S)

    def is_stable(self, S: Iterable[Argument]) -> bool:
        """S is stable iff S is conflict-free and S+ = A \\ S."""
        S = self._check(S)
        return self.is_conflict_free(S) and self.plus(S) == self.arguments - S

    # ------------------------------------------------------------------ #
    # 6A. Grounded extension (Def 5.7): least fixed point of F
    # ------------------------------------------------------------------ #
    def grounded_trace(self) -> List[ArgSet]:
        """[F^1(∅), F^2(∅), ...] up to and including the fixed point."""
        trace: List[ArgSet] = []
        S: ArgSet = frozenset()
        while True:
            nxt = self.characteristic(S)
            trace.append(nxt)
            if nxt == S:
                return trace
            S = nxt

    def grounded_extension(self) -> ArgSet:
        """The unique grounded extension = least fixed point of F, reached from ∅."""
        if "grounded" not in self._cache:
            self._cache["grounded"] = self.grounded_trace()[-1]
        return self._cache["grounded"]  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # 6D. Legal labellings (Def 5.6)
    # ------------------------------------------------------------------ #
    def is_legal_labelling(self, L: Labelling) -> bool:
        """
        L is legal iff for every argument a:
            L(a) = out  <=>  some attacker of a is in
            L(a) = in   <=>  all attackers of a are out
            otherwise undec.
        """
        if set(L) != set(self.arguments):
            return False
        for a in self.arguments:
            att = self.attackers[a]
            some_in = any(L[b] == IN for b in att)
            all_out = all(L[b] == OUT for b in att)
            expected = OUT if some_in else (IN if all_out else UNDEC)
            if L[a] != expected:
                return False
        return True

    def legal_labellings(self) -> List[Labelling]:
        """
        All legal in/out/undec labellings, by backtracking search with
        constraint propagation-style pruning: after each assignment, every
        argument whose own label and all attackers' labels are fixed is
        checked against Def 5.6.
        """
        if "labellings" in self._cache:
            return [dict(L) for L in self._cache["labellings"]]  # type: ignore[union-attr]

        order = sorted(self.arguments, key=_sort_key)
        pos = {a: i for i, a in enumerate(order)}
        # For each argument a, the arguments whose legality check becomes possible
        # once position i is filled: a can be checked when a and all its attackers
        # have been assigned, i.e. at index max(pos[a], pos[attackers]).
        ready_at: Dict[int, List[Argument]] = {i: [] for i in range(len(order))}
        for a in order:
            idx = max([pos[a]] + [pos[b] for b in self.attackers[a]])
            ready_at[idx].append(a)

        results: List[Labelling] = []
        L: Labelling = {}

        def ok(a: Argument) -> bool:
            att = self.attackers[a]
            some_in = any(L[b] == IN for b in att)
            all_out = all(L[b] == OUT for b in att)
            expected = OUT if some_in else (IN if all_out else UNDEC)
            return L[a] == expected

        def rec(i: int) -> None:
            if i == len(order):
                results.append(dict(L))
                return
            a = order[i]
            for lab in (IN, OUT, UNDEC):
                L[a] = lab
                if all(ok(b) for b in ready_at[i]):
                    rec(i + 1)
                del L[a]

        rec(0)
        self._cache["labellings"] = results
        return [dict(x) for x in results]

    @staticmethod
    def labelling_to_extension(L: Labelling) -> ArgSet:
        """in(L)."""
        return frozenset(a for a, lab in L.items() if lab == IN)

    def extension_to_labelling(self, S: Iterable[Argument]) -> Labelling:
        """Caminada's Ext2Lab: in = S, out = S+, undec = rest."""
        S = self._check(S)
        Sp = self.plus(S)
        return {a: (IN if a in S else OUT if a in Sp else UNDEC) for a in self.arguments}

    # ------------------------------------------------------------------ #
    # 6B. Complete extensions
    # ------------------------------------------------------------------ #
    def complete_extensions(self) -> List[ArgSet]:
        """All complete extensions = in-sets of all legal labellings (Caminada)."""
        exts = {self.labelling_to_extension(L) for L in self.legal_labellings()}
        return sorted(exts, key=lambda s: (len(s), sorted(map(_sort_key, s))))

    def complete_extensions_bruteforce(self) -> List[ArgSet]:
        """Reference implementation: test every subset with is_complete (for cross-checking)."""
        args = sorted(self.arguments, key=_sort_key)
        res = []
        for k in range(len(args) + 1):
            for c in combinations(args, k):
                if self.is_complete(c):
                    res.append(frozenset(c))
        return res

    def admissible_sets(self) -> List[ArgSet]:
        """All admissible sets (brute force; fine for small frameworks)."""
        args = sorted(self.arguments, key=_sort_key)
        res = []
        for k in range(len(args) + 1):
            for c in combinations(args, k):
                if self.is_admissible(c):
                    res.append(frozenset(c))
        return res

    # ------------------------------------------------------------------ #
    # 6C. Preferred, stable, semi-stable (Def 5.7, Table 5.1)
    # ------------------------------------------------------------------ #
    def preferred_extensions(self) -> List[ArgSet]:
        """Maximal (w.r.t. ⊆) complete extensions."""
        comp = self.complete_extensions()
        return [E for E in comp if not any(E < E2 for E2 in comp)]

    def stable_extensions(self) -> List[ArgSet]:
        """Complete extensions with S+ = A \\ S (labellings with empty undec)."""
        return [E for E in self.complete_extensions() if self.plus(E) == self.arguments - E]

    def semi_stable_extensions(self) -> List[ArgSet]:
        """Complete extensions S whose range S ∪ S+ is maximal (minimal undec)."""
        comp = self.complete_extensions()
        rng = {E: E | self.plus(E) for E in comp}
        return [E for E in comp if not any(rng[E] < rng[E2] for E2 in comp)]

    def extensions(self, semantics: str) -> List[ArgSet]:
        """Extensions under a named semantics."""
        s = semantics.lower().replace("_", "-")
        if s == "grounded":
            return [self.grounded_extension()]
        if s == "complete":
            return self.complete_extensions()
        if s == "preferred":
            return self.preferred_extensions()
        if s == "stable":
            return self.stable_extensions()
        if s in ("semi-stable", "semistable"):
            return self.semi_stable_extensions()
        raise ValueError(f"unknown semantics {semantics!r}; choose from {SEMANTICS}")

    def all_extensions(self) -> Dict[str, List[ArgSet]]:
        """Item 6C: every extension under every semantics."""
        return {s: self.extensions(s) for s in SEMANTICS}

    # ------------------------------------------------------------------ #
    # 6E. Acceptance status (Def 5.8)
    # ------------------------------------------------------------------ #
    def acceptance_status(self, a: Argument, semantics: str = "preferred") -> str:
        """
        skeptically accepted  : a in every extension
        credulously accepted  : a in some (but not every) extension
        rejected              : a in no extension

        Note: if there are no extensions (stable semantics on an odd cycle)
        nothing is in "some" extension, so every argument is rejected.
        (Vacuous skeptical acceptance is deliberately not reported.)
        """
        if a not in self.arguments:
            raise ValueError(f"unknown argument {a}")
        exts = self.extensions(semantics)
        if not exts or not any(a in E for E in exts):
            return REJECTED
        if all(a in E for E in exts):
            return SKEPTICAL
        return CREDULOUS

    def acceptance_report(self, semantics: Optional[Iterable[str]] = None) -> Dict[Argument, Dict[str, str]]:
        """Status of every argument under every (requested) semantics."""
        sems = list(semantics) if semantics else list(SEMANTICS)
        return {a: {s: self.acceptance_status(a, s) for s in sems}
                for a in sorted(self.arguments, key=_sort_key)}

    # ------------------------------------------------------------------ #
    # Pretty printing helpers (used by the demo)
    # ------------------------------------------------------------------ #
    def labelling_str(self, L: Labelling) -> str:
        parts = []
        for lab in (IN, OUT, UNDEC):
            parts.append(f"{lab}={fmt_set(a for a in L if L[a] == lab)}")
        return "  ".join(parts)
