"""Preserved publication settings, auto-trim proposals and complete backups."""
from io import BytesIO
import hashlib
import json
from zipfile import ZipFile

import numpy as np
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.publication_presets import capture_publication_settings, apply_publication_settings
from vitrifit2.science import suggest_automatic_trim


def test_publication_snapshot_keeps_scientific_style_keys():
    state = {
        "pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
        "pub_w": 8.5, "pub_h": 7.5, "pub_rel_lw": 1.5,
        "pub_kinfont_family": "Arial", "eyr_lw": 2.0,
        "vh_legfont": 10, "sh_fig3": True, "plx_2": -.12,
        "active_results": ["not a figure style"],
        "v2_saved_style_selected": "not part of publication"
    }
    snapshot = capture_publication_settings(state)
    assert snapshot["eyr_lw"] == 2.0
    assert snapshot["vh_legfont"] == 10
    assert "active_results" not in snapshot
    assert "v2_saved_style_selected" not in snapshot
    restored = {}
    count = apply_publication_settings(restored, snapshot)
    assert count >= 9
    assert restored["pub_size_preset"] == state["pub_preset"]
    assert restored["sh_fig3"]


def test_backup_roundtrip_original_upload_and_sqlite(tmp_path):
    store = VitriFitStore(tmp_path / "library")
    sample = store.create_sample(store.create_project("LCE"), "LCE2")
    raw = b"unaltered-input-123"
    imported = store.import_experiment(sample, "input.csv", raw,
        [{"source_curve_id": "c1", "temperature_c": 100,
          "time_s": [0.01, 1, 2], "modulus_mpa": [2, 1.3, 0.9]}])
    store.apply_region(imported["curve_ids"][0], "keep", 0.01, 1)
    backup = store.export_backup_bytes()
    with ZipFile(BytesIO(backup)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["format"] == "vitrifit2-backup-v2"
        digest = hashlib.sha256(raw).hexdigest()
        assert archive.read("raw_blobs/" + digest) == raw
        # Restoration to a separate directory, matching documented manual recovery.
        restored_dir = tmp_path / "restored"
        restored_dir.mkdir()
        archive.extractall(restored_dir)
    restored = VitriFitStore(restored_dir)
    assert restored.get_original_file(imported["experiment_id"]) == raw
    assert sum(restored.get_curve(imported["curve_ids"][0])["mask"]) == 2


def test_automatic_suggestion_does_not_change_curve(tmp_path):
    store = VitriFitStore(tmp_path / "library")
    sample = store.create_sample(store.create_project("LCE"), "IPN")
    times = np.geomspace(.01, 100, 100).tolist()
    modulus = np.exp(-np.asarray(times)/30).tolist()
    exp = store.import_experiment(sample, "original.csv", b"original",
        [{"source_curve_id": "c1", "temperature_c": 100,
          "time_s": times, "modulus_mpa": modulus}])
    cid = exp["curve_ids"][0]
    before = store.get_curve(cid)["active_revision_id"]
    proposal = suggest_automatic_trim(store, cid)
    assert not proposal["applied"]
    assert proposal["start_s"] <= proposal["end_s"]
    assert store.get_curve(cid)["active_revision_id"] == before
