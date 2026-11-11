"""Part 1 tests -- assertions are the answers stated in the book (Ch. 5)."""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from argumentation import (ArgumentationFramework, CREDULOUS, IN, OUT, REJECTED, SKEPTICAL, UNDEC)
from argumentation.book_examples import exercise_1, exercise_2, fig_5_1, fig_5_2, fig_5_3

fs = frozenset


def sets(*xs):
    return {fs(x) for x in xs}


class TestFigure51(unittest.TestCase):
    def setUp(self):
        self.af = fig_5_1()

    def test_conflict_free(self):
        self.assertTrue(self.af.is_conflict_free({"a1", "a3", "a5"}))
        self.assertFalse(self.af.is_conflict_free({"a1", "a2"}))
        self.assertTrue(self.af.is_conflict_free(set()))

    def test_defence(self):
        # "In Figure 5.1, {α3, α5} defends α1"
        self.assertTrue(self.af.defends({"a3", "a5"}, "a1"))
        self.assertFalse(self.af.defends({"a3"}, "a1"))

    def test_characteristic(self):
        # Example 5.6: F({α3}) = F({α5}) = {α3, α5}
        self.assertEqual(self.af.F({"a3"}), fs({"a3", "a5"}))
        self.assertEqual(self.af.F({"a5"}), fs({"a3", "a5"}))
        self.assertEqual(self.af.F({"a1", "a3", "a5"}), fs({"a1", "a3", "a5"}))

    def test_admissible_example_5_5(self):
        self.assertEqual(set(self.af.admissible_sets()),
                         sets((), ("a3",), ("a5",), ("a3", "a5"), ("a1", "a3", "a5")))

    def test_complete_example_5_6(self):
        self.assertFalse(self.af.is_complete({"a3", "a5"}))      # defends α1 but omits it
        self.assertEqual(self.af.is_admissible_and_complete({"a3", "a5"}), (True, False))
        self.assertTrue(self.af.is_complete({"a1", "a3", "a5"}))
        self.assertEqual(set(self.af.complete_extensions()), sets(("a1", "a3", "a5")))

    def test_grounded_trace(self):
        # F^1(∅) = {α3, α5}; F^2(∅) = {α1, α3, α5} = F^3(∅)
        tr = self.af.grounded_trace()
        self.assertEqual(tr[0], fs({"a3", "a5"}))
        self.assertEqual(tr[1], fs({"a1", "a3", "a5"}))
        self.assertEqual(self.af.grounded_extension(), fs({"a1", "a3", "a5"}))

    def test_preferred_example_5_8(self):
        self.assertEqual(set(self.af.preferred_extensions()), sets(("a1", "a3", "a5")))


class TestFigure52(unittest.TestCase):
    def setUp(self):
        self.af = fig_5_2()

    def test_complete_example_5_7(self):
        self.assertEqual(set(self.af.complete_extensions()),
                         sets(("a3",), ("a1", "a3"), ("a2", "a3")))

    def test_grounded(self):
        self.assertEqual(self.af.grounded_extension(), fs({"a3"}))

    def test_preferred_example_5_8(self):
        self.assertEqual(set(self.af.preferred_extensions()), sets(("a1", "a3"), ("a2", "a3")))

    def test_three_labellings(self):
        labs = self.af.legal_labellings()
        self.assertEqual(len(labs), 3)
        LG = {"a1": UNDEC, "a2": UNDEC, "a3": IN}
        L1 = {"a1": IN, "a2": OUT, "a3": IN}
        L2 = {"a1": OUT, "a2": IN, "a3": IN}
        for L in (LG, L1, L2):
            self.assertIn(L, labs)

    def test_acceptance(self):
        self.assertEqual(self.af.acceptance_status("a3", "preferred"), SKEPTICAL)
        self.assertEqual(self.af.acceptance_status("a1", "preferred"), CREDULOUS)
        self.assertEqual(self.af.acceptance_status("a1", "grounded"), REJECTED)


class TestFigure53(unittest.TestCase):
    def test_grounded(self):
        self.assertEqual(fig_5_3().grounded_extension(), fs({"a", "c", "e"}))


class TestExercises(unittest.TestCase):
    def test_exercise_1(self):
        af = exercise_1()
        self.assertEqual(set(af.complete_extensions()), sets((), ("d",), ("a", "d"), ("b", "d")))
        self.assertEqual(af.grounded_extension(), fs())
        self.assertEqual(set(af.preferred_extensions()), sets(("a", "d"), ("b", "d")))
        self.assertEqual(set(af.stable_extensions()), sets(("a", "d"), ("b", "d")))
        self.assertEqual(set(af.semi_stable_extensions()), sets(("a", "d"), ("b", "d")))
        self.assertEqual(af.acceptance_status("d", "preferred"), SKEPTICAL)
        self.assertEqual(af.acceptance_status("c", "preferred"), REJECTED)

    def test_exercise_2_odd_cycle(self):
        af = exercise_2()
        self.assertEqual(af.complete_extensions(), [fs()])
        self.assertEqual(af.stable_extensions(), [])
        self.assertEqual(af.semi_stable_extensions(), [fs()])
        self.assertEqual(af.legal_labellings(), [{"a": UNDEC, "b": UNDEC, "c": UNDEC}])
        self.assertEqual(af.acceptance_status("a", "stable"), REJECTED)


class TestEdgeCases(unittest.TestCase):
    def test_self_attack(self):
        af = ArgumentationFramework({"a", "b"}, {("a", "a"), ("a", "b")})
        self.assertFalse(af.is_conflict_free({"a"}))
        self.assertEqual(af.grounded_extension(), fs())
        self.assertEqual(af.stable_extensions(), [])

    def test_empty(self):
        af = ArgumentationFramework(set())
        self.assertEqual(af.grounded_extension(), fs())
        self.assertEqual(af.complete_extensions(), [fs()])
        self.assertEqual(af.stable_extensions(), [fs()])

    def test_unknown_argument(self):
        with self.assertRaises(ValueError):
            ArgumentationFramework({"a"}, {("a", "z")})


class TestRandomProperties(unittest.TestCase):
    """Semantics-level invariants on random small graphs (self-loops allowed)."""

    def test_properties(self):
        rng = random.Random(7)
        for _ in range(300):
            n = rng.randint(0, 6)
            args = [f"x{k}" for k in range(n)]
            atts = {(a, b) for a in args for b in args if rng.random() < 0.3}
            af = ArgumentationFramework(args, atts)
            comp = af.complete_extensions()
            self.assertEqual(set(comp), set(af.complete_extensions_bruteforce()))
            for L in af.legal_labellings():
                self.assertTrue(af.is_legal_labelling(L))
                self.assertEqual(af.extension_to_labelling(af.labelling_to_extension(L)), L)
            G = af.grounded_extension()
            self.assertTrue(af.is_complete(G))
            self.assertTrue(all(G <= E for E in comp))
            pref = set(af.preferred_extensions())
            semi = set(af.semi_stable_extensions())
            stab = set(af.stable_extensions())
            self.assertTrue(stab <= semi <= pref <= set(comp))
            if stab:
                self.assertEqual(stab, semi)
            # maximal admissible sets = preferred
            adm = af.admissible_sets()
            max_adm = {A for A in adm if not any(A < B for B in adm)}
            self.assertEqual(max_adm, pref)


if __name__ == "__main__":
    unittest.main()
