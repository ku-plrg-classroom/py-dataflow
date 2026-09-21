"""100 checks of the worklist engine and three classic analyses.

Small programs checked point by point, including the corner cases that bite: parameters, re-assignment, `x[i] = e`, nested loops, an `if`
without `else`, list literals, and an expression that kills itself.

Each program point gets one test, so a failure names the program, the
analysis, and the point (see the edge list printed with it).
"""

import unittest

from syntax import parse
from cfg import build, dominators as cfg_dominators
from dataflow import (solve, dominators, reaching_definitions, live_variables,
                      available_expressions, PARAM)


# ---------------------------------------------------------------- programs

PROGRAMS = {
    # examples/loop.py: one loop, one variable
    'loop': 'def f(n):\n    i = 0\n    while i < n:\n        i = i + 1\n    return i\n',
    # one dead and one live assignment before a branch
    'branch': 'def f(a, b):\n    x = a * 2\n    y = b * 2\n    if a < b:\n        x = y\n    else:\n        x = b\n    return x\n',
    # a + b is lost on one branch, c * 2 is kept
    'shared': 'def f(a, b, c):\n    x = (a + b) + (c * 2)\n    if a < b:\n        a = 0\n    y = (a + b) + 3\n    z = 1 + (c * 2)\n    return y + z\n',
    # a diamond: two branches that meet again
    'diamond': 'def f(x):\n    if 0 < x:\n        y = 1\n    else:\n        y = 2\n        y = y * 2\n    return y\n',
    # examples/sum.py: two variables around one loop
    'sum': 'def sum(n):\n    i = 0\n    s = 0\n    while i <= n:\n        s = s + i\n        i = i + 1\n    return s\n',
    # examples/total.py: a list, an index read, an if without else
    'total': 'def total(n):\n    xs = [3, -1, 4]\n    s = 0\n    i = 0\n    while i < n:\n        if 0 <= xs[i]:\n            s = s + xs[i]\n        i = i + 1\n    return s\n',
    # two loops, one inside the other
    'nested': 'def f(n):\n    i = 0\n    while i < n:\n        j = 0\n        while j < n:\n            j = j + 1\n        i = i + 1\n    return i\n',
    # x = n is dead, yet n is read
    'dead': 'def f(n):\n    x = n\n    x = 1\n    return x\n',
    # the same command on two edges is two definitions
    'twice': 'def f(c):\n    x = 1\n    if c < 0:\n        x = 1\n    return x\n',
    # xs[0] = v writes the list, not the variable
    'index': 'def f(v):\n    xs = [0]\n    xs[0] = v\n    return xs\n',
    # after x = x + 1, x + 1 is stale
    'selfkill': 'def f(x):\n    x = x + 1\n    return x\n',
    # a condition reads its variables
    'cond': 'def f(a, b):\n    if a < b:\n        c = 1\n    else:\n        c = 2\n    return c\n',
    # a * b survives a loop that does not touch a or b
    'invariant': 'def f(a, b, n):\n    s = a * b\n    i = 0\n    while i < n:\n        i = i + 1\n    return s\n',
}


# ----------------------------------------------------------------- helpers

def graph(name):
    return build(parse(PROGRAMS[name]))


def expr(text):
    """The AST of the expression `text`."""
    return parse(f"def g():\n    t = {text}\n    return t\n").body[0].e


def exprs(*texts):
    return frozenset(expr(t) for t in texts)


def describe(g):
    return "\n".join(f"  edge {e.id}: {e.src} --{e}--> {e.dst}" for e in g.edges)


def check(test, name, make, expected):
    """One test per program point, from a table of expected sets."""
    g = graph(name)
    data = solve(g, make(g))
    for p, want in expected.items():
        with test.subTest(point=p):
            test.assertEqual(data[p], frozenset(want),
                             f"{make.__name__} on {name!r} at point {p}\n{describe(g)}")


# -------------------------------------------------------------- expected
# Sets at every program point. Points are numbered as cfg.build numbers them:
# 0 is the entry, 1 the exit, and the rest follow the program text.

REACHING_DEFINITIONS = {
    'loop': {
        0: {("n", PARAM)},
        1: {("i", 0), ("i", 2), ("n", PARAM)},
        2: {("i", 0), ("i", 2), ("n", PARAM)},
        3: {("i", 0), ("i", 2), ("n", PARAM)},
    },
    'branch': {
        0: {("a", PARAM), ("b", PARAM)},
        1: {("a", PARAM), ("b", PARAM), ("x", 3), ("x", 5), ("y", 1)},
        2: {("a", PARAM), ("b", PARAM), ("x", 0)},
        3: {("a", PARAM), ("b", PARAM), ("x", 0), ("y", 1)},
        4: {("a", PARAM), ("b", PARAM), ("x", 0), ("y", 1)},
        5: {("a", PARAM), ("b", PARAM), ("x", 0), ("y", 1)},
    },
    'sum': {
        0: {("n", PARAM)},
        1: {("i", 0), ("i", 4), ("n", PARAM), ("s", 1), ("s", 3)},
        2: {("i", 0), ("n", PARAM)},
        3: {("i", 0), ("i", 4), ("n", PARAM), ("s", 1), ("s", 3)},
        4: {("i", 0), ("i", 4), ("n", PARAM), ("s", 1), ("s", 3)},
        5: {("i", 0), ("i", 4), ("n", PARAM), ("s", 3)},
    },
    'nested': {
        0: {("n", PARAM)},
        1: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
        2: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
        3: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
        4: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
        5: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
        6: {("i", 0), ("i", 6), ("j", 2), ("j", 4), ("n", PARAM)},
    },
    'dead': {
        0: {("n", PARAM)},
        1: {("n", PARAM), ("x", 1)},
        2: {("n", PARAM), ("x", 0)},
    },
    'twice': {
        0: {("c", PARAM)},
        1: {("c", PARAM), ("x", 0), ("x", 2)},
        2: {("c", PARAM), ("x", 0)},
        3: {("c", PARAM), ("x", 0)},
    },
    'index': {
        0: {("v", PARAM)},
        1: {("v", PARAM), ("xs", 0)},
        2: {("v", PARAM), ("xs", 0)},
    },
}

LIVE_VARIABLES = {
    'branch': {
        0: {"a", "b"},
        1: {"x"},
        2: {"a", "b"},
        3: {"a", "b", "y"},
        4: {"y"},
        5: {"b"},
    },
    'loop': {
        0: {"n"},
        1: {"i"},
        2: {"i", "n"},
        3: {"i", "n"},
    },
    'sum': {
        0: {"n"},
        1: {"s"},
        2: {"i", "n"},
        3: {"i", "n", "s"},
        4: {"i", "n", "s"},
        5: {"i", "n", "s"},
    },
    'total': {
        0: {"n"},
        1: {"s"},
        2: {"n", "xs"},
        3: {"n", "s", "xs"},
        4: {"i", "n", "s", "xs"},
        5: {"i", "n", "s", "xs"},
        6: {"i", "n", "s", "xs"},
        7: {"i", "n", "s", "xs"},
    },
    'dead': {
        0: {"n"},
        1: {"x"},
        2: set(),
    },
    'cond': {
        0: {"a", "b"},
        1: {"c"},
        2: set(),
        3: set(),
    },
}

AVAILABLE_EXPRESSIONS = {
    'shared': {
        0: exprs(),
        1: exprs("1 + c * 2", "a + b", "a + b + 3", "c * 2"),
        2: exprs("a + b", "a + b + c * 2", "c * 2"),
        3: exprs("c * 2"),
        4: exprs("a + b", "a + b + c * 2", "a < b", "c * 2"),
        5: exprs("a + b", "a + b + 3", "c * 2"),
    },
    'diamond': {
        0: exprs(),
        1: exprs("0 < x"),
        2: exprs("0 < x"),
        3: exprs("0 < x", "not 0 < x"),
        4: exprs("0 < x", "not 0 < x"),
    },
    'selfkill': {
        0: exprs(),
        1: exprs(),
    },
    'invariant': {
        0: exprs(),
        1: exprs("a * b", "i < n", "not i < n"),
        2: exprs("a * b"),
        3: exprs("a * b"),
        4: exprs("a * b", "i < n"),
    },
    'total': {
        0: exprs(),
        1: exprs("i < n", "not i < n"),
        2: exprs(),
        3: exprs(),
        4: exprs(),
        5: exprs("i < n"),
        6: exprs("0 <= xs[i]", "i < n", "xs[i]"),
        7: exprs("0 <= xs[i]", "i < n", "xs[i]"),
    },
}


# ------------------------------------------------------------------ engine

class TestEngine(unittest.TestCase):
    def test_one_set_per_point(self):
        for name in PROGRAMS:
            g = graph(name)
            for mk in (dominators, reaching_definitions, live_variables,
                       available_expressions):
                with self.subTest(program=name, analysis=mk.__name__):
                    data = solve(g, mk(g))
                    self.assertEqual(set(data), set(g.nodes))
                    for p in g:
                        self.assertIsInstance(data[p], frozenset)

    def test_the_result_is_a_fixpoint(self):
        """One more round from the answer changes nothing."""
        for name in PROGRAMS:
            g = graph(name)
            for mk in (reaching_definitions, live_variables, available_expressions):
                a = mk(g)
                data = solve(g, a)
                for e in g.edges:
                    p, q = (e.src, e.dst) if a.forward else (e.dst, e.src)
                    with self.subTest(program=name, analysis=mk.__name__, edge=str(e)):
                        self.assertEqual(a.join(data[q], a.transfer(e, data[p])), data[q])

    def test_the_start_point_keeps_its_initial_data(self):
        g = graph("sum")
        self.assertEqual(solve(g, reaching_definitions(g))[g.entry], frozenset({("n", PARAM)}))
        self.assertEqual(solve(g, live_variables(g))[g.exit], frozenset({"s"}))
        self.assertEqual(solve(g, available_expressions(g))[g.entry], frozenset())

    def test_solving_twice_gives_the_same_answer(self):
        g = graph("total")
        for mk in (reaching_definitions, live_variables, available_expressions):
            with self.subTest(analysis=mk.__name__):
                self.assertEqual(solve(g, mk(g)), solve(g, mk(g)))

    def test_an_empty_body_is_one_pass_edge(self):
        g = build(parse("def f(x):\n    return x\n"))
        self.assertEqual(solve(g, reaching_definitions(g))[g.exit], frozenset({("x", PARAM)}))
        self.assertEqual(solve(g, live_variables(g))[g.entry], frozenset({"x"}))
        self.assertEqual(solve(g, available_expressions(g))[g.exit], frozenset())


# -------------------------------------------------------------- dominators

class TestDominators(unittest.TestCase):
    """The finished example must agree with the dominator algorithm in cfg.py."""

    def check(self, name):
        g = graph(name)
        self.assertEqual({p: set(d) for p, d in solve(g, dominators(g)).items()},
                         {p: set(d) for p, d in cfg_dominators(g).items()})

    def test_diamond(self): self.check("diamond")
    def test_loop(self): self.check("loop")
    def test_branch(self): self.check("branch")
    def test_sum(self): self.check("sum")
    def test_nested(self): self.check("nested")


# -------------------------------------------------- reaching definitions

class TestReachingDefinitions(unittest.TestCase):
    # examples/loop.py: one loop, one variable
    def test_loop_point_0(self):
        check(self, 'loop', reaching_definitions, {0: REACHING_DEFINITIONS['loop'][0]})
    def test_loop_point_1(self):
        check(self, 'loop', reaching_definitions, {1: REACHING_DEFINITIONS['loop'][1]})
    def test_loop_point_2(self):
        check(self, 'loop', reaching_definitions, {2: REACHING_DEFINITIONS['loop'][2]})
    def test_loop_point_3(self):
        check(self, 'loop', reaching_definitions, {3: REACHING_DEFINITIONS['loop'][3]})

    # one dead and one live assignment before a branch
    def test_branch_point_0(self):
        check(self, 'branch', reaching_definitions, {0: REACHING_DEFINITIONS['branch'][0]})
    def test_branch_point_1(self):
        check(self, 'branch', reaching_definitions, {1: REACHING_DEFINITIONS['branch'][1]})
    def test_branch_point_2(self):
        check(self, 'branch', reaching_definitions, {2: REACHING_DEFINITIONS['branch'][2]})
    def test_branch_point_3(self):
        check(self, 'branch', reaching_definitions, {3: REACHING_DEFINITIONS['branch'][3]})
    def test_branch_point_4(self):
        check(self, 'branch', reaching_definitions, {4: REACHING_DEFINITIONS['branch'][4]})
    def test_branch_point_5(self):
        check(self, 'branch', reaching_definitions, {5: REACHING_DEFINITIONS['branch'][5]})

    # examples/sum.py: two variables around one loop
    def test_sum_point_0(self):
        check(self, 'sum', reaching_definitions, {0: REACHING_DEFINITIONS['sum'][0]})
    def test_sum_point_1(self):
        check(self, 'sum', reaching_definitions, {1: REACHING_DEFINITIONS['sum'][1]})
    def test_sum_point_2(self):
        check(self, 'sum', reaching_definitions, {2: REACHING_DEFINITIONS['sum'][2]})
    def test_sum_point_3(self):
        check(self, 'sum', reaching_definitions, {3: REACHING_DEFINITIONS['sum'][3]})
    def test_sum_point_4(self):
        check(self, 'sum', reaching_definitions, {4: REACHING_DEFINITIONS['sum'][4]})
    def test_sum_point_5(self):
        check(self, 'sum', reaching_definitions, {5: REACHING_DEFINITIONS['sum'][5]})

    # two loops, one inside the other
    def test_nested_point_0(self):
        check(self, 'nested', reaching_definitions, {0: REACHING_DEFINITIONS['nested'][0]})
    def test_nested_point_1(self):
        check(self, 'nested', reaching_definitions, {1: REACHING_DEFINITIONS['nested'][1]})
    def test_nested_point_2(self):
        check(self, 'nested', reaching_definitions, {2: REACHING_DEFINITIONS['nested'][2]})
    def test_nested_point_3(self):
        check(self, 'nested', reaching_definitions, {3: REACHING_DEFINITIONS['nested'][3]})
    def test_nested_point_4(self):
        check(self, 'nested', reaching_definitions, {4: REACHING_DEFINITIONS['nested'][4]})
    def test_nested_point_5(self):
        check(self, 'nested', reaching_definitions, {5: REACHING_DEFINITIONS['nested'][5]})
    def test_nested_point_6(self):
        check(self, 'nested', reaching_definitions, {6: REACHING_DEFINITIONS['nested'][6]})

    # x = n is dead, yet n is read
    def test_dead_point_0(self):
        check(self, 'dead', reaching_definitions, {0: REACHING_DEFINITIONS['dead'][0]})
    def test_dead_point_1(self):
        check(self, 'dead', reaching_definitions, {1: REACHING_DEFINITIONS['dead'][1]})
    def test_dead_point_2(self):
        check(self, 'dead', reaching_definitions, {2: REACHING_DEFINITIONS['dead'][2]})

    # the same command on two edges is two definitions
    def test_twice_point_0(self):
        check(self, 'twice', reaching_definitions, {0: REACHING_DEFINITIONS['twice'][0]})
    def test_twice_point_1(self):
        check(self, 'twice', reaching_definitions, {1: REACHING_DEFINITIONS['twice'][1]})
    def test_twice_point_2(self):
        check(self, 'twice', reaching_definitions, {2: REACHING_DEFINITIONS['twice'][2]})
    def test_twice_point_3(self):
        check(self, 'twice', reaching_definitions, {3: REACHING_DEFINITIONS['twice'][3]})

    # xs[0] = v writes the list, not the variable
    def test_index_point_0(self):
        check(self, 'index', reaching_definitions, {0: REACHING_DEFINITIONS['index'][0]})
    def test_index_point_1(self):
        check(self, 'index', reaching_definitions, {1: REACHING_DEFINITIONS['index'][1]})
    def test_index_point_2(self):
        check(self, 'index', reaching_definitions, {2: REACHING_DEFINITIONS['index'][2]})


# -------------------------------------------------------- live variables

class TestLiveVariables(unittest.TestCase):
    # one dead and one live assignment before a branch
    def test_branch_point_0(self):
        check(self, 'branch', live_variables, {0: LIVE_VARIABLES['branch'][0]})
    def test_branch_point_1(self):
        check(self, 'branch', live_variables, {1: LIVE_VARIABLES['branch'][1]})
    def test_branch_point_2(self):
        check(self, 'branch', live_variables, {2: LIVE_VARIABLES['branch'][2]})
    def test_branch_point_3(self):
        check(self, 'branch', live_variables, {3: LIVE_VARIABLES['branch'][3]})
    def test_branch_point_4(self):
        check(self, 'branch', live_variables, {4: LIVE_VARIABLES['branch'][4]})
    def test_branch_point_5(self):
        check(self, 'branch', live_variables, {5: LIVE_VARIABLES['branch'][5]})

    # examples/loop.py: one loop, one variable
    def test_loop_point_0(self):
        check(self, 'loop', live_variables, {0: LIVE_VARIABLES['loop'][0]})
    def test_loop_point_1(self):
        check(self, 'loop', live_variables, {1: LIVE_VARIABLES['loop'][1]})
    def test_loop_point_2(self):
        check(self, 'loop', live_variables, {2: LIVE_VARIABLES['loop'][2]})
    def test_loop_point_3(self):
        check(self, 'loop', live_variables, {3: LIVE_VARIABLES['loop'][3]})

    # examples/sum.py: two variables around one loop
    def test_sum_point_0(self):
        check(self, 'sum', live_variables, {0: LIVE_VARIABLES['sum'][0]})
    def test_sum_point_1(self):
        check(self, 'sum', live_variables, {1: LIVE_VARIABLES['sum'][1]})
    def test_sum_point_2(self):
        check(self, 'sum', live_variables, {2: LIVE_VARIABLES['sum'][2]})
    def test_sum_point_3(self):
        check(self, 'sum', live_variables, {3: LIVE_VARIABLES['sum'][3]})
    def test_sum_point_4(self):
        check(self, 'sum', live_variables, {4: LIVE_VARIABLES['sum'][4]})
    def test_sum_point_5(self):
        check(self, 'sum', live_variables, {5: LIVE_VARIABLES['sum'][5]})

    # examples/total.py: a list, an index read, an if without else
    def test_total_point_0(self):
        check(self, 'total', live_variables, {0: LIVE_VARIABLES['total'][0]})
    def test_total_point_1(self):
        check(self, 'total', live_variables, {1: LIVE_VARIABLES['total'][1]})
    def test_total_point_2(self):
        check(self, 'total', live_variables, {2: LIVE_VARIABLES['total'][2]})
    def test_total_point_3(self):
        check(self, 'total', live_variables, {3: LIVE_VARIABLES['total'][3]})
    def test_total_point_4(self):
        check(self, 'total', live_variables, {4: LIVE_VARIABLES['total'][4]})
    def test_total_point_5(self):
        check(self, 'total', live_variables, {5: LIVE_VARIABLES['total'][5]})
    def test_total_point_6(self):
        check(self, 'total', live_variables, {6: LIVE_VARIABLES['total'][6]})
    def test_total_point_7(self):
        check(self, 'total', live_variables, {7: LIVE_VARIABLES['total'][7]})

    # x = n is dead, yet n is read
    def test_dead_point_0(self):
        check(self, 'dead', live_variables, {0: LIVE_VARIABLES['dead'][0]})
    def test_dead_point_1(self):
        check(self, 'dead', live_variables, {1: LIVE_VARIABLES['dead'][1]})
    def test_dead_point_2(self):
        check(self, 'dead', live_variables, {2: LIVE_VARIABLES['dead'][2]})

    # a condition reads its variables
    def test_cond_point_0(self):
        check(self, 'cond', live_variables, {0: LIVE_VARIABLES['cond'][0]})
    def test_cond_point_1(self):
        check(self, 'cond', live_variables, {1: LIVE_VARIABLES['cond'][1]})
    def test_cond_point_2(self):
        check(self, 'cond', live_variables, {2: LIVE_VARIABLES['cond'][2]})
    def test_cond_point_3(self):
        check(self, 'cond', live_variables, {3: LIVE_VARIABLES['cond'][3]})


# ------------------------------------------------- available expressions

class TestAvailableExpressions(unittest.TestCase):
    # a + b is lost on one branch, c * 2 is kept
    def test_shared_point_0(self):
        check(self, 'shared', available_expressions, {0: AVAILABLE_EXPRESSIONS['shared'][0]})
    def test_shared_point_1(self):
        check(self, 'shared', available_expressions, {1: AVAILABLE_EXPRESSIONS['shared'][1]})
    def test_shared_point_2(self):
        check(self, 'shared', available_expressions, {2: AVAILABLE_EXPRESSIONS['shared'][2]})
    def test_shared_point_3(self):
        check(self, 'shared', available_expressions, {3: AVAILABLE_EXPRESSIONS['shared'][3]})
    def test_shared_point_4(self):
        check(self, 'shared', available_expressions, {4: AVAILABLE_EXPRESSIONS['shared'][4]})
    def test_shared_point_5(self):
        check(self, 'shared', available_expressions, {5: AVAILABLE_EXPRESSIONS['shared'][5]})

    # a diamond: two branches that meet again
    def test_diamond_point_0(self):
        check(self, 'diamond', available_expressions, {0: AVAILABLE_EXPRESSIONS['diamond'][0]})
    def test_diamond_point_1(self):
        check(self, 'diamond', available_expressions, {1: AVAILABLE_EXPRESSIONS['diamond'][1]})
    def test_diamond_point_2(self):
        check(self, 'diamond', available_expressions, {2: AVAILABLE_EXPRESSIONS['diamond'][2]})
    def test_diamond_point_3(self):
        check(self, 'diamond', available_expressions, {3: AVAILABLE_EXPRESSIONS['diamond'][3]})
    def test_diamond_point_4(self):
        check(self, 'diamond', available_expressions, {4: AVAILABLE_EXPRESSIONS['diamond'][4]})

    # after x = x + 1, x + 1 is stale
    def test_selfkill_point_0(self):
        check(self, 'selfkill', available_expressions, {0: AVAILABLE_EXPRESSIONS['selfkill'][0]})
    def test_selfkill_point_1(self):
        check(self, 'selfkill', available_expressions, {1: AVAILABLE_EXPRESSIONS['selfkill'][1]})

    # a * b survives a loop that does not touch a or b
    def test_invariant_point_0(self):
        check(self, 'invariant', available_expressions, {0: AVAILABLE_EXPRESSIONS['invariant'][0]})
    def test_invariant_point_1(self):
        check(self, 'invariant', available_expressions, {1: AVAILABLE_EXPRESSIONS['invariant'][1]})
    def test_invariant_point_2(self):
        check(self, 'invariant', available_expressions, {2: AVAILABLE_EXPRESSIONS['invariant'][2]})
    def test_invariant_point_3(self):
        check(self, 'invariant', available_expressions, {3: AVAILABLE_EXPRESSIONS['invariant'][3]})
    def test_invariant_point_4(self):
        check(self, 'invariant', available_expressions, {4: AVAILABLE_EXPRESSIONS['invariant'][4]})

    # examples/total.py: a list, an index read, an if without else
    def test_total_point_0(self):
        check(self, 'total', available_expressions, {0: AVAILABLE_EXPRESSIONS['total'][0]})
    def test_total_point_1(self):
        check(self, 'total', available_expressions, {1: AVAILABLE_EXPRESSIONS['total'][1]})
    def test_total_point_2(self):
        check(self, 'total', available_expressions, {2: AVAILABLE_EXPRESSIONS['total'][2]})
    def test_total_point_3(self):
        check(self, 'total', available_expressions, {3: AVAILABLE_EXPRESSIONS['total'][3]})
    def test_total_point_4(self):
        check(self, 'total', available_expressions, {4: AVAILABLE_EXPRESSIONS['total'][4]})
    def test_total_point_5(self):
        check(self, 'total', available_expressions, {5: AVAILABLE_EXPRESSIONS['total'][5]})
    def test_total_point_6(self):
        check(self, 'total', available_expressions, {6: AVAILABLE_EXPRESSIONS['total'][6]})
    def test_total_point_7(self):
        check(self, 'total', available_expressions, {7: AVAILABLE_EXPRESSIONS['total'][7]})


if __name__ == "__main__":
    unittest.main()
