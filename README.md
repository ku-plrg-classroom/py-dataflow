# MiniPy Dataflow Analyzer

A small, complete dataflow-analysis framework for **MiniPy**, a subset of
Python: one `def`, integers, booleans, strings, lists, `if`, `while`, and a
final `return`. Programs are parsed, turned into a control flow graph, and
analyzed by a worklist engine that is parameterized by the analysis.

The engine and three classic analyses are left for you to write. The tests
tell you when you are done.

## Layout

| File | What it is | Edit? |
|---|---|---|
| `dataflow.py` | the engine and the analyses, with four holes | **yes, only this one** |
| `test_dataflow.py` | 100 tests, one per program point | no |
| `syntax.py` | the MiniPy parser and AST | no |
| `cfg.py` | control flow graphs and the `Worklist` | no |
| `examples/` | small MiniPy programs to try | no |

A control flow graph has *program points* joined by edges, and every edge
carries one command: an assignment, `pass`, or `assume(e)` for a branch
taken. A dataflow analysis attaches a set of facts to every point.

## The holes

Each of the four functions below raises `NotImplementedError` until you
replace it.

1. **`solve(g, a)`**: the worklist algorithm. Start with the initial data at
   the start point, pop a point, push its data along every edge in the
   analysis direction, join it into the target, and push the target when
   its data changed, or when it is reached for the first time.
2. **`reaching_definitions(g)`**: facts are pairs `(x, d)`: variable `x`
   was last written on edge `d`, or `d == PARAM` if `x` is a parameter.
   Forward, union.
3. **`live_variables(g)`**: facts are variable names that may still be read.
   Backward, union.
4. **`available_expressions(g)`**: facts are `Expr` nodes whose value is
   already computed on every path and still valid. Forward, intersection.

Every analysis is an `Analysis` record: a direction, a bottom, the initial
data at the start point, a join, and a transfer function. `dominators` is
finished and shows the shape; the other three follow it. Define any helper
you like.

## Running the tests

```
python3 -m unittest test_dataflow
```

Each test names its program and point, and a failure prints the graph's
edges, so you can trace the expected set by hand. Run one class at a time
while you work:

```
python3 -m unittest test_dataflow.TestReachingDefinitions
```

To draw a graph with Graphviz:

```
python3 cfg.py examples/loop.py | dot -Tpdf -o loop.pdf
```

## Requirements

Python 3.12 or later. No packages beyond the standard library.
