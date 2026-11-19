from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..formula import IGV_COMPRAS_KEY
from ..services import run_calculation, serialize_line_items

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_project(db: Session, project_id: int) -> models.Project:
    proj = db.get(models.Project, project_id)
    if not proj:
        raise HTTPException(404, "Proyecto no encontrado")
    return proj


def _get_item(db: Session, project_id: int, item_id: int) -> models.ProjectLineItem:
    item = db.get(models.ProjectLineItem, item_id)
    if not item or item.project_id != project_id:
        raise HTTPException(404, "Partida no encontrada")
    return item


def _resolve_parent(db: Session, project_id: int, parent_key: str | None, self_id: int | None = None):
    if not parent_key:
        return None
    parent = db.execute(
        select(models.ProjectLineItem).where(
            models.ProjectLineItem.project_id == project_id,
            models.ProjectLineItem.key == parent_key,
        )
    ).scalar_one_or_none()
    if not parent:
        raise HTTPException(400, f"No existe una partida con key '{parent_key}' para usar como padre")
    if self_id and parent.id == self_id:
        raise HTTPException(400, "Una partida no puede ser su propio padre")
    return parent.id


def _check_key(db: Session, project_id: int, key: str, kind: str, self_id: int | None = None):
    if key == IGV_COMPRAS_KEY:
        raise HTTPException(400, f"'{IGV_COMPRAS_KEY}' es una key reservada por el sistema (IGV de compras)")
    model = models.ProjectVariable if kind == "variable" else models.ProjectLineItem
    q = select(model).where(model.project_id == project_id, model.key == key)
    existing = db.execute(q).scalar_one_or_none()
    if existing and existing.id != self_id:
        raise HTTPException(409, f"Ya existe un(a) {kind} con key '{key}' en este proyecto")
    other_kind_model = models.ProjectLineItem if kind == "variable" else models.ProjectVariable
    q2 = select(other_kind_model).where(other_kind_model.project_id == project_id, other_kind_model.key == key)
    if db.execute(q2).scalar_one_or_none():
        raise HTTPException(409, f"La key '{key}' ya está en uso por otro elemento del proyecto")


def _detail(proj: models.Project) -> dict:
    return {
        "id": proj.id, "name": proj.name, "template_id": proj.template_id,
        "template_name_snapshot": proj.template_name_snapshot,
        "template_version_snapshot": proj.template_version_snapshot,
        "created_at": proj.created_at, "updated_at": proj.updated_at,
        "variables": [schemas.ProjectVariableOut.model_validate(v) for v in proj.variables],
        "line_items": serialize_line_items(proj.line_items),
    }


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.execute(select(models.Project).order_by(models.Project.updated_at.desc())).scalars().all()


@router.post("", response_model=schemas.ProjectDetailOut, status_code=201)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    tpl = db.get(models.Template, payload.template_id)
    if not tpl:
        raise HTTPException(404, "Plantilla no encontrada")
    proj = models.Project(
        name=payload.name, template_id=tpl.id,
        template_name_snapshot=tpl.name, template_version_snapshot=tpl.version,
    )
    db.add(proj)
    db.flush()
    for v in tpl.variables:
        db.add(models.ProjectVariable(
            project_id=proj.id, key=v.key, label=v.label, value=v.default_value, unit=v.unit, order=v.order,
        ))
    id_to_key = {it.id: it.key for it in tpl.line_items}
    key_to_new_id = {}
    for it in tpl.line_items:
        new_item = models.ProjectLineItem(
            project_id=proj.id, key=it.key, name=it.name, category=it.category, formula=it.formula,
            is_aggregator=it.is_aggregator, applies_igv_compra=it.applies_igv_compra, notes=it.notes, order=it.order,
        )
        db.add(new_item)
        db.flush()
        key_to_new_id[it.key] = new_item.id
    for it in tpl.line_items:
        if it.parent_id:
            parent_key = id_to_key[it.parent_id]
            new_item = db.execute(
                select(models.ProjectLineItem).where(
                    models.ProjectLineItem.project_id == proj.id, models.ProjectLineItem.key == it.key
                )
            ).scalar_one()
            new_item.parent_id = key_to_new_id[parent_key]
    db.commit()
    db.refresh(proj)
    return _detail(proj)


@router.get("/{project_id}", response_model=schemas.ProjectDetailOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _detail(_get_project(db, project_id))


@router.put("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: int, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    proj = _get_project(db, project_id)
    if payload.name:
        proj.name = payload.name
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db.delete(_get_project(db, project_id))
    db.commit()


# ---------------------------- Variables ----------------------------
@router.put("/{project_id}/variables/{var_id}", response_model=schemas.ProjectVariableOut)
def update_project_variable(project_id: int, var_id: int, payload: schemas.ProjectVariableUpdate, db: Session = Depends(get_db)):
    var = db.get(models.ProjectVariable, var_id)
    if not var or var.project_id != project_id:
        raise HTTPException(404, "Variable no encontrada")
    var.value = payload.value
    db.commit()
    db.refresh(var)
    return var


# ---------------------------- Line items ----------------------------
@router.post("/{project_id}/items", response_model=schemas.LineItemOut, status_code=201)
def add_item(project_id: int, payload: schemas.LineItemIn, db: Session = Depends(get_db)):
    proj = _get_project(db, project_id)
    _check_key(db, project_id, payload.key, "partida")
    data = payload.model_dump()
    parent_key = data.pop("parent_key")
    parent_id = _resolve_parent(db, project_id, parent_key)
    item = models.ProjectLineItem(project_id=proj.id, parent_id=parent_id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {**payload.model_dump(), "id": item.id}


@router.put("/{project_id}/items/{item_id}", response_model=schemas.LineItemOut)
def update_item(project_id: int, item_id: int, payload: schemas.LineItemIn, db: Session = Depends(get_db)):
    item = _get_item(db, project_id, item_id)
    _check_key(db, project_id, payload.key, "partida", self_id=item_id)
    old_formula = item.formula
    data = payload.model_dump()
    parent_key = data.pop("parent_key")
    item.parent_id = _resolve_parent(db, project_id, parent_key, self_id=item_id)
    for k, v in data.items():
        setattr(item, k, v)
    if old_formula != item.formula:
        db.add(models.ProjectLineItemHistory(line_item_id=item.id, old_formula=old_formula, new_formula=item.formula))
    db.commit()
    db.refresh(item)
    return {**payload.model_dump(), "id": item.id}


@router.delete("/{project_id}/items/{item_id}", status_code=204)
def delete_item(project_id: int, item_id: int, db: Session = Depends(get_db)):
    db.delete(_get_item(db, project_id, item_id))
    db.commit()


@router.get("/{project_id}/items/{item_id}/history", response_model=list[schemas.HistoryOut])
def item_history(project_id: int, item_id: int, db: Session = Depends(get_db)):
    return _get_item(db, project_id, item_id).history


@router.get("/{project_id}/calculate", response_model=schemas.CalculationOut)
def calculate_project(project_id: int, db: Session = Depends(get_db)):
    proj = _get_project(db, project_id)
    variables = {v.key: v.value for v in proj.variables}
    return run_calculation(variables, proj.line_items)
