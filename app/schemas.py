from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------- Variables ----------------------------
class VariableIn(BaseModel):
    key: str
    label: str
    default_value: float = 0
    unit: str | None = None
    order: int = 0


class VariableOut(VariableIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProjectVariableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    label: str
    value: float
    unit: str | None
    order: int


class ProjectVariableUpdate(BaseModel):
    value: float


# ---------------------------- Line items ----------------------------
class LineItemIn(BaseModel):
    key: str
    name: str
    category: str | None = None
    formula: str | None = None
    is_aggregator: bool = False
    parent_key: str | None = None
    applies_igv_compra: bool = False
    notes: str | None = None
    order: int = 0


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    key: str
    name: str
    category: str | None
    formula: str | None
    is_aggregator: bool
    parent_key: str | None = None
    applies_igv_compra: bool
    notes: str | None
    order: int


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    old_formula: str | None
    new_formula: str | None
    changed_at: datetime


# ---------------------------- Templates ----------------------------
class TemplateIn(BaseModel):
    name: str
    description: str | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TemplateDetailOut(TemplateOut):
    variables: list[VariableOut] = []
    line_items: list[LineItemOut] = []


# ---------------------------- Projects ----------------------------
class ProjectCreate(BaseModel):
    name: str
    template_id: int


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    template_id: int | None
    template_name_snapshot: str | None
    template_version_snapshot: int | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    variables: list[ProjectVariableOut] = []
    line_items: list[LineItemOut] = []


class ProjectUpdate(BaseModel):
    name: str | None = None


# ---------------------------- Calculation ----------------------------
class CalcResultOut(BaseModel):
    key: str
    value: float | None
    error: str | None
    depends_on: list[str]
    is_variable: bool = False
    is_virtual: bool = False


class CalculationOut(BaseModel):
    results: dict[str, CalcResultOut]
    order: list[str]
    has_errors: bool


# ---------------------------- Formula validation ----------------------------
class FormulaValidateIn(BaseModel):
    formula: str


class FormulaValidateOut(BaseModel):
    valid: bool
    error: str | None
    dependencies: list[str]
