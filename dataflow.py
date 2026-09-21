"""A worklist engine, and three classic dataflow analyses on top of it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cfg import CFG, Cmd, Edge, Assume, NodeId, Worklist
from syntax import *

Data = frozenset

PARAM = -1          # the "edge" that defines the parameters: the call itself


@dataclass(frozen=True)
class Analysis:
    forward: bool
    bottom: Data                                   # initial guess everywhere
    init: Data                                     # the data at the start point
    join: Callable[[Data, Data], Data]
    transfer: Callable[[Edge, Data], Data]         # what one edge does


def solve(g: CFG, a: Analysis) -> dict[NodeId, Data]:
    """Least fixpoint of the dataflow equations: one set per program point.

        forward:   data(q) = join of transfer(e, data(p)) for every edge p -> q
        backward:  data(p) = join of transfer(e, data(q)) for every edge p -> q
    """
    start = g.entry if a.forward else g.exit
    data = {p: a.bottom for p in g}
    data[start] = a.init
    work = Worklist([start])
    while work:
        p = work.pop()
        # TODO: the worklist algorithm (see README)
        raise NotImplementedError("TODO: solve")
    return data


# ------------------------------------------------------- dominators, again

def dominators(g: CFG) -> Analysis:
    """Which points must have run before this one?"""
    def transfer(e: Edge, s: Data) -> Data:
        return s | {e.dst}                          # kill nothing, gen q

    return Analysis(True, frozenset(g.nodes), frozenset({g.entry}),
                    frozenset.intersection, transfer)


# ------------------------------------------------ three classic analyses

def reaching_definitions(g: CFG) -> Analysis:
    """Which assignment may have written the value of a variable here?

    A fact is a pair (x, d): the variable x was last written on edge d, where
    d is the edge's `id`, or PARAM if x came in as a parameter.
    """
    raise NotImplementedError("TODO: reaching definitions")


def live_variables(g: CFG) -> Analysis:
    """Might the current value of a variable still be read later?

    A fact is a variable name. At the exit, the variables of the returned
    expression `g.ret` are live.
    """
    raise NotImplementedError("TODO: live variables")


def available_expressions(g: CFG) -> Analysis:
    """May the result of an expression be reused here?

    A fact is an expression: an `Expr` node such as `BinOp`, `UnOp`, or
    `Index`. Variables, constants, and list literals are not facts (a list
    literal makes a new list every time). The initial guess for every point
    but the entry is *every* such expression in the program, including those
    inside the returned expression `g.ret`. Writing x kills every expression
    that mentions x, including the one being computed: after `x = x + 1`,
    `x + 1` is stale.
    """
    raise NotImplementedError("TODO: available expressions")
