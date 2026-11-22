"""Out-of-window fitted relaxation times must not bias kinetic regressions."""
from vitrifit2.comparison import compare_runs
from vitrifit2.persistence import VitriFitStore


def test_kinetics_excludes_out_of_window_tau_but_keeps_curve_comparison(tmp_path):
    store = VitriFitStore(tmp_path / "store")
    project = store.create_project("Synthetic kinetics")
    sample = store.create_sample(project, "Synthetic sample")
    ids = []
    for index, (temp, tau, flagged) in enumerate([
        (70, 100.0, False), (80, 60.0, False),
        (90, 999999.0, True), (100, 20.0, False),
    ]):
        experiment = store.import_experiment(
            sample, f"synthetic-{index}.csv", f"synthetic-{index}".encode(),
            [{"source_curve_id": str(temp), "temperature_c": temp,
              "time_s": [0.01, 1, 10, 100, 1000, 2000, 3000, 4000],
              "modulus_mpa": [1, .95, .8, .5, .3, .2, .15, .1]}])
        run = store.save_analysis(
            experiment["curve_ids"][0], "Single_KWW",
            "fit:Single_KWW:characteristic", {},
            {"tau_s": tau, "r2": 0.99,
             "flags": ["Tau outside measurement window; review before kinetics."] if flagged else []})
        ids.append(run)
    kinetic = compare_runs(store, ids, "kinetics")
    assert kinetic["excluded_unresolved_run_ids"] == [ids[2]]
    assert len(kinetic["samples"][0]["observations"]) == 3
    assert kinetic["samples"][0]["fit_available"]
    curves = compare_runs(store, ids, "curves")
    assert len(curves["curves"]) == 4
