"""Seeds one realistic demo template on first run, so the app is usable
out of the box. Only runs if there are no templates yet."""
from sqlalchemy import select

from . import models
from .database import SessionLocal


VARIABLES = [
    dict(key="UIT", label="UIT vigente", default_value=4950, unit="PEN", order=1),
    dict(key="TipoCambio", label="Tipo de cambio (S/ por US$)", default_value=3.75, unit="PEN/USD", order=2),
    dict(key="AreaVendible", label="Área vendible", default_value=2000, unit="m2", order=3),
    dict(key="AreaConstruidaTotal", label="Área construida total", default_value=2500, unit="m2", order=4),
    dict(key="PrecioVentaM2", label="Precio de venta por m2", default_value=8000, unit="PEN/m2", order=5),
    dict(key="IGV_COMPRAS_TASA", label="Tasa de IGV de compras", default_value=0.18, unit="%", order=6),
]

# (key, name, category, formula, is_aggregator, parent_key, applies_igv, notes)
ITEMS = [
    ("Terreno", "Terreno", "Terreno", "1000000", False, None, False, "Monto de compra del terreno (valor de ejemplo, no gravado con IGV)"),
    ("Alcabala", "Alcabala", "Terreno", "max(0, Terreno - 10*UIT) * 0.03", False, None, False, "Tramo exonerado de 10 UIT antes de aplicar 3%"),

    ("ObrasPreliminares", "Obras preliminares", "Costo directo", "AreaConstruidaTotal * 45", False, "CostoDirectoConstruccion", True, None),
    ("Estructuras", "Estructuras", "Costo directo", "AreaConstruidaTotal * 560", False, "CostoDirectoConstruccion", True, None),
    ("Arquitectura", "Arquitectura", "Costo directo", "AreaConstruidaTotal * 745", False, "CostoDirectoConstruccion", True, None),
    ("InstalacionesElectricas", "Instalaciones eléctricas", "Costo directo", "AreaConstruidaTotal * 148", False, "CostoDirectoConstruccion", True, None),
    ("InstalacionesSanitarias", "Instalaciones sanitarias", "Costo directo", "AreaConstruidaTotal * 85", False, "CostoDirectoConstruccion", True, None),
    ("CostoDirectoConstruccion", "Costo directo de construcción", "Costo directo", None, True, None, False, "Suma de las sub-partidas de construcción"),

    ("GastosGenerales", "Gastos generales", "Costo indirecto", "CostoDirectoConstruccion * 0.10", False, None, True, None),
    ("UtilidadConstructor", "Utilidad del constructor", "Costo indirecto", "CostoDirectoConstruccion * 0.06", False, None, True, None),
    ("CostoConstruccionTotal", "Costo de construcción total", "Costo indirecto",
     "CostoDirectoConstruccion + GastosGenerales + UtilidadConstructor", False, None, False, None),

    ("IngresosTotales", "Ingresos totales por venta", "Ingresos", "AreaVendible * PrecioVentaM2", False, None, False, "Precio de venta incluye IGV de ventas (9%)"),
    ("IngresosNetos", "Ingresos netos (sin IGV ventas)", "Ingresos", "IngresosTotales / 1.09", False, None, False, "Cálculo hacia atrás del IGV de ventas"),

    ("GestionInmobiliaria", "Gestión inmobiliaria", "Fees", "IngresosTotales * 0.02", False, None, True, "% sobre ingresos totales"),
    ("Marketing", "Marketing y ventas", "Fees", "IngresosTotales * 0.03", False, None, True, "% sobre ingresos totales"),
    ("Contingencia", "Contingencia", "Fees", "CostoConstruccionTotal * 0.03", False, None, True, "% sobre costo de construcción"),

    ("InversionTotal", "Inversión total", "Resumen",
     "Terreno + Alcabala + CostoConstruccionTotal + IGV_COMPRAS + GestionInmobiliaria + Marketing + Contingencia",
     False, None, False, None),
    ("UtilidadProyecto", "Utilidad del proyecto", "Resumen", "IngresosNetos - InversionTotal", False, None, False, None),
    ("MargenProyecto", "Margen sobre ingresos (%)", "Resumen", "UtilidadProyecto / IngresosNetos * 100", False, None, False, None),
]


def seed_if_empty():
    db = SessionLocal()
    try:
        exists = db.execute(select(models.Template.id)).first()
        if exists:
            return
        tpl = models.Template(
            name="Modelo Inmobiliario Estándar",
            description="Plantilla de evaluación de proyecto inmobiliario: terreno, alcabala, costo de "
                        "construcción, IGV, fees e ingresos, con fórmulas paramétricas referenciadas por nombre.",
        )
        db.add(tpl)
        db.flush()

        for i, v in enumerate(VARIABLES, start=1):
            db.add(models.TemplateVariable(template_id=tpl.id, **v))

        key_to_id = {}
        for order, (key, name, category, formula, is_agg, parent_key, applies_igv, notes) in enumerate(ITEMS, start=1):
            item = models.TemplateLineItem(
                template_id=tpl.id, key=key, name=name, category=category, formula=formula,
                is_aggregator=is_agg, applies_igv_compra=applies_igv, notes=notes, order=order,
            )
            db.add(item)
            db.flush()
            key_to_id[key] = item.id

        for key, *_rest, parent_key, _applies, _notes in ITEMS:
            if parent_key:
                db.get(models.TemplateLineItem, key_to_id[key]).parent_id = key_to_id[parent_key]

        db.commit()
        print(f"[seed] Plantilla demo creada: '{tpl.name}' (id={tpl.id})")
    finally:
        db.close()
