"""Glue between the SQLAlchemy models and the pure formula engine, plus small
helpers shared by the templates/projects routers (parent_id <-> parent_key
resolution, formula-change history logging, running a full calculation)."""
from __future__ import annotations

from .formula import LineItemSpec, calculate


def build_line_item_specs(items) -> list[LineItemSpec]:
    id_to_key = {it.id: it.key for it in items}
    specs = []
    for it in items:
        parent_key = id_to_key.get(it.parent_id) if it.parent_id else None
        specs.append(LineItemSpec(
            key=it.key,
            formula=it.formula,
            is_aggregator=it.is_aggregator,
            parent_key=parent_key,
            applies_igv_compra=it.applies_igv_compra,
        ))
    return specs


def serialize_line_item(item, id_to_key: dict[int, str]) -> dict:
    return {
        "id": item.id,
        "key": item.key,
        "name": item.name,
        "category": item.category,
        "formula": item.formula,
        "is_aggregator": item.is_aggregator,
        "parent_key": id_to_key.get(item.parent_id) if item.parent_id else None,
        "applies_igv_compra": item.applies_igv_compra,
        "notes": item.notes,
        "order": item.order,
    }


def serialize_line_items(items) -> list[dict]:
    id_to_key = {it.id: it.key for it in items}
    return [serialize_line_item(it, id_to_key) for it in items]


def run_calculation(variables: dict[str, float], items) -> dict:
    specs = build_line_item_specs(items)
    results = calculate(variables, specs)
    order = list(results.keys())
    has_errors = any(r.error for r in results.values())
    return {
        "results": {
            k: {
                "key": r.key, "value": r.value, "error": r.error,
                "depends_on": r.depends_on, "is_variable": r.is_variable, "is_virtual": r.is_virtual,
            }
            for k, r in results.items()
        },
        "order": order,
        "has_errors": has_errors,
    }
