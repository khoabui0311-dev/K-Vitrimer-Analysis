"""Raw uploads are immutable and corruption must not be silently reused."""
import hashlib
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import (
    create_specimen, create_measurement, attach_measurement_file,
    get_measurement_file, list_measurement_files,
)


@pytest.fixture
def measurement(tmp_path):
    store = VitriFitStore(tmp_path)
    sample = store.create_sample(store.create_project("P"), "S")
    specimen = create_specimen(store, sample, "film")
    mid = create_measurement(store, specimen, "DSC", "calorimetry")
    return store, mid


def test_duplicate_raw_bytes_share_immutable_digest(measurement):
    store, mid = measurement
    payload = b"temperature,heat\n20,1\n30,2\n"
    first = attach_measurement_file(store, mid, "first.csv", payload)
    second = attach_measurement_file(store, mid, "second.csv", payload)
    assert first != second
    assert get_measurement_file(store, first) == payload
    assert get_measurement_file(store, second) == payload
    assert len(list(store.blobs.iterdir())) == 1


def test_corrupted_existing_blob_rejected_before_new_record(measurement):
    store, mid = measurement
    payload = b"temperature,heat\n20,1\n30,2\n"
    first = attach_measurement_file(store, mid, "original.csv", payload)
    digest = hashlib.sha256(payload).hexdigest()
    (store.blobs / digest).write_bytes(b"tampered")
    with pytest.raises(IOError, match="corrupt"):
        attach_measurement_file(store, mid, "duplicate.csv", payload)
    assert len(list_measurement_files(store, mid)) == 1
    with pytest.raises(IOError, match="integrity"):
        get_measurement_file(store, first)


def test_missing_raw_blob_is_actionable(measurement):
    store, mid = measurement
    payload = b"raw"
    file_id = attach_measurement_file(store, mid, "raw.csv", payload)
    (store.blobs / hashlib.sha256(payload).hexdigest()).unlink()
    with pytest.raises(IOError, match="missing"):
        get_measurement_file(store, file_id)
