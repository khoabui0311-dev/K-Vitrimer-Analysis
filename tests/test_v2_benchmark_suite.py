"""Independent benchmark tests: mathematical ground truth and published summaries."""
import math
import pytest

from vitrifit2.benchmark_suite import (
    R, LITERATURE_EPOXY_REFERENCE, apparent_arrhenius_ea,
    arrhenius_tau, relaxation_case, time_grid, vft_tau,
)


def test_time_grid_positive_strictly_increasing():
    times = time_grid()
    assert times[0] == pytest.approx(0.01)
    assert times[-1] == pytest.approx(10000)
    assert all(b > a > 0 for a, b in zip(times, times[1:]))


@pytest.mark.parametrize("model", ["maxwell", "kww", "dual_maxwell"])
def test_noise_free_relaxation_matches_known_analytical_function(model):
    case = relaxation_case(model, tau_s=100, beta=.65,
                           fast_fraction=.3, fast_tau_s=10)
    for t, g in zip(case.time_s, case.normalized_modulus):
        expected = {
            "maxwell": lambda: math.exp(-t / 100),
            "kww": lambda: math.exp(-(t / 100) ** .65),
            "dual_maxwell": lambda: .3 * math.exp(-t / 10) + .7 * math.exp(-t / 100),
        }[model]()
        assert g == pytest.approx(expected, abs=1e-14)


def test_kww_beta_one_reduces_to_maxwell():
    a = relaxation_case("maxwell")
    b = relaxation_case("kww", beta=1)
    assert a.normalized_modulus == b.normalized_modulus


def test_noise_is_seeded_and_not_clipped():
    a = relaxation_case("maxwell", noise_fraction=.02, seed=41)
    b = relaxation_case("maxwell", noise_fraction=.02, seed=41)
    c = relaxation_case("maxwell", noise_fraction=.02, seed=42)
    assert a.normalized_modulus == b.normalized_modulus
    assert a.normalized_modulus != c.normalized_modulus
    assert any(g < 0 for g in a.normalized_modulus)


def test_arrhenius_known_activation_energy_recovered():
    temperatures = (100., 120., 140., 160., 180.)
    tau = arrhenius_tau(temperatures, activation_kj_mol=85)
    assert apparent_arrhenius_ea(temperatures, tau) == pytest.approx(85, abs=1e-9)
    assert tau[0] > tau[-1]


def test_vft_formula_and_monotonicity():
    temps = (70., 90., 110., 130.)
    tau = vft_tau(temps, a=-4, b_kelvin=500, t0_c=20)
    assert tau[0] == pytest.approx(math.exp(-4 + 500 / 50))
    assert all(a > b for a, b in zip(tau, tau[1:]))


def test_literature_reference_is_not_raw_curve_ground_truth():
    ref = LITERATURE_EPOXY_REFERENCE
    assert ref["doi"] == "10.3390/ma14040919"
    assert ref["tau_definition"] == "observed 1/e crossing"
    assert "not digitized raw data" in ref["provenance"]
    for name in ("evs_tau_s", "evd_tau_s"):
        assert len(ref[name]) == len(ref["temperature_c"]) == 5
        assert all(a > b > 0 for a, b in zip(ref[name], ref[name][1:]))


@pytest.mark.parametrize("invalid", [-1., 0., float("nan")])
def test_invalid_maxwell_tau_rejected(invalid):
    with pytest.raises(ValueError):
        relaxation_case("maxwell", tau_s=invalid)


def test_invalid_arrhenius_temperature_rejected():
    with pytest.raises(ValueError):
        arrhenius_tau((-273.15, 100.))


def test_invalid_vft_temperature_rejected():
    with pytest.raises(ValueError):
        vft_tau((20., 100.), t0_c=20.)


def test_duplicate_temperature_cannot_determine_activation_energy():
    with pytest.raises(ValueError):
        apparent_arrhenius_ea((100., 100.), (1., 2.))


def test_production_arrhenius_engine_recovers_independent_ground_truth():
    from can_relax.core.kinetics import KineticsEngine
    temperatures = (100., 120., 140., 160., 180., 200.)
    taus = arrhenius_tau(temperatures, activation_kj_mol=85.)
    fit = KineticsEngine().fit_arrhenius(temperatures, taus)
    assert fit is not None
    assert fit["Ea"] == pytest.approx(85., abs=.1)
    assert fit["R2"] == pytest.approx(1., abs=1e-10)


def test_production_vft_engine_recovers_independent_ground_truth():
    from can_relax.core.kinetics import KineticsEngine
    temperatures = (70., 85., 100., 115., 130., 145., 160.)
    taus = vft_tau(temperatures, a=-4., b_kelvin=500., t0_c=20.)
    fit = KineticsEngine().fit_vft(temperatures, taus)
    assert fit is not None
    assert fit["Params"]["A"] == pytest.approx(-4., abs=.2)
    assert fit["Params"]["B"] == pytest.approx(500., abs=30.)
    assert fit["Params"]["T0"] == pytest.approx(293.15, abs=3.)
    assert fit["R2"] > .999


@pytest.mark.parametrize("key", ["evs_tau_s", "evd_tau_s"])
def test_production_arrhenius_engine_on_published_summary_values(key):
    from can_relax.core.kinetics import KineticsEngine
    ref = LITERATURE_EPOXY_REFERENCE
    fit = KineticsEngine().fit_arrhenius(ref["temperature_c"], ref[key])
    assert fit is not None
    expected = apparent_arrhenius_ea(ref["temperature_c"], ref[key])
    assert fit["Ea"] == pytest.approx(expected, abs=.01)
    assert fit["R2"] > .9


def test_vft_benchmark_rejects_exponential_overflow():
    with pytest.raises(ValueError, match="overflow"):
        vft_tau((20.00001, 100.), t0_c=20.)


def test_arrhenius_benchmark_rejects_exponential_overflow():
    with pytest.raises(ValueError, match="overflow"):
        arrhenius_tau((-273.149, 160.), activation_kj_mol=85.)


@pytest.mark.parametrize(
    "case_name, model, parameters",
    [
        ("single Maxwell", "maxwell", (100.,)),
        ("stretched KWW", "kww", (100., .65)),
        ("two Maxwell modes", "dual_maxwell", (.3, 10., 100.)),
    ],
)
def test_production_relaxation_models_match_independent_analytical_curves(
        case_name, model, parameters):
    import numpy as np
    from can_relax.core.models import Maxwell, SingleKWW, TwoMaxwell
    case = relaxation_case(model, tau_s=100., beta=.65,
                           fast_fraction=.3, fast_tau_s=10.)
    implementation = {"maxwell": Maxwell, "kww": SingleKWW,
                      "dual_maxwell": TwoMaxwell}[model]()
    prediction = implementation.func(np.asarray(case.time_s), *parameters)
    np.testing.assert_allclose(
        prediction, case.normalized_modulus, rtol=1e-12, atol=1e-14,
        err_msg=case_name)


def test_production_single_maxwell_least_squares_recovers_known_tau():
    import numpy as np
    from scipy.optimize import curve_fit
    from can_relax.core.models import Maxwell
    case = relaxation_case("maxwell", tau_s=75.)
    t = np.asarray(case.time_s)
    y = np.asarray(case.normalized_modulus)
    model = Maxwell()
    fit, _ = curve_fit(model.func, t, y, p0=model.get_initial_guess(t, y),
                       bounds=model.get_bounds())
    assert fit[0] == pytest.approx(75., rel=.01)


def test_production_kww_least_squares_recovers_known_tau_and_beta():
    import numpy as np
    from scipy.optimize import curve_fit
    from can_relax.core.models import SingleKWW
    case = relaxation_case("kww", tau_s=120., beta=.6)
    t = np.asarray(case.time_s)
    y = np.asarray(case.normalized_modulus)
    model = SingleKWW()
    fit, _ = curve_fit(model.func, t, y, p0=model.get_initial_guess(t, y),
                       bounds=model.get_bounds())
    assert fit[0] == pytest.approx(120., rel=.01)
    assert fit[1] == pytest.approx(.6, abs=.01)
