"""Metadata compatibility regression tests for LVR screening."""
import pytest

from vitrifit2.lvr_compatibility import assess_lvr_compatibility

EVIDENCE = {
    "status": "departure_detected",
    "highest_measured_in_range_strain_percent": 0.1,
    "first_departure_strain_percent": 0.2,
}
BASE = dict(
    applied_strain_percent=.05, experiment_mode="oscillatory_shear",
    temperature_c=40, frequency_hz=1, specimen_id="vugt-01",
    geometry_id="plate-8mm", material_state_id="annealed",
    lvr_temperature_c=40, lvr_frequency_hz=1, lvr_specimen_id="vugt-01",
    lvr_geometry_id="plate-8mm", lvr_material_state_id="annealed",
)


def check(**changes):
    return assess_lvr_compatibility(EVIDENCE, **(BASE | changes))


def test_matching_oscillatory_conditions_are_supported():
    r = check()
    assert r["status"] == "verified_oscillatory_lvr"
    assert r["supporting_oscillatory_evidence"]
    assert r["step_strain_verified"] is False


def test_unmeasured_intermediate_temperature_is_not_verified():
    assert check(temperature_c=100)["status"] == "not_directly_verified"


def test_mismatched_frequency_is_not_verified():
    assert check(frequency_hz=10)["status"] == "not_directly_verified"


def test_step_strain_never_directly_verified():
    r = check(experiment_mode="step_shear")
    assert r["status"] == "not_directly_verified"
    assert not r["step_strain_verified"]


@pytest.mark.parametrize("field,value", [
    ("specimen_id", "vugt-02"),
    ("geometry_id", "cone"),
    ("material_state_id", "unannealed"),
])
def test_mismatched_specimen_geometry_or_state_not_verified(field, value):
    assert check(**{field: value})["status"] == "not_directly_verified"


def test_departure_and_unmeasured_gap_are_distinguished():
    assert check(applied_strain_percent=.2)["status"] == "outside_measured_lvr"
    assert check(applied_strain_percent=.15)["status"] == "not_directly_verified"


def test_screening_without_plateau_cannot_verify():
    r = assess_lvr_compatibility({"status": "indeterminate"}, **BASE)
    assert r["status"] == "not_directly_verified"


def test_invalid_frequency_rejected():
    with pytest.raises(ValueError):
        check(frequency_hz=0)
