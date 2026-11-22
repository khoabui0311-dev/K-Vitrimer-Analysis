"""Numerical validation for the saved-curve fitting entry point.

Invalid instrument values must fail before crossing interpolation or nonlinear
optimization, rather than producing plausible but scientifically invalid tau.
"""
import numpy as np
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.science import fit_saved_curve


@pytest.mark.parametrize(
    "bad_time,bad_modulus,expected",
    [
        (float("nan"), None, "non-finite"),
        (float("inf"), None, "non-finite"),
        (None, float("nan"), "non-finite"),
        (None, float("inf"), "non-finite"),
        (-0.5, None, "negative elapsed time"),
    ],
)
def test_invalid_instrument_values_rejected_before_fit(
    tmp_path, bad_time, bad_modulus, expected
):
    store = VitriFitStore(tmp_path / "store")
    project_id = store.create_project("Numerical guards")
    sample_id = store.create_sample(project_id, "Synthetic")
    t = np.linspace(0.01, 60.0, 40)
    g = np.exp(-t / 12.0)
    if bad_time is not None:
        t[3] = bad_time
    if bad_modulus is not None:
        g[3] = bad_modulus
    try:
        imported = store.import_experiment(
            sample_id, "synthetic.csv", b"synthetic-invalid-input",
            [{"source_curve_id": "70C", "temperature_c": 70,
              "time_s": t.tolist(), "modulus_mpa": g.tolist()}],
        )
    except ValueError:
        # Strict import-time rejection is also acceptable and preferable.
        return
    with pytest.raises(ValueError, match=expected):
        fit_saved_curve(store, imported["curve_ids"][0], model="Maxwell")
