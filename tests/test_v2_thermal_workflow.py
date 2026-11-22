"""Scientific and persistence regressions for DMA and DSC CSV workflows."""
import pytest

from vitrifit2.persistence import VitriFitStore
from vitrifit2.sample_profile import create_measurement, create_specimen
from vitrifit2.thermal_analysis import analyze_dma_ramp, analyze_dsc_trace
from vitrifit2.thermal_workflow import (
    import_thermal_csv, get_thermal_analysis, list_thermal_analyses,
)


def test_dma_observed_interior_tan_delta_peak():
    result = analyze_dma_ramp(
        [20, 30, 40, 50, 60], [1000, 900, 700, 500, 400],
        [100, 180, 350, 100, 40], modulus_unit="MPa")
    assert result["tan_delta_peak_temperature_c"] == 40
    assert result["storage_modulus_pa"][0] == 1e9
    assert result["tan_delta"][2] == pytest.approx(.5)


def test_dma_endpoint_peak_is_not_claimed():
    result = analyze_dma_ramp([20, 30, 40, 50], [100, 100, 100, 100],
                              [10, 20, 30, 40])
    assert result["tan_delta_peak_temperature_c"] is None


def test_dsc_does_not_invent_tg():
    result = analyze_dsc_trace(
        [20, 30, 40, 50, 60], [1, 1.1, 1.8, 2.1, 2.2],
        heating_rate_c_min=5)
    assert result["t_g_onset_c"] is None
    assert result["enthalpy_j_g"] is None
    with pytest.raises(ValueError):
        analyze_dsc_trace([20, 30, 25, 40], [1, 2, 3, 4])


def test_dma_dsc_persist_reopen_and_reject_invalid(tmp_path):
    root = tmp_path / "data"
    store = VitriFitStore(root)
    sample = store.create_sample(store.create_project("P"), "VUGT")
    specimen = create_specimen(store, sample, "film")
    dma = create_measurement(store, specimen, "DMA", "temperature_ramp")
    dsc = create_measurement(store, specimen, "DSC", "calorimetry")
    dma_raw = b"T,Ep,Epp\n20,1000,100\n30,900,180\n40,700,350\n50,500,100\n60,400,40\n"
    dma_id = import_thermal_csv(
        store, dma, "dma.csv", dma_raw, method="temperature_ramp",
        columns={"temperature_c": "T", "storage_modulus": "Ep",
                 "loss_modulus": "Epp"}, modulus_unit="MPa")
    dsc_raw = b"T,heat\n20,1\n30,1.1\n40,1.8\n50,2.1\n60,2.2\n"
    dsc_id = import_thermal_csv(
        store, dsc, "dsc.csv", dsc_raw, method="calorimetry",
        columns={"temperature_c": "T", "heat_flow": "heat"},
        heat_flow_unit="mW", heating_rate_c_min=5)
    reopened = VitriFitStore(root)
    assert get_thermal_analysis(reopened, dma_id)["results"]["tan_delta_peak_temperature_c"] == 40
    assert get_thermal_analysis(reopened, dsc_id)["results"]["t_g_onset_c"] is None
    assert len(list_thermal_analyses(reopened, dma)) == 1
    with pytest.raises(ValueError):
        import_thermal_csv(
            store, dsc, "wrong.csv", dma_raw, method="temperature_ramp",
            columns={"temperature_c": "T", "storage_modulus": "Ep",
                     "loss_modulus": "Epp"})
