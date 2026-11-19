import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import formulas, projects, templates

app = FastAPI(title="Evaluación de Proyectos Inmobiliarios")

app.include_router(templates.router)
app.include_router(projects.router)
app.include_router(formulas.router)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    if os.environ.get("SEED_ON_STARTUP", "true").lower() == "true":
        from .seed import seed_if_empty
        seed_if_empty()


app.mount("/css", StaticFiles(directory=PUBLIC_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=PUBLIC_DIR / "js"), name="js")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/{full_path:path}")
def spa(full_path: str):
    return FileResponse(PUBLIC_DIR / "index.html")
