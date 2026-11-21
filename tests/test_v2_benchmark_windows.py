"""Independent ground-truth tests of measurement-window sensitivity."""
import pytest
from vitrifit2.benchmark_suite import relaxation_case
from vitrifit2.benchmark_windows import window_sensitivity


def test_full_window_recovers_kww_ground_truth():
    case = relaxation_case("kww", tau_s=100., beta=.65)
    report = window_sensitivity(case.time_s, case.normalized_modulus)
    full = report["windows"][0]
    assert full["status"] == "ok"
    assert full["parameters"][0] == pytest.approx(100., rel=.01)
    assert full["parameters"][1] == pytest.approx(.65, abs=.01)
    assert full["relative_parameter_change"] == pytest.approx([0., 0.])


def test_windows_have_monotonically_shorter_end_times():
    case = relaxation_case("maxwell", tau_s=100.)
    report = window_sensitivity(case.time_s, case.normalized_modulus,
                                model="maxwell")
    windows = report["windows"]
    assert all(item["status"] == "ok" for item in windows)
    assert all(a["last_time_s"] > b["last_time_s"]
               for a, b in zip(windows, windows[1:]))
    assert windows[-1]["points"] < windows[0]["points"]


@pytest.mark.parametrize("fractions", [(0,), (1.2,), (float("nan"),)])
def test_invalid_window_fractions_rejected(fractions):
    case = relaxation_case("kww")
    with pytest.raises(ValueError):
        window_sensitivity(case.time_s, case.normalized_modulus,
                           fractions=fractions)
