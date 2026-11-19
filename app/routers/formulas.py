from fastapi import APIRouter

from .. import schemas
from ..formula import FormulaSyntaxError, extract_dependencies, parse_formula

router = APIRouter(prefix="/api/formulas", tags=["formulas"])


@router.post("/validate", response_model=schemas.FormulaValidateOut)
def validate_formula(payload: schemas.FormulaValidateIn):
    if not payload.formula or not payload.formula.strip():
        return {"valid": True, "error": None, "dependencies": []}
    try:
        node = parse_formula(payload.formula)
        deps = sorted(extract_dependencies(node))
        return {"valid": True, "error": None, "dependencies": deps}
    except FormulaSyntaxError as exc:
        return {"valid": False, "error": str(exc), "dependencies": []}
