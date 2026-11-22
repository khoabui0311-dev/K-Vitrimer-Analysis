"""Local-only sample profile and rheology endpoints for the v2 web app."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .persistence import VitriFitStore
from .sample_profile import (
    create_specimen, create_measurement, get_sample_profile,
    list_measurement_files, get_measurement_file,
)
from .rheology_workflow import analyze_rheology_csv, get_rheology_analysis
from .rheology_history import (
    list_rheology_analyses, reanalyze_rheology_file,
    compare_rheology_analyses, check_frequency_sweep_lvr,
)
from .rheology_manifest import export_rheology_manifest_json
from .tensile_workflow import import_tensile_csv, get_tensile_analysis, list_tensile_analyses
from .thermal_workflow import import_thermal_csv, get_thermal_analysis, list_thermal_analyses

router = APIRouter(prefix="/api/v2", tags=["Sample profiles and rheology"])
MAX_UPLOAD = 50 * 1024 * 1024


def store_dependency():
    # Import lazily to avoid circular dependency with the main API module.
    from .api import get_store
    return get_store()


class SpecimenInput(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    metadata: dict = Field(default_factory=dict)


class MeasurementInput(BaseModel):
    technique: str
    method: str
    conditions: dict = Field(default_factory=dict)


class ReanalysisInput(BaseModel):
    plateau_points: int | None = None
    departure_fraction: float | None = None
    max_plateau_cv: float | None = None


class ComparisonInput(BaseModel):
    analysis_ids: list[str] = Field(min_length=2)
    required_condition_keys: list[str] = Field(min_length=1)


class ManifestInput(BaseModel):
    analysis_ids: list[str] = Field(min_length=1)
    include_results: bool = True


class LvrEvidenceInput(BaseModel):
    frequency_analysis_id: str
    lvr_analysis_id: str


@router.get("/samples/{sample_id}/profile")
def sample_profile(sample_id: str, store: VitriFitStore = Depends(store_dependency)):
    return get_sample_profile(store, sample_id)


@router.post("/samples/{sample_id}/specimens", status_code=201)
def new_specimen(sample_id: str, req: SpecimenInput,
                 store: VitriFitStore = Depends(store_dependency)):
    return {"id": create_specimen(store, sample_id, req.label, req.metadata)}


@router.post("/specimens/{specimen_id}/measurements", status_code=201)
def new_measurement(specimen_id: str, req: MeasurementInput,
                    store: VitriFitStore = Depends(store_dependency)):
    return {"id": create_measurement(
        store, specimen_id, req.technique, req.method, req.conditions)}


@router.get("/measurements/{measurement_id}/files")
def measurement_files(measurement_id: str,
                      store: VitriFitStore = Depends(store_dependency)):
    return list_measurement_files(store, measurement_id)


@router.get("/files/{file_id}/raw")
def download_raw(file_id: str, store: VitriFitStore = Depends(store_dependency)):
    # Keep downloaded filename generic; never trust an uploaded filename as a path.
    return Response(get_measurement_file(store, file_id),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": 'attachment; filename="vitrifit-original.bin"'})


@router.post("/measurements/{measurement_id}/rheology/import", status_code=201)
async def import_rheology(
    measurement_id: str,
    file: UploadFile = File(...),
    method: str = Form(...),
    columns_json: str = Form(...),
    frequency_unit: str = Form("Hz"),
    modulus_unit: str = Form("Pa"),
    plateau_points: int = Form(5),
    departure_fraction: float = Form(.05),
    max_plateau_cv: float = Form(.03),
    store: VitriFitStore = Depends(store_dependency),
):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "Upload exceeds 50 MiB")
    try:
        columns = json.loads(columns_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Column mapping must be valid JSON") from exc
    if not isinstance(columns, dict):
        raise ValueError("Column mapping must be a JSON object")
    analysis_id = analyze_rheology_csv(
        store, measurement_id, Path(file.filename or "upload.csv").name,
        content, method=method, columns=columns,
        frequency_unit=frequency_unit, modulus_unit=modulus_unit,
        plateau_points=plateau_points,
        departure_fraction=departure_fraction,
        max_plateau_cv=max_plateau_cv)
    return get_rheology_analysis(store, analysis_id)


@router.get("/measurements/{measurement_id}/rheology/analyses")
def analysis_history(measurement_id: str,
                     store: VitriFitStore = Depends(store_dependency)):
    return list_rheology_analyses(store, measurement_id)


@router.get("/rheology/analyses/{analysis_id}")
def load_analysis(analysis_id: str,
                  store: VitriFitStore = Depends(store_dependency)):
    return get_rheology_analysis(store, analysis_id)


@router.post("/rheology/analyses/{analysis_id}/reanalyze", status_code=201)
def reanalyze(analysis_id: str, req: ReanalysisInput,
              store: VitriFitStore = Depends(store_dependency)):
    new_id = reanalyze_rheology_file(
        store, analysis_id, plateau_points=req.plateau_points,
        departure_fraction=req.departure_fraction,
        max_plateau_cv=req.max_plateau_cv)
    return get_rheology_analysis(store, new_id)


@router.post("/rheology/compare")
def compare(req: ComparisonInput, store: VitriFitStore = Depends(store_dependency)):
    return compare_rheology_analyses(
        store, req.analysis_ids,
        required_condition_keys=req.required_condition_keys)


@router.post("/rheology/lvr-evidence")
def lvr_evidence(req: LvrEvidenceInput,
                 store: VitriFitStore = Depends(store_dependency)):
    return check_frequency_sweep_lvr(
        store, req.frequency_analysis_id, req.lvr_analysis_id)


@router.post("/rheology/manifest")
def manifest(req: ManifestInput, store: VitriFitStore = Depends(store_dependency)):
    content = export_rheology_manifest_json(
        store, req.analysis_ids, include_results=req.include_results)
    return Response(content, media_type="application/json",
                    headers={"Content-Disposition":
                             'attachment; filename="vitrifit-rheology-manifest.json"'})


@router.post("/measurements/{measurement_id}/tensile/import", status_code=201)
async def import_tensile(
    measurement_id: str,
    file: UploadFile = File(...),
    columns_json: str = Form(...),
    gauge_length_mm: float = Form(...),
    width_mm: float = Form(...),
    thickness_mm: float = Form(...),
    modulus_fit_strain_min: float = Form(.0005),
    modulus_fit_strain_max: float = Form(.005),
    calculate_true: bool = Form(True),
    store: VitriFitStore = Depends(store_dependency),
):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "Upload exceeds 50 MiB")
    try:
        columns = json.loads(columns_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Column mapping must be valid JSON") from exc
    if not isinstance(columns, dict):
        raise ValueError("Column mapping must be an object")
    aid = import_tensile_csv(
        store, measurement_id, Path(file.filename or "tensile.csv").name,
        content, columns=columns, gauge_length_mm=gauge_length_mm,
        width_mm=width_mm, thickness_mm=thickness_mm,
        modulus_fit_strain_min=modulus_fit_strain_min,
        modulus_fit_strain_max=modulus_fit_strain_max,
        calculate_true=calculate_true)
    return get_tensile_analysis(store, aid)


@router.get("/measurements/{measurement_id}/tensile/analyses")
def tensile_history(measurement_id: str,
                    store: VitriFitStore = Depends(store_dependency)):
    return list_tensile_analyses(store, measurement_id)


@router.get("/tensile/analyses/{analysis_id}")
def tensile_analysis(analysis_id: str,
                     store: VitriFitStore = Depends(store_dependency)):
    return get_tensile_analysis(store, analysis_id)


@router.post("/measurements/{measurement_id}/thermal/import", status_code=201)
async def import_thermal(
    measurement_id: str,
    file: UploadFile = File(...),
    method: str = Form(...),
    columns_json: str = Form(...),
    modulus_unit: str = Form("Pa"),
    heat_flow_unit: str = Form("mW"),
    heating_rate_c_min: float | None = Form(None),
    store: VitriFitStore = Depends(store_dependency),
):
    content = await file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, "Upload exceeds 50 MiB")
    try:
        columns = json.loads(columns_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Column mapping must be valid JSON") from exc
    if not isinstance(columns, dict):
        raise ValueError("Column mapping must be a JSON object")
    aid = import_thermal_csv(
        store, measurement_id, Path(file.filename or "thermal.csv").name,
        content, method=method, columns=columns,
        modulus_unit=modulus_unit, heat_flow_unit=heat_flow_unit,
        heating_rate_c_min=heating_rate_c_min)
    return get_thermal_analysis(store, aid)


@router.get("/measurements/{measurement_id}/thermal/analyses")
def thermal_history(measurement_id: str,
                    store: VitriFitStore = Depends(store_dependency)):
    return list_thermal_analyses(store, measurement_id)


@router.get("/thermal/analyses/{analysis_id}")
def thermal_analysis(analysis_id: str,
                     store: VitriFitStore = Depends(store_dependency)):
    return get_thermal_analysis(store, analysis_id)
