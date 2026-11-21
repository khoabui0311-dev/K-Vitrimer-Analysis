"""Small deterministic smoke tests for coverage simulation."""
import pytest
from vitrifit2.benchmark_coverage import bootstrap_coverage_study


def test_maxwell_coverage_study_reports_bounded_frequency():
    result = bootstrap_coverage_study(
        model="maxwell", datasets=3, replicates=20,
        noise_fraction=.01, seed=23)
    assert result["datasets"] == 3
    assert result["successful_datasets"] + result["failed_datasets"] == 3
    assert result["parameters"] == ("tau_s",)
    assert all(value is None or 0 <= value <= 1
               for value in result["empirical_coverage"])


def test_kww_coverage_study_is_reproducible():
    options = dict(model="kww", datasets=2, replicates=20,
                   noise_fraction=.01, seed=37)
    assert bootstrap_coverage_study(**options) == bootstrap_coverage_study(**options)


@pytest.mark.parametrize("datasets", [0, 1, 201, True])
def test_invalid_dataset_count_rejected(datasets):
    with pytest.raises(ValueError):
        bootstrap_coverage_study(datasets=datasets)
