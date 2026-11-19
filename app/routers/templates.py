from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..formula import IGV_COMPRAS_KEY
from ..services import run_calculation, serialize_line_items

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _get_template(db: Session, template_id: int) -> models.Template:
    tpl = db.get(models.Template, template_id)
    if not tpl:
        raise HTTPException(404, "Plantilla no encontrada")
    return tpl


def _get_item(db: Session, template_id: int, item_id: int) -> models.TemplateLineItem:
    item = db.get(models.TemplateLineItem, item_id)
    if not item or item.template_id != template_id:
        raise HTTPException(404, "Partida no encontrada")
    return item


def _resolve_parent(db: Session, template_id: int, parent_key: str | None, self_id: int | None = None):
    if not parent_key:
        return None
    parent = db.execute(
        select(models.TemplateLineItem).where(
            models.TemplateLineItem.template_id == template_id,
            models.TemplateLineItem.key == parent_key,
        )
    ).scalar_one_or_none()
    if not parent:
        raise HTTPException(400, f"No existe una partida con key '{parent_key}' para usar como padre")
    if self_id and parent.id == self_id:
        raise HTTPException(400, "Una partida no puede ser su propio padre")
    return parent.id


def _check_key(db: Session, template_id: int, key: str, kind: str, self_id: int | None = None):
    if key == IGV_COMPRAS_KEY:
        raise HTTPException(400, f"'{IGV_COMPRAS_KEY}' es una key reservada por el sistema (IGV de compras)")
    model = models.TemplateVariable if kind == "variable" else models.TemplateLineItem
    q = select(model).where(model.template_id == template_id, model.key == key)
    existing = db.execute(q).scalar_one_or_none()
    if existing and existing.id != self_id:
        raise HTTPException(409, f"Ya existe un(a) {kind} con key '{key}' en esta plantilla")
    other_kind_model = models.TemplateLineItem if kind == "variable" else models.TemplateVariable
    q2 = select(other_kind_model).where(other_kind_model.template_id == template_id, other_kind_model.key == key)
    if db.execute(q2).scalar_one_or_none():
        raise HTTPException(409, f"La key '{key}' ya está en uso por otro elemento de la plantilla")


def _detail(db: Session, tpl: models.Template) -> dict:
    items = serialize_line_items(tpl.line_items)
    return {
        "id": tpl.id, "name": tpl.name, "description": tpl.description, "version": tpl.version,
        "created_at": tpl.created_at, "updated_at": tpl.updated_at,
        "variables": [schemas.VariableOut.model_validate(v) for v in tpl.variables],
        "line_items": items,
    }


@router.get("", response_model=list[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    return db.execute(select(models.Template).order_by(models.Template.updated_at.desc())).scalars().all()


@router.post("", response_model=schemas.TemplateOut, status_code=201)
def create_template(payload: schemas.TemplateIn, db: Session = Depends(get_db)):
    tpl = models.Template(name=payload.name, description=payload.description)
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.get("/{template_id}", response_model=schemas.TemplateDetailOut)
def get_template(template_id: int, db: Session = Depends(get_db)):
    return _detail(db, _get_template(db, template_id))


@router.put("/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: int, payload: schemas.TemplateIn, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    tpl.name = payload.name
    tpl.description = payload.description
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    db.delete(tpl)
    db.commit()


@router.post("/{template_id}/duplicate", response_model=schemas.TemplateOut, status_code=201)
def duplicate_template(template_id: int, db: Session = Depends(get_db)):
    src = _get_template(db, template_id)
    clone = models.Template(name=f"{src.name} (copia)", description=src.description)
    db.add(clone)
    db.flush()
    key_to_new_id = {}
    for v in src.variables:
        db.add(models.TemplateVariable(
            template_id=clone.id, key=v.key, label=v.label, default_value=v.default_value,
            unit=v.unit, order=v.order,
        ))
    id_to_key = {it.id: it.key for it in src.line_items}
    for it in src.line_items:
        new_item = models.TemplateLineItem(
            template_id=clone.id, key=it.key, name=it.name, category=it.category, formula=it.formula,
            is_aggregator=it.is_aggregator, applies_igv_compra=it.applies_igv_compra, notes=it.notes, order=it.order,
        )
        db.add(new_item)
        db.flush()
        key_to_new_id[it.key] = new_item.id
    for it in src.line_items:
        if it.parent_id:
            parent_key = id_to_key[it.parent_id]
            db.execute(
                models.TemplateLineItem.__table__.update()
                .where(models.TemplateLineItem.key == it.key, models.TemplateLineItem.template_id == clone.id)
                .values(parent_id=key_to_new_id[parent_key])
            )
    db.commit()
    db.refresh(clone)
    return clone


# ---------------------------- Variables ----------------------------
@router.post("/{template_id}/variables", response_model=schemas.VariableOut, status_code=201)
def add_variable(template_id: int, payload: schemas.VariableIn, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    _check_key(db, template_id, payload.key, "variable")
    var = models.TemplateVariable(template_id=tpl.id, **payload.model_dump())
    db.add(var)
    tpl.version += 1
    db.commit()
    db.refresh(var)
    return var


@router.put("/{template_id}/variables/{var_id}", response_model=schemas.VariableOut)
def update_variable(template_id: int, var_id: int, payload: schemas.VariableIn, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    var = db.get(models.TemplateVariable, var_id)
    if not var or var.template_id != template_id:
        raise HTTPException(404, "Variable no encontrada")
    _check_key(db, template_id, payload.key, "variable", self_id=var_id)
    for k, v in payload.model_dump().items():
        setattr(var, k, v)
    tpl.version += 1
    db.commit()
    db.refresh(var)
    return var


@router.delete("/{template_id}/variables/{var_id}", status_code=204)
def delete_variable(template_id: int, var_id: int, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    var = db.get(models.TemplateVariable, var_id)
    if not var or var.template_id != template_id:
        raise HTTPException(404, "Variable no encontrada")
    db.delete(var)
    tpl.version += 1
    db.commit()


# ---------------------------- Line items ----------------------------
@router.post("/{template_id}/items", response_model=schemas.LineItemOut, status_code=201)
def add_item(template_id: int, payload: schemas.LineItemIn, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    _check_key(db, template_id, payload.key, "partida")
    data = payload.model_dump()
    parent_key = data.pop("parent_key")
    parent_id = _resolve_parent(db, template_id, parent_key)
    item = models.TemplateLineItem(template_id=tpl.id, parent_id=parent_id, **data)
    db.add(item)
    tpl.version += 1
    db.commit()
    db.refresh(item)
    return {**payload.model_dump(), "id": item.id}


@router.put("/{template_id}/items/{item_id}", response_model=schemas.LineItemOut)
def update_item(template_id: int, item_id: int, payload: schemas.LineItemIn, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    item = _get_item(db, template_id, item_id)
    _check_key(db, template_id, payload.key, "partida", self_id=item_id)
    old_formula = item.formula
    data = payload.model_dump()
    parent_key = data.pop("parent_key")
    item.parent_id = _resolve_parent(db, template_id, parent_key, self_id=item_id)
    for k, v in data.items():
        setattr(item, k, v)
    if old_formula != item.formula:
        db.add(models.TemplateLineItemHistory(line_item_id=item.id, old_formula=old_formula, new_formula=item.formula))
    tpl.version += 1
    db.commit()
    db.refresh(item)
    return {**payload.model_dump(), "id": item.id}


@router.delete("/{template_id}/items/{item_id}", status_code=204)
def delete_item(template_id: int, item_id: int, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    item = _get_item(db, template_id, item_id)
    db.delete(item)
    tpl.version += 1
    db.commit()


@router.get("/{template_id}/items/{item_id}/history", response_model=list[schemas.HistoryOut])
def item_history(template_id: int, item_id: int, db: Session = Depends(get_db)):
    item = _get_item(db, template_id, item_id)
    return item.history


@router.get("/{template_id}/calculate", response_model=schemas.CalculationOut)
def calculate_template(template_id: int, db: Session = Depends(get_db)):
    tpl = _get_template(db, template_id)
    variables = {v.key: v.default_value for v in tpl.variables}
    return run_calculation(variables, tpl.line_items)
