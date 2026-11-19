"""Dependency-graph calculation engine.

Given a set of project/template variables (leaf inputs) and line items
(each with either an explicit formula or an "aggregator" flag meaning its
value is the sum of its children), this:

1. Parses every formula and extracts its dependencies by NAME (not position).
2. Builds a DAG and computes a topological order (Kahn's algorithm).
3. Detects cycles up front and reports which keys are involved.
4. Evaluates every node in dependency order, capturing per-node errors
   without aborting the whole calculation — anything that transitively
   depends on a failed node fails too, with a clear message why.

This module has no knowledge of the database — it works on plain
dataclasses so it can be unit tested and reused for template previews.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .evaluator import FormulaEvalError
from .lexer import FormulaSyntaxError
from .parser import parse_formula
from .evaluator import evaluate as eval_ast, extract_dependencies

IGV_COMPRAS_KEY = "IGV_COMPRAS"
IGV_COMPRAS_RATE_VAR = "IGV_COMPRAS_TASA"
DEFAULT_IGV_COMPRAS_RATE = 0.18

RESERVED_KEYS = {IGV_COMPRAS_KEY}


@dataclass
class LineItemSpec:
    key: str
    formula: str | None
    is_aggregator: bool = False
    parent_key: str | None = None
    applies_igv_compra: bool = False


@dataclass
class NodeResult:
    key: str
    value: float | None
    error: str | None
    depends_on: list[str] = field(default_factory=list)
    is_variable: bool = False
    is_virtual: bool = False


class CycleError(Exception):
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__("Ciclo de dependencias: " + " → ".join(cycle))


def _find_one_cycle(nodes: set[str], deps: dict[str, set[str]]) -> list[str]:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in nodes}
    path: list[str] = []

    def dfs(n: str):
        color[n] = GRAY
        path.append(n)
        for d in deps.get(n, ()):
            if d not in nodes:
                continue
            if color[d] == WHITE:
                found = dfs(d)
                if found:
                    return found
            elif color[d] == GRAY:
                start = path.index(d)
                return path[start:] + [d]
        path.pop()
        color[n] = BLACK
        return None

    for n in nodes:
        if color[n] == WHITE:
            found = dfs(n)
            if found:
                return found
    return list(nodes)


def calculate(variables: dict[str, float], items: list[LineItemSpec]) -> dict[str, NodeResult]:
    item_by_key = {it.key: it for it in items}
    children_of: dict[str, list[str]] = {}
    for it in items:
        if it.parent_key:
            children_of.setdefault(it.parent_key, []).append(it.key)

    has_igv_virtual = any(it.applies_igv_compra for it in items)

    # --- parse formulas & extract raw (declared) dependencies ---
    parsed: dict[str, object] = {}
    parse_error: dict[str, str] = {}
    declared_deps: dict[str, set[str]] = {}

    for it in items:
        if it.is_aggregator:
            declared_deps[it.key] = set(children_of.get(it.key, []))
            continue
        if not it.formula:
            parse_error[it.key] = "Sin fórmula definida"
            declared_deps[it.key] = set()
            continue
        try:
            node = parse_formula(it.formula)
            parsed[it.key] = node
            declared_deps[it.key] = extract_dependencies(node)
        except FormulaSyntaxError as exc:
            parse_error[it.key] = str(exc)
            declared_deps[it.key] = set()

    all_known = set(variables.keys()) | set(item_by_key.keys())
    if has_igv_virtual:
        all_known.add(IGV_COMPRAS_KEY)

    # only known references count for graph edges; unknown ones surface as
    # an evaluation-time error ("no está definido") which is clearer to a user.
    graph_deps: dict[str, set[str]] = {
        key: {d for d in deps if d in all_known} for key, deps in declared_deps.items()
    }
    if has_igv_virtual:
        graph_deps[IGV_COMPRAS_KEY] = {it.key for it in items if it.applies_igv_compra}

    all_nodes = set(variables.keys()) | set(item_by_key.keys())
    if has_igv_virtual:
        all_nodes.add(IGV_COMPRAS_KEY)

    # --- Kahn's topological sort ---
    in_degree = {n: 0 for n in all_nodes}
    dependents: dict[str, list[str]] = {n: [] for n in all_nodes}
    for n in all_nodes:
        for d in graph_deps.get(n, ()):
            in_degree[n] += 1
            dependents[d].append(n)

    queue = [n for n in all_nodes if in_degree[n] == 0]
    order: list[str] = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for dep_n in dependents[n]:
            in_degree[dep_n] -= 1
            if in_degree[dep_n] == 0:
                queue.append(dep_n)

    cycle_members = set(all_nodes) - set(order)
    cycle_path = _find_one_cycle(cycle_members, graph_deps) if cycle_members else []

    # --- evaluate in resolved order ---
    context: dict[str, float] = dict(variables)
    results: dict[str, NodeResult] = {}
    for key in variables:
        results[key] = NodeResult(key=key, value=variables[key], error=None, depends_on=[], is_variable=True)

    for key in order:
        if key in variables:
            continue
        it = item_by_key.get(key)
        if key == IGV_COMPRAS_KEY:
            rate = context.get(IGV_COMPRAS_RATE_VAR, DEFAULT_IGV_COMPRAS_RATE)
            base_keys = graph_deps[key]
            try:
                base = sum(_lookup(context, results, k) for k in base_keys)
                value = base * rate
                context[key] = value
                results[key] = NodeResult(key=key, value=value, error=None, depends_on=sorted(base_keys), is_virtual=True)
            except FormulaEvalError as exc:
                results[key] = NodeResult(key=key, value=None, error=str(exc), depends_on=sorted(base_keys), is_virtual=True)
            continue

        deps_display = sorted(declared_deps.get(key, set()))
        if key in parse_error:
            results[key] = NodeResult(key=key, value=None, error=parse_error[key], depends_on=deps_display)
            continue
        if it and it.is_aggregator:
            child_keys = children_of.get(key, [])
            try:
                value = sum(_lookup(context, results, c) for c in child_keys)
                context[key] = value
                results[key] = NodeResult(key=key, value=value, error=None, depends_on=deps_display)
            except FormulaEvalError as exc:
                results[key] = NodeResult(key=key, value=None, error=str(exc), depends_on=deps_display)
            continue
        try:
            value = eval_ast(parsed[key], context)
            context[key] = value
            results[key] = NodeResult(key=key, value=value, error=None, depends_on=deps_display)
        except FormulaEvalError as exc:
            results[key] = NodeResult(key=key, value=None, error=str(exc), depends_on=deps_display)

    for key in cycle_members:
        deps_display = sorted(declared_deps.get(key, set())) if key != IGV_COMPRAS_KEY else sorted(graph_deps.get(key, set()))
        in_cycle = key in cycle_path
        msg = ("Ciclo de dependencias: " + " → ".join(cycle_path)) if in_cycle else (
            "Bloqueado por un ciclo de dependencias entre: " + ", ".join(cycle_path)
        )
        results[key] = NodeResult(key=key, value=None, error=msg, depends_on=deps_display, is_virtual=(key == IGV_COMPRAS_KEY))

    return results


def _lookup(context: dict, results: dict[str, NodeResult], key: str) -> float:
    if key not in context:
        ref = results.get(key)
        if ref and ref.error:
            raise FormulaEvalError(f"depende de '{key}', que tiene un error")
        raise FormulaEvalError(f"'{key}' no está definido o no se pudo calcular")
    return context[key]
