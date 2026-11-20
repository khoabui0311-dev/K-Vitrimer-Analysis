"""Import adapter must reuse the established v1 parser, not a new parser."""
from pathlib import Path

from vitrifit2.import_adapter import import_relaxation_upload
from vitrifit2.persistence import VitriFitStore


def test_existing_wide_csv_imports_and_survives_restart(tmp_path):
    store = VitriFitStore(tmp_path / "db")
    sample = store.create_sample(store.create_project("Project"), "Sample")
    source = Path("examples/toy_data.csv").read_bytes()
    result = import_relaxation_upload(store, sample, "toy_data.csv", source)
    assert result["curve_ids"]
    reopened = VitriFitStore(store.root)
    assert reopened.get_original_file(result["experiment_id"]) == source
    for cid in result["curve_ids"]:
        curve = reopened.get_curve(cid)
        assert len(curve["time_s"]) == len(curve["modulus_mpa"])
        assert len(curve["mask"]) == len(curve["time_s"])
        assert curve["active_revision_id"]


def test_reject_unhandled_legacy_xls(tmp_path):
    store = VitriFitStore(tmp_path / "db")
    sample = store.create_sample(store.create_project("Project"), "Sample")
    try:
        import_relaxation_upload(store, sample, "raw.xls", b"legacy")
    except ValueError as exc:
        assert "CSV, TXT or XLSX" in str(exc)
    else:
        raise AssertionError("Expected unsupported format error")
