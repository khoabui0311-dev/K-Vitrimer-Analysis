"""Foundation regressions for persistent, non-destructive analysis state."""
import pytest
from vitrifit2.persistence import VitriFitStore


@pytest.fixture
def store(tmp_path):
    return VitriFitStore(tmp_path / "research")


@pytest.fixture
def imported(store):
    project = store.create_project("LCE-IPN")
    sample = store.create_sample(project, "VUGT 13/11")
    exp = store.import_experiment(sample, "raw.csv", b"original-instrument-file",
        [{"source_curve_id": "curve-70", "temperature_c": 70,
          "time_s": [0.01, 1, 2, 3, 4, 5],
          "modulus_mpa": [1, .9, .8, .7, .6, .5]},
         {"source_curve_id": "curve-100", "temperature_c": 100,
          "time_s": [0.01, 1, 2, 3, 4, 5],
          "modulus_mpa": [2, 1.9, 1.8, 1.7, 1.6, 1.5]}],
        {"strain_pct": .5})
    return store, exp


def test_original_file_persisted_and_verified(imported):
    store, exp = imported
    assert store.get_original_file(exp["experiment_id"]) == b"original-instrument-file"
    reopened = VitriFitStore(store.root)
    assert reopened.get_original_file(exp["experiment_id"]) == b"original-instrument-file"


def test_individual_trimming_and_undo_redo_survive_restart(imported):
    store, exp = imported
    first, second = exp["curve_ids"]
    pristine = store.get_curve(second)
    initial = store.get_curve(first)
    a = store.apply_region(first, "keep", 1, 4)
    assert store.get_curve(first)["active_revision_id"] == a
    assert store.get_curve(first)["mask"] == [False, True, True, True, True, False]
    assert store.get_curve(second)["mask"] == pristine["mask"]
    assert store.get_curve(first)["time_s"] == initial["time_s"]
    store.undo(first)
    assert store.get_curve(first)["mask"] == [True] * 6
    reopened = VitriFitStore(store.root)
    assert reopened.get_curve(first)["can_redo"]
    assert reopened.redo(first) == a
    assert reopened.get_curve(first)["mask"] == [False, True, True, True, True, False]


def test_exclude_region_cumulative_and_branching(imported):
    store, exp = imported
    curve_id = exp["curve_ids"][0]
    store.apply_region(curve_id, "exclude", 1, 2)
    assert store.get_curve(curve_id)["mask"] == [True, False, False, True, True, True]
    store.apply_region(curve_id, "exclude", 4, 5)
    assert store.get_curve(curve_id)["mask"] == [True, False, False, True, False, False]
    store.undo(curve_id)
    assert store.get_curve(curve_id)["can_redo"]
    store.apply_region(curve_id, "keep", 0, 3)
    assert store.get_curve(curve_id)["mask"] == [True, False, False, True, False, False]
    assert not store.get_curve(curve_id)["can_redo"]


def test_stale_saved_results_recoverable(imported):
    store, exp = imported
    cid = exp["curve_ids"][0]
    run = store.save_analysis(cid, "KWW", "KWW_tau", {"beta_bounds": [.1, 1]}, {"tau_s": 100})
    assert store.get_analysis(run)["is_current"]
    store.apply_region(cid, "keep", 1, 4)
    old = store.get_analysis(run)
    assert old["results"]["tau_s"] == 100
    assert not old["is_current"]
    store.undo(cid)
    assert store.get_analysis(run)["is_current"]


def test_cross_sample_comparison_and_figures(imported):
    store, exp = imported
    project = store.create_project("PEDOT PSS")
    sample = store.create_sample(project, "VUEG 70")
    new_exp = store.import_experiment(sample, "another.csv", b"another-sample",
        [{"source_curve_id": "curve-100", "temperature_c": 100,
          "time_s": [0.01, 1, 3], "modulus_mpa": [1, .7, .4]}])
    a = store.save_analysis(exp["curve_ids"][1], "KWW", "KWW_tau", {}, {"tau_s": 100})
    b = store.save_analysis(new_exp["curve_ids"][0], "KWW", "KWW_tau", {}, {"tau_s": 30})
    comparison = store.save_comparison("100C cross-sample", "fixed_temperature", [a, b],
                                       {"temperature_c": 100, "interpolation": False})
    preset = store.save_figure_preset("ACS/RSC single", {"pub_preset": "ACS/RSC Single-Column (85 x 75 mm)",
                                               "pub_relfont_family": "Arial", "pub_rel_lw": 1.5})
    figure = store.save_figure("Figure 3", [a, b], preset, {"panels": ["a", "b"]},
                                {"pub_rel_lw": 2.0})
    reopened = VitriFitStore(store.root)
    assert reopened.get_comparison(comparison)["run_ids"] == [a, b]
    assert reopened.get_figure(figure)["overrides"]["pub_rel_lw"] == 2.0
    assert reopened.get_figure_preset(preset)["settings"]["pub_rel_lw"] == 1.5


def test_bad_region_does_not_change_head(imported):
    store, exp = imported
    cid = exp["curve_ids"][0]
    head = store.get_curve(cid)["active_revision_id"]
    with pytest.raises(ValueError):
        store.apply_region(cid, "keep", 5, 5)
    assert store.get_curve(cid)["active_revision_id"] == head


def test_invalid_curve_rejected_without_experiment_row(store):
    sample = store.create_sample(store.create_project("LCE"), "LCE2")
    with pytest.raises(ValueError):
        store.import_experiment(sample, "bad.csv", b"bad",
            [{"source_curve_id": "bad", "temperature_c": 70,
              "time_s": [0, 1], "modulus_mpa": [1]}])
