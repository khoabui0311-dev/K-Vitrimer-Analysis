"""Persistent, local-first foundation for VitriFit 2.0.

No UI dependency. Original upload bytes and raw curve observations are immutable.
Editing creates an inclusion mask/revision; scientific results pin that revision.
This is a standalone prototype store, not a replacement for v1 analysis code.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


def _id() -> str:
    return uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)


class VitriFitStore:
    """Single-user SQLite + content-addressed raw-file store.

    Each method uses a short transaction, so browser reloads and process restarts
    do not discard the active edit revision or undo/redo stack.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs = self.root / "raw_blobs"
        self.blobs.mkdir(exist_ok=True)
        self.db_path = self.root / "vitrifit.sqlite3"
        self._init_schema()

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_schema(self):
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS samples (
                id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY, sample_id TEXT NOT NULL REFERENCES samples(id),
                original_filename TEXT NOT NULL, file_sha256 TEXT NOT NULL,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS curves (
                id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiments(id),
                source_curve_id TEXT NOT NULL, temperature_c REAL NOT NULL,
                raw_json TEXT NOT NULL, active_revision_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS processing_revisions (
                id TEXT PRIMARY KEY, curve_id TEXT NOT NULL REFERENCES curves(id),
                parent_revision_id TEXT REFERENCES processing_revisions(id),
                mask_json TEXT NOT NULL, operation_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edit_state (
                curve_id TEXT PRIMARY KEY REFERENCES curves(id),
                redo_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY, curve_id TEXT NOT NULL REFERENCES curves(id),
                revision_id TEXT NOT NULL REFERENCES processing_revisions(id),
                model TEXT NOT NULL, tau_definition TEXT NOT NULL,
                config_json TEXT NOT NULL, results_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comparison_sessions (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, mode TEXT NOT NULL,
                run_ids_json TEXT NOT NULL, settings_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS figure_presets (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, settings_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saved_figures (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                run_ids_json TEXT NOT NULL, preset_id TEXT REFERENCES figure_presets(id),
                overrides_json TEXT NOT NULL, composition_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_curves_experiment ON curves(experiment_id);
            CREATE INDEX IF NOT EXISTS idx_runs_curve ON analysis_runs(curve_id);
            """)

    @staticmethod
    def _require(db, table: str, key: str):
        # table is always a code-controlled literal, not user input
        row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(f"{table}: no record {key}")
        return row

    def create_project(self, name: str) -> str:
        if not name.strip():
            raise ValueError("Project name is required")
        key = _id()
        with self._db() as db:
            db.execute("INSERT INTO projects VALUES (?, ?, ?)", (key, name.strip(), _now()))
        return key

    def create_sample(self, project_id: str, name: str) -> str:
        if not name.strip():
            raise ValueError("Sample name is required")
        key = _id()
        with self._db() as db:
            self._require(db, "projects", project_id)
            db.execute("INSERT INTO samples VALUES (?, ?, ?, ?)", (key, project_id, name.strip(), _now()))
        return key

    @staticmethod
    def _validate_curve(curve: dict) -> tuple[str, float, list, list]:
        source = str(curve["source_curve_id"])
        temp = float(curve["temperature_c"])
        times = [float(v) for v in curve["time_s"]]
        modulus = [float(v) for v in curve["modulus_mpa"]]
        if not source or not math.isfinite(temp) or temp <= -273.15:
            raise ValueError("Curve identifier and physical temperature are required")
        if len(times) < 2 or len(times) != len(modulus):
            raise ValueError("Curve needs at least two paired observations")
        if (any(not math.isfinite(v) or v < 0 for v in times)
                or any(not math.isfinite(v) for v in modulus)):
            raise ValueError("Raw observations must be finite; time must be nonnegative")
        # Never reorder or discard raw points: each mask index refers to an original row.
        return source, temp, times, modulus

    def import_experiment(self, sample_id: str, filename: str, raw_bytes: bytes,
                          curves: list[dict], metadata: dict | None = None) -> dict:
        """Store an original file and its parsed, row-aligned curves.

        Parsing/units conversion belongs to an instrument adapter (v1 parser
        can be bridged later). This method stores the canonical output in s/MPa.
        """
        if not filename.strip() or not raw_bytes or not curves:
            raise ValueError("Filename, original bytes, and curves are required")
        if not isinstance(raw_bytes, bytes):
            raise TypeError("raw_bytes must be bytes")
        validated = [self._validate_curve(c) for c in curves]
        digest = hashlib.sha256(raw_bytes).hexdigest()
        target = self.blobs / digest
        if not target.exists():
            temp_file = self.blobs / f".{digest}.{_id()}.tmp"
            try:
                temp_file.write_bytes(raw_bytes)
                temp_file.replace(target)
            finally:
                temp_file.unlink(missing_ok=True)
        experiment_id = _id()
        curve_ids = []
        with self._db() as db:
            self._require(db, "samples", sample_id)
            db.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?)",
                       (experiment_id, sample_id, filename, digest, _json(metadata or {}), _now()))
            for source, temperature, times, modulus in validated:
                curve_id = _id()
                revision_id = _id()
                raw = {"time_s": times, "modulus_mpa": modulus}
                db.execute("INSERT INTO curves VALUES (?,?,?,?,?,?,?)",
                           (curve_id, experiment_id, source, temperature, _json(raw), revision_id, _now()))
                db.execute("INSERT INTO processing_revisions VALUES (?,?,?,?,?,?)",
                           (revision_id, curve_id, None, _json([True] * len(times)),
                            _json({"type": "import", "time_origin": "instrument_unmodified"}), _now()))
                db.execute("INSERT INTO edit_state VALUES (?, '[]')", (curve_id,))
                curve_ids.append(curve_id)
        return {"experiment_id": experiment_id, "curve_ids": curve_ids, "file_sha256": digest}

    def get_original_file(self, experiment_id: str) -> bytes:
        with self._db() as db:
            experiment = self._require(db, "experiments", experiment_id)
        content = (self.blobs / experiment["file_sha256"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != experiment["file_sha256"]:
            raise IOError("Original file integrity check failed")
        return content

    def get_curve(self, curve_id: str) -> dict:
        with self._db() as db:
            curve = self._require(db, "curves", curve_id)
            revision = self._require(db, "processing_revisions", curve["active_revision_id"])
            state = db.execute("SELECT redo_json FROM edit_state WHERE curve_id=?", (curve_id,)).fetchone()
            raw = json.loads(curve["raw_json"])
            mask = json.loads(revision["mask_json"])
            return {"curve_id": curve_id, "experiment_id": curve["experiment_id"],
                    "source_curve_id": curve["source_curve_id"],
                    "temperature_c": curve["temperature_c"], **raw,
                    "mask": mask, "active_revision_id": revision["id"],
                    "can_undo": revision["parent_revision_id"] is not None,
                    "can_redo": bool(json.loads(state["redo_json"]))}

    def _set_head(self, db, curve_id: str, revision_id: str, redo: list[str]):
        db.execute("UPDATE curves SET active_revision_id=? WHERE id=?", (revision_id, curve_id))
        db.execute("UPDATE edit_state SET redo_json=? WHERE curve_id=?", (_json(redo), curve_id))

    def apply_region(self, curve_id: str, mode: str, start_s: float, end_s: float) -> str:
        """Apply an inclusive time interval to ONE curve, never alter raw data."""
        if mode not in ("keep", "exclude"):
            raise ValueError("mode must be 'keep' or 'exclude'")
        if not all(math.isfinite(float(v)) for v in (start_s, end_s)) or start_s > end_s:
            raise ValueError("Invalid time selection")
        with self._db() as db:
            curve = self._require(db, "curves", curve_id)
            parent_id = curve["active_revision_id"]
            parent = self._require(db, "processing_revisions", parent_id)
            raw = json.loads(curve["raw_json"])
            prev = json.loads(parent["mask_json"])
            inside = [start_s <= t <= end_s for t in raw["time_s"]]
            mask = [old and (hit if mode == "keep" else not hit)
                    for old, hit in zip(prev, inside)]
            if sum(mask) < 2:
                raise ValueError("Selection leaves fewer than two included points")
            revision_id = _id()
            db.execute("INSERT INTO processing_revisions VALUES (?,?,?,?,?,?)",
                       (revision_id, curve_id, parent_id, _json(mask),
                        _json({"type": "region", "mode": mode, "start_s": start_s,
                               "end_s": end_s, "time_origin": "instrument_unmodified"}), _now()))
            self._set_head(db, curve_id, revision_id, [])
        return revision_id

    def undo(self, curve_id: str) -> str:
        with self._db() as db:
            curve = self._require(db, "curves", curve_id)
            head = self._require(db, "processing_revisions", curve["active_revision_id"])
            parent = head["parent_revision_id"]
            if parent is None:
                raise ValueError("No trim operation to undo")
            state = db.execute("SELECT redo_json FROM edit_state WHERE curve_id=?", (curve_id,)).fetchone()
            redo = json.loads(state["redo_json"])
            redo.append(head["id"])
            self._set_head(db, curve_id, parent, redo)
            return parent

    def redo(self, curve_id: str) -> str:
        with self._db() as db:
            curve = self._require(db, "curves", curve_id)
            state = db.execute("SELECT redo_json FROM edit_state WHERE curve_id=?", (curve_id,)).fetchone()
            redo = json.loads(state["redo_json"])
            if not redo:
                raise ValueError("No trim operation to redo")
            target = redo.pop()
            revision = self._require(db, "processing_revisions", target)
            if revision["curve_id"] != curve_id or revision["parent_revision_id"] != curve["active_revision_id"]:
                raise ValueError("Undo history was branched or corrupted")
            self._set_head(db, curve_id, target, redo)
            return target

    def save_analysis(self, curve_id: str, model: str, tau_definition: str,
                      config: dict, results: dict) -> str:
        """Pin results to the current processing revision; never overwrite fits."""
        if not model.strip() or not tau_definition.strip():
            raise ValueError("Model and relaxation time definition are required")
        key = _id()
        with self._db() as db:
            curve = self._require(db, "curves", curve_id)
            db.execute("INSERT INTO analysis_runs VALUES (?,?,?,?,?,?,?,?)",
                       (key, curve_id, curve["active_revision_id"], model, tau_definition,
                        _json(config), _json(results), _now()))
        return key

    def get_analysis(self, run_id: str) -> dict:
        with self._db() as db:
            run = self._require(db, "analysis_runs", run_id)
            curve = self._require(db, "curves", run["curve_id"])
            return {"id": run_id, "curve_id": run["curve_id"],
                    "revision_id": run["revision_id"],
                    "is_current": run["revision_id"] == curve["active_revision_id"],
                    "model": run["model"], "tau_definition": run["tau_definition"],
                    "config": json.loads(run["config_json"]),
                    "results": json.loads(run["results_json"])}

    def save_comparison(self, name: str, mode: str, run_ids: list[str],
                        settings: dict | None = None) -> str:
        if mode not in ("curves", "kinetics", "fixed_temperature") or len(set(run_ids)) < 2:
            raise ValueError("Select a comparison mode and at least two distinct analysis runs")
        key = _id()
        with self._db() as db:
            for run_id in run_ids:
                self._require(db, "analysis_runs", run_id)
            db.execute("INSERT INTO comparison_sessions VALUES (?,?,?,?,?,?)",
                       (key, name, mode, _json(run_ids), _json(settings or {}), _now()))
        return key

    def get_comparison(self, comparison_id: str) -> dict:
        with self._db() as db:
            row = self._require(db, "comparison_sessions", comparison_id)
            return {"id": comparison_id, "name": row["name"], "mode": row["mode"],
                    "run_ids": json.loads(row["run_ids_json"]),
                    "settings": json.loads(row["settings_json"])}

    def save_figure_preset(self, name: str, settings: dict) -> str:
        """Preserve existing v1 publication widget/state keys without rewriting."""
        if not name.strip():
            raise ValueError("Preset name is required")
        key = _id()
        with self._db() as db:
            db.execute("INSERT INTO figure_presets VALUES (?,?,?,?)",
                       (key, name.strip(), _json(settings), _now()))
        return key

    def get_figure_preset(self, preset_id: str) -> dict:
        with self._db() as db:
            row = self._require(db, "figure_presets", preset_id)
            return {"id": preset_id, "name": row["name"],
                    "settings": json.loads(row["settings_json"])}

    def save_figure(self, name: str, run_ids: list[str], preset_id: str | None,
                    composition: dict, overrides: dict | None = None) -> str:
        if not name.strip() or not run_ids:
            raise ValueError("Figure name and referenced analyses are required")
        key = _id()
        with self._db() as db:
            for run_id in run_ids:
                self._require(db, "analysis_runs", run_id)
            if preset_id is not None:
                self._require(db, "figure_presets", preset_id)
            db.execute("INSERT INTO saved_figures VALUES (?,?,?,?,?,?,?)",
                       (key, name, _json(run_ids), preset_id, _json(overrides or {}),
                        _json(composition), _now()))
        return key

    def get_figure(self, figure_id: str) -> dict:
        with self._db() as db:
            row = self._require(db, "saved_figures", figure_id)
            return {"id": figure_id, "name": row["name"],
                    "run_ids": json.loads(row["run_ids_json"]),
                    "preset_id": row["preset_id"],
                    "overrides": json.loads(row["overrides_json"]),
                    "composition": json.loads(row["composition_json"])}
