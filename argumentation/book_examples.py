"""
Examples from Weiss (ed.), *Multiagent Systems* 2nd ed., Chapter 5
("Argumentation among Agents", I. Rahwan). Edges of Figures 5.1-5.5 were read
off the figures; the expected answers are the ones stated in the book text.

Arguments α1, α2, ... are written a1, a2, ... ; Fig 5.3 uses a..e as in the book.
"""

from .framework import ArgumentationFramework


def fig_5_1() -> ArgumentationFramework:
    """Figure 5.1 -- α1 has defeaters α2, α4, themselves defeated by α3, α5."""
    return ArgumentationFramework(
        {"a1", "a2", "a3", "a4", "a5"},
        {("a2", "a1"), ("a4", "a1"), ("a3", "a2"), ("a5", "a4")},
    )


def fig_5_2() -> ArgumentationFramework:
    """Figure 5.2 -- α1 and α2 defeat each other, α3 is unattacked."""
    return ArgumentationFramework({"a1", "a2", "a3"}, {("a1", "a2"), ("a2", "a1")})


def fig_5_3() -> ArgumentationFramework:
    """Figure 5.3(i) -- b->a, c->b, d->b, c<->d, e->d (grounded extension {a, c, e})."""
    return ArgumentationFramework(
        {"a", "b", "c", "d", "e"},
        {("b", "a"), ("c", "b"), ("d", "b"), ("c", "d"), ("d", "c"), ("e", "d")},
    )


def exercise_1() -> ArgumentationFramework:
    """End-of-chapter Exercise 1: A={a,b,c,d}, ->={(a,b),(b,a),(a,c),(b,c),(c,d),(d,c)}."""
    return ArgumentationFramework(
        {"a", "b", "c", "d"},
        {("a", "b"), ("b", "a"), ("a", "c"), ("b", "c"), ("c", "d"), ("d", "c")},
    )


def exercise_2() -> ArgumentationFramework:
    """End-of-chapter Exercise 2: odd cycle a->b->c->a."""
    return ArgumentationFramework({"a", "b", "c"}, {("a", "b"), ("b", "c"), ("c", "a")})


# ---------------------------------------------------------------------- #
# Strategic examples (Sec. 5.4)
# ---------------------------------------------------------------------- #
EX_5_10_ATTACKS = {("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a3", "a5")}
EX_5_10_TYPES = {"x": {"a1", "a4", "a5"}, "y": {"a2"}, "z": {"a3"}}

EX_5_11_ATTACKS = EX_5_10_ATTACKS | {("a6", "a3")}
EX_5_11_TYPES = {"x": {"a1", "a4", "a5", "a6"}, "y": {"a2"}, "z": {"a3"}}


def example_5_10():
    """Example 5.10 / Figure 5.4: (attacks, types)."""
    return set(EX_5_10_ATTACKS), {k: set(v) for k, v in EX_5_10_TYPES.items()}


def example_5_11():
    """Example 5.11 / Figure 5.5: (attacks, types)."""
    return set(EX_5_11_ATTACKS), {k: set(v) for k, v in EX_5_11_TYPES.items()}


FRAMEWORKS = {
    "Figure 5.1": fig_5_1,
    "Figure 5.2": fig_5_2,
    "Figure 5.3": fig_5_3,
    "Exercise 1": exercise_1,
    "Exercise 2": exercise_2,
}
