import numpy as np
import pytest

from validation.experimental_prony import independent_fit


@pytest.mark.parametrize('reference', [0., 2.])
def test_independent_audit_solver_recovers_known_times(reference):
    t = reference + np.geomspace(.001, 1200, 150)
    absolute = 1.2*np.exp(-t/4) + .6*np.exp(-t/68)
    solutions = independent_fit(t, absolute/absolute[0])
    assert len(solutions) == 12
    assert solutions[0]['tau_fast_s'] == pytest.approx(4., rel=1e-5)
    assert solutions[0]['tau_slow_s'] == pytest.approx(68., rel=1e-5)
