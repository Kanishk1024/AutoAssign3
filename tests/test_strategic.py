"""Part 2 tests -- Examples 5.10 / 5.11 and Theorems 5.3 / 5.4."""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from argumentation import (ArgumentationFramework, ArgumentationGame, best_responses, check_theorem_53,
                           check_theorem_54, mechanism, utility)
from argumentation.book_examples import example_5_10, example_5_11

fs = frozenset


class TestExample510(unittest.TestCase):
    def setUp(self):
        self.att, self.types = example_5_10()

    def test_truthful_outcome(self):
        o = mechanism(self.att, list(self.types.values()))
        self.assertEqual(o, fs({"a1", "a3"}))
        # Correct utilities (the book swaps y's and z's argument sets -- misprint)
        self.assertEqual(utility(o, self.types["x"]), 1)
        self.assertEqual(utility(o, self.types["y"]), 0)   # A_y = {α2}
        self.assertEqual(utility(o, self.types["z"]), 1)   # A_z = {α3}

    def test_x_hides_a1(self):
        o = mechanism(self.att, [{"a4", "a5"}, {"a2"}, {"a3"}])
        self.assertEqual(o, fs({"a2", "a4", "a5"}))
        self.assertEqual(utility(o, self.types["x"]), 2)

    def test_best_response_x(self):
        br = best_responses(self.att, self.types, "x", {"y": {"a2"}, "z": {"a3"}})
        self.assertEqual(br["best_utility"], 2)
        self.assertEqual(br["truthful_utility"], 1)
        self.assertFalse(br["truthful_is_best"])
        self.assertIn(fs({"a4", "a5"}), br["best_reports"])

    def test_y_and_z_truthful_weakly_dominant(self):
        # "for both agents y and z, revealing their true types weakly dominates revealing nothing"
        for ag in ("y", "z"):
            for rx in ({"a1", "a4", "a5"}, {"a4", "a5"}, set()):
                others = {k: (rx if k == "x" else v) for k, v in self.types.items() if k != ag}
                br = best_responses(self.att, self.types, ag, others)
                self.assertTrue(br["truthful_is_best"])

    def test_not_strategyproof(self):
        res = check_theorem_53(self.att, self.types)
        self.assertFalse(res["strategyproof"])
        self.assertEqual(res["violations"][0]["agent"], "x")

    def test_condition_fails(self):
        res = check_theorem_54(self.att, self.types)
        self.assertFalse(res["holds"])
        self.assertIn(("x", "a1", "a4"), res["violations"])
        self.assertIn(("x", "a1", "a5"), res["violations"])


class TestExample511(unittest.TestCase):
    def setUp(self):
        self.att, self.types = example_5_11()

    def test_truthful_outcome(self):
        self.assertEqual(mechanism(self.att, list(self.types.values())), fs({"a1", "a4", "a5", "a6"}))

    def test_strategyproof_although_condition_fails(self):
        self.assertTrue(check_theorem_53(self.att, self.types)["strategyproof"])
        self.assertFalse(check_theorem_54(self.att, self.types)["holds"])

    def test_a6_not_a5_cancels_self_defeat(self):
        # Misprint: the book says α5 cancels the indirect self-defeat; it is α6.
        # Taking α6 away from x brings back Example 5.10's manipulation...
        att, types = example_5_11()
        types["x"] = {"a1", "a4", "a5"}
        self.assertFalse(check_theorem_53(att, types)["strategyproof"])
        # ...whereas taking α5 away does not.
        att, types = example_5_11()
        types["x"] = {"a1", "a4", "a6"}
        self.assertTrue(check_theorem_53(att, types)["strategyproof"])


class TestPathConditions(unittest.TestCase):
    def test_cycle_terminates_and_parity(self):
        # a -> b -> c -> a (odd cycle): every pair connected by an odd walk
        att = {("a", "b"), ("b", "c"), ("c", "a")}
        self.assertFalse(check_theorem_54(att, [{"a"}], include_same=True)["holds"])  # a ~> a length 3
        self.assertTrue(check_theorem_54(att, [{"a"}], include_same=False)["holds"])

    def test_even_cycle(self):
        # a <-> b: odd paths a->b, b->a only; a ~> a has even length only
        att = {("a", "b"), ("b", "a")}
        self.assertTrue(check_theorem_54(att, [{"a"}, {"b"}])["holds"])
        self.assertFalse(check_theorem_54(att, [{"a", "b"}])["holds"])

    def test_walk_vs_simple(self):
        # s -> x, x -> t ; odd 3-cycle x -> y -> z -> x.
        # simple paths s~>t: s,x,t (length 2, even) only.
        # walk s,x,y,z,x,t has length 5 (odd).
        att = {("s", "x"), ("x", "t"), ("x", "y"), ("y", "z"), ("z", "x")}
        types = [{"s", "t"}, {"x"}, {"y", "z"}]
        self.assertIn((0, "s", "t"), check_theorem_54(att, types, "walk")["violations"])
        self.assertNotIn((0, "s", "t"), check_theorem_54(att, types, "simple")["violations"])

    def test_odd_walk_witness(self):
        from argumentation.strategic import odd_walk_witness
        att = {("s", "x"), ("x", "t"), ("x", "y"), ("y", "z"), ("z", "x")}
        g = ArgumentationGame(att, [{"s", "t"}, {"x"}, {"y", "z"}])
        w = odd_walk_witness(g, "s", "t")
        self.assertEqual((w[0], w[-1]), ("s", "t"))
        self.assertEqual((len(w) - 1) % 2, 1)
        self.assertTrue(all((u, v) in att for u, v in zip(w, w[1:])))
        self.assertIsNone(odd_walk_witness(ArgumentationGame({("a", "b"), ("b", "a")}, [{"a", "b"}]), "a", "a"))
        self.assertEqual(odd_walk_witness(ArgumentationGame({("a", "a")}, [{"a"}]), "a", "a"), ["a", "a"])

    def test_self_attack_counts(self):
        att = {("a", "a")}
        self.assertFalse(check_theorem_54(att, [{"a"}])["holds"])


class TestTheoremsOnRandomInstances(unittest.TestCase):
    def test_bitmask_grounded_matches_engine(self):
        rng = random.Random(3)
        for _ in range(200):
            n = rng.randint(1, 7)
            args = [f"x{k}" for k in range(n)]
            att = {(a, b) for a in args for b in args if rng.random() < 0.3}
            g = ArgumentationGame(att, [set(args)])
            for m in g.submasks(g.full_mask):
                sub = g.to_set(m)
                expected = ArgumentationFramework(args, att).restrict(sub).grounded_extension()
                self.assertEqual(g.to_set(g.grounded_mask(m)), expected)

    def test_theorem_54_implies_53(self):
        """Every instance satisfying the condition must be strategyproof (Thm 5.4)."""
        rng = random.Random(11)
        checked = 0
        for _ in range(400):
            n = rng.randint(3, 7)
            args = [f"x{k}" for k in range(n)]
            att = {(a, b) for a in args for b in args if rng.random() < 0.2}
            types = [set(), set(), set()]
            for a in args:
                types[rng.randrange(3)].add(a)
            if check_theorem_54(att, types)["holds"]:
                checked += 1
                self.assertTrue(check_theorem_53(att, types)["strategyproof"], (att, types))
        self.assertGreater(checked, 10)


if __name__ == "__main__":
    unittest.main()
