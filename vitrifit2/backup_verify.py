"""Read-only verification of a VitriFit backup archive before restoring.

Never extracts archive entries, overwrites a workspace or trusts a ZIP path.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

_SHA = re.compile(r"^[a-f0-9]{64}$")


def verify_backup_bytes(payload: bytes) -> dict:
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("Nonempty ZIP backup bytes required")
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            # Reject oversized or suspiciously compressed ZIP entries before reading.
            entries = archive.infolist()
            if len(entries) > 100_000:
                raise ValueError("Too many backup entries")
            if sum(item.file_size for item in entries) > 2 * 1024**3:
                raise ValueError("Backup exceeds 2 GiB uncompressed verification limit")
            if any(item.file_size > 1024**3 for item in entries):
                raise ValueError("Oversized backup entry")
            if any(item.file_size > 100 * max(1, item.compress_size)
                   and item.file_size > 1024**2 for item in entries):
                raise ValueError("Suspicious archive compression ratio")
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Duplicate ZIP entry names are unsafe")
            if "manifest.json" not in names or "vitrifit.sqlite3" not in names:
                raise ValueError("Missing backup manifest or database")
            manifest = json.loads(archive.read("manifest.json"))
            if not isinstance(manifest, dict):
                raise ValueError("Backup manifest must be a JSON object")
            if manifest.get("format") not in (
                    "vitrifit2-backup-v1", "vitrifit2-backup-v2"):
                raise ValueError("Unsupported backup format")
            declared = manifest.get("original_file_hashes")
            if not isinstance(declared, list) or len(declared) != len(set(declared)):
                raise ValueError("Invalid backup hash manifest")
            if any(not isinstance(d, str) or not _SHA.fullmatch(d) for d in declared):
                raise ValueError("Invalid SHA256 identifier")
            expected_entries = {"manifest.json", "vitrifit.sqlite3"}
            expected_entries.update("raw_blobs/" + d for d in declared)
            if set(names) != expected_entries:
                raise ValueError("Backup contains unexpected or missing entries")
            for digest in declared:
                raw = archive.read("raw_blobs/" + digest)
                if hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError("Corrupt raw blob: " + digest)
            # Validate SQLite structure and compare every referenced hash to
            # the archive manifest, not just the manifest's self-declaration.
            with tempfile.TemporaryDirectory(prefix="vitrifit-verify-") as td:
                database = Path(td) / "snapshot.sqlite3"
                database.write_bytes(archive.read("vitrifit.sqlite3"))
                connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
                try:
                    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("SQLite integrity check failed")
                    tables = {r[0] for r in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                    if "experiments" not in tables:
                        raise ValueError("Not a VitriFit database")
                    referenced = {r[0] for r in connection.execute(
                        "SELECT DISTINCT file_sha256 FROM experiments")}
                    if "v2_measurement_files" in tables:
                        referenced.update(r[0] for r in connection.execute(
                            "SELECT DISTINCT sha256 FROM v2_measurement_files"))
                finally:
                    connection.close()
            if referenced != set(declared):
                raise ValueError("Database references do not match archived raw files")
            return {"status": "verified", "format": manifest["format"],
                    "raw_blob_count": len(declared),
                    "database_integrity": "ok",
                    "safe_to_consider_restore": True,
                    "warning": "Verification does not perform a restore."}
    except (BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError,
            sqlite3.DatabaseError, OSError, EOFError, RuntimeError) as exc:
        raise ValueError("Invalid or incomplete VitriFit backup ZIP") from exc
