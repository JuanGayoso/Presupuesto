from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now():
    return datetime.now(timezone.utc)


# ============================= PLANTILLAS =============================

class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    variables: Mapped[list["TemplateVariable"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateVariable.order"
    )
    line_items: Mapped[list["TemplateLineItem"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateLineItem.order"
    )


class TemplateVariable(Base):
    __tablename__ = "template_variables"
    __table_args__ = (UniqueConstraint("template_id", "key", name="uq_template_variable_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    default_value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[Template] = relationship(back_populates="variables")


class TemplateLineItem(Base):
    __tablename__ = "template_line_items"
    __table_args__ = (UniqueConstraint("template_id", "key", name="uq_template_item_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    formula: Mapped[str | None] = mapped_column(Text)
    is_aggregator: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("template_line_items.id", ondelete="SET NULL"))
    applies_igv_compra: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped[Template] = relationship(back_populates="line_items")
    history: Mapped[list["TemplateLineItemHistory"]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan", order_by="TemplateLineItemHistory.changed_at.desc()"
    )


class TemplateLineItemHistory(Base):
    __tablename__ = "template_line_item_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_item_id: Mapped[int] = mapped_column(ForeignKey("template_line_items.id", ondelete="CASCADE"))
    old_formula: Mapped[str | None] = mapped_column(Text)
    new_formula: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    line_item: Mapped[TemplateLineItem] = relationship(back_populates="history")


# ============================== PROYECTOS ==============================

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id", ondelete="SET NULL"))
    template_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    template_version_snapshot: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    variables: Mapped[list["ProjectVariable"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectVariable.order"
    )
    line_items: Mapped[list["ProjectLineItem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectLineItem.order"
    )


class ProjectVariable(Base):
    __tablename__ = "project_variables"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_variable_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str | None] = mapped_column(String(40))
    order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="variables")


class ProjectLineItem(Base):
    __tablename__ = "project_line_items"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_item_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    formula: Mapped[str | None] = mapped_column(Text)
    is_aggregator: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("project_line_items.id", ondelete="SET NULL"))
    applies_igv_compra: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship(back_populates="line_items")
    history: Mapped[list["ProjectLineItemHistory"]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan", order_by="ProjectLineItemHistory.changed_at.desc()"
    )


class ProjectLineItemHistory(Base):
    __tablename__ = "project_line_item_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_item_id: Mapped[int] = mapped_column(ForeignKey("project_line_items.id", ondelete="CASCADE"))
    old_formula: Mapped[str | None] = mapped_column(Text)
    new_formula: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    line_item: Mapped[ProjectLineItem] = relationship(back_populates="history")
