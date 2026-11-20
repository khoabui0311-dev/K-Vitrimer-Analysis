"""Local-first FastAPI service for VitriFit 2.0.

Bind to 127.0.0.1 (see run_v2.py). Do not expose this unauthenticated service
to the internet or a laboratory LAN.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .comparison import compare_runs
from .import_adapter import import_relaxation_upload
from .persistence import VitriFitStore
from .publication_export import export_publication_figure
from .science import fit_saved_curve, suggest_automatic_trim

DATA_DIR = Path.home() / ".vitrifit2"
MAX_UPLOAD = 50 * 1024 * 1024


def get_store() -> VitriFitStore:
    return VitriFitStore(Path(os.environ.get("VITRIFIT2_DATA_DIR", DATA_DIR)))


app = FastAPI(title="VitriFit 2.0", version="0.1.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")

# This service has no user authentication: enforce local host and origin.
@app.middleware("http")
async def localhost_only(request, call_next):
    from fastapi.responses import JSONResponse as Response
    hostname = (request.headers.get("host", "").split(":")[0]).lower()
    origin = request.headers.get("origin")
    if hostname not in ("127.0.0.1", "localhost", "testserver"):
        return Response(status_code=403, content={"detail": "Localhost access only"})
    if origin and origin not in (
        "http://127.0.0.1:8000", "http://localhost:8000",
        "http://127.0.0.1:5173", "http://localhost:5173"
    ):
        return Response(status_code=403, content={"detail": "Untrusted request origin"})
    return await call_next(request)


app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"])


@app.exception_handler(ValueError)
async def _bad_request(request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(KeyError)
async def _not_found(request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


class Named(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class Region(BaseModel):
    mode: str
    start_s: float
    end_s: float


class FitRequest(BaseModel):
    model: str = "Single_KWW"
    plateau_mode: str = "Zero"
    fixed_plateau_mpa: float = 0.0
    component: str = "characteristic"


class CompareRequest(BaseModel):
    run_ids: list[str]
    mode: str
    temperature_c: float | None = None
    kinetic_model: str = "Arrhenius"
    windows: dict[str, list[float]] = Field(default_factory=dict)


class SavedComparison(BaseModel):
    name: str
    run_ids: list[str]
    mode: str
    settings: dict = Field(default_factory=dict)


class NewPreset(BaseModel):
    name: str
    settings: dict


class NewFigure(BaseModel):
    name: str
    run_ids: list[str]
    preset_id: str | None = None
    composition: dict = Field(default_factory=dict)
    overrides: dict = Field(default_factory=dict)


@app.get("/api/health")
def health():
    return {"status": "ok", "application": "VitriFit 2.0", "storage": "local"}


@app.get("/api/backup")
def export_backup(store: VitriFitStore = Depends(get_store)):
    return Response(store.export_backup_bytes(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="vitrifit2-backup.zip"'})


@app.get("/api/projects")
def list_projects(store: VitriFitStore = Depends(get_store)):
    return store.list_projects()


@app.post("/api/projects", status_code=201)
def create_project(req: Named, store: VitriFitStore = Depends(get_store)):
    return {"id": store.create_project(req.name)}


@app.get("/api/projects/{project_id}/samples")
def list_samples(project_id: str, store: VitriFitStore = Depends(get_store)):
    return store.list_samples(project_id)


@app.post("/api/projects/{project_id}/samples", status_code=201)
def create_sample(project_id: str, req: Named, store: VitriFitStore = Depends(get_store)):
    return {"id": store.create_sample(project_id, req.name)}


@app.get("/api/samples/{sample_id}/experiments")
def list_experiments(sample_id: str, store: VitriFitStore = Depends(get_store)):
    return store.list_experiments(sample_id)


@app.post("/api/samples/{sample_id}/experiments", status_code=201)
async def import_experiment(sample_id: str,
                            file: UploadFile = File(...),
                            metadata: str = Form("{}"),
                            store: VitriFitStore = Depends(get_store)):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, f"File limit is {MAX_UPLOAD} bytes")
    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise ValueError("Experiment metadata must be valid JSON") from exc
    if not isinstance(meta, dict):
        raise ValueError("Experiment metadata must be a JSON object")
    return import_relaxation_upload(store, sample_id, Path(file.filename or "").name,
                                    content, metadata=meta)


@app.get("/api/experiments/{experiment_id}/curves")
def list_curves(experiment_id: str, store: VitriFitStore = Depends(get_store)):
    return store.list_curves(experiment_id)


@app.get("/api/curves/{curve_id}")
def get_curve(curve_id: str, store: VitriFitStore = Depends(get_store)):
    return store.get_curve(curve_id)


@app.get("/api/curves/{curve_id}/suggest-trim")
def suggest_trim(curve_id: str, store: VitriFitStore = Depends(get_store)):
    return suggest_automatic_trim(store, curve_id)


@app.post("/api/curves/{curve_id}/region")
def apply_region(curve_id: str, req: Region, store: VitriFitStore = Depends(get_store)):
    revision = store.apply_region(curve_id, req.mode, req.start_s, req.end_s)
    return {"revision_id": revision, "curve": store.get_curve(curve_id)}


@app.post("/api/curves/{curve_id}/undo")
def undo(curve_id: str, store: VitriFitStore = Depends(get_store)):
    store.undo(curve_id)
    return store.get_curve(curve_id)


@app.post("/api/curves/{curve_id}/redo")
def redo(curve_id: str, store: VitriFitStore = Depends(get_store)):
    store.redo(curve_id)
    return store.get_curve(curve_id)


@app.post("/api/curves/{curve_id}/fit", status_code=201)
def fit(curve_id: str, req: FitRequest, store: VitriFitStore = Depends(get_store)):
    return fit_saved_curve(store, curve_id, model=req.model,
                           plateau_mode=req.plateau_mode,
                           fixed_plateau_mpa=req.fixed_plateau_mpa,
                           component=req.component)


@app.get("/api/analyses")
def list_analyses(project_id: str | None = None,
                  store: VitriFitStore = Depends(get_store)):
    return store.list_analysis_runs(project_id)


@app.get("/api/analyses/{run_id}")
def analysis(run_id: str, store: VitriFitStore = Depends(get_store)):
    return store.get_analysis(run_id)


@app.post("/api/compare")
def compare(req: CompareRequest, store: VitriFitStore = Depends(get_store)):
    return compare_runs(store, req.run_ids, req.mode, req.temperature_c,
                        req.kinetic_model, req.windows)


@app.get("/api/comparisons")
def list_comparisons(store: VitriFitStore = Depends(get_store)):
    return store.list_comparisons()


@app.post("/api/comparisons", status_code=201)
def save_comparison(req: SavedComparison, store: VitriFitStore = Depends(get_store)):
    return {"id": store.save_comparison(req.name, req.mode, req.run_ids, req.settings)}


@app.get("/api/comparisons/{comparison_id}")
def load_comparison(comparison_id: str, store: VitriFitStore = Depends(get_store)):
    return store.get_comparison(comparison_id)


@app.get("/api/figures/presets")
def list_presets(store: VitriFitStore = Depends(get_store)):
    return store.list_figure_presets()


@app.post("/api/figures/presets", status_code=201)
def save_preset(req: NewPreset, store: VitriFitStore = Depends(get_store)):
    return {"id": store.save_figure_preset(req.name, req.settings)}


@app.get("/api/figures/presets/{preset_id}")
def get_preset(preset_id: str, store: VitriFitStore = Depends(get_store)):
    return store.get_figure_preset(preset_id)


@app.get("/api/figures")
def list_figures(store: VitriFitStore = Depends(get_store)):
    return store.list_saved_figures()


@app.post("/api/figures", status_code=201)
def save_figure(req: NewFigure, store: VitriFitStore = Depends(get_store)):
    return {"id": store.save_figure(req.name, req.run_ids,
                                    req.preset_id, req.composition, req.overrides)}


@app.get("/api/figures/{figure_id}")
def get_figure(figure_id: str, store: VitriFitStore = Depends(get_store)):
    return store.get_figure(figure_id)



@app.get("/api/figures/{figure_id}/export")
def export_saved_publication(figure_id: str, fmt: str = "tiff",
                             dpi: int = 300,
                             store: VitriFitStore = Depends(get_store)):
    """Export a saved manuscript figure with the exact pinned fit revisions."""
    saved = store.get_figure(figure_id)
    settings = {}
    if saved["preset_id"]:
        settings.update(store.get_figure_preset(saved["preset_id"])["settings"])
    settings.update(saved["overrides"])
    composition = saved["composition"]
    kind = {"curves": "relaxation", "relaxation": "relaxation",
            "kinetics": "kinetics",
            "fixed_temperature": "fixed_temperature"}.get(
                composition.get("plot_type", "relaxation"))
    if kind is None:
        raise ValueError("Unknown figure-composition plot type")
    content, media_type = export_publication_figure(
        store, saved["run_ids"], kind, settings, fmt=fmt, dpi=dpi,
        kinetic_model=composition.get("kinetic_model", "Arrhenius"),
        windows=composition.get("windows", {}),
        temperature_c=composition.get("temperature_c"))
    extension = "jpg" if fmt == "jpeg" else fmt
    return Response(content, media_type=media_type,
                    headers={"Content-Disposition":
                             f'attachment; filename="VitriFit_Figure_{figure_id[:8]}.{extension}"'})


# In production, serve the prebuilt React interface from the same origin.
# In development, Vite proxies /api to the localhost backend.
UI_DIST = Path(__file__).resolve().parent / "web" / "dist"
if UI_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="web")
