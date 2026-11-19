"""Sandboxed evaluation of a parsed formula AST.

Only arithmetic on numbers and a fixed whitelist of pure math functions are
reachable — no attribute access, no indexing, no builtins, no imports.
"""
from __future__ import annotations

import math

from .ast_nodes import BinOp, Call, Name, Node, Num, UnaryOp
from .parser import parse_formula


class FormulaEvalError(Exception):
    pass


def _fn_if(cond, a, b):
    return a if cond else b


FUNCTIONS = {
    "max": lambda *args: max(args),
    "min": lambda *args: min(args),
    "round": lambda x, n=0: round(x, int(n)),
    "sqrt": math.sqrt,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "if": _fn_if,
}

BIN_OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
    "^": lambda a, b: a**b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def extract_dependencies(node: Node) -> set[str]:
    """Every bare identifier referenced in the formula (variable or partida key)."""
    deps: set[str] = set()

    def walk(n: Node):
        if isinstance(n, Name):
            deps.add(n.ident)
        elif isinstance(n, BinOp):
            walk(n.left)
            walk(n.right)
        elif isinstance(n, UnaryOp):
            walk(n.operand)
        elif isinstance(n, Call):
            for a in n.args:
                walk(a)
        elif isinstance(n, Num):
            pass

    walk(node)
    return deps


def evaluate(node: Node, context: dict[str, float]) -> float:
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Name):
        if node.ident not in context:
            raise FormulaEvalError(f"'{node.ident}' no está definido o no se pudo calcular")
        return context[node.ident]
    if isinstance(node, UnaryOp):
        val = evaluate(node.operand, context)
        return val if node.op == "+" else -val
    if isinstance(node, BinOp):
        left = evaluate(node.left, context)
        right = evaluate(node.right, context)
        try:
            return BIN_OPS[node.op](left, right)
        except ZeroDivisionError as exc:
            raise FormulaEvalError("división por cero") from exc
    if isinstance(node, Call):
        if node.name not in FUNCTIONS:
            raise FormulaEvalError(f"función no permitida: '{node.name}'")
        args = [evaluate(a, context) for a in node.args]
        try:
            return FUNCTIONS[node.name](*args)
        except (TypeError, ValueError) as exc:
            raise FormulaEvalError(f"error en la función '{node.name}': {exc}") from exc
    raise FormulaEvalError("nodo de fórmula desconocido")


def parse_and_eval(text: str, context: dict[str, float]) -> float:
    node = parse_formula(text)
    return evaluate(node, context)
