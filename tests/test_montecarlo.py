import pytest

from valuation_engine.dcf import DCFAssumptions, run_dcf
from valuation_engine.montecarlo import MonteCarloConfig, run_monte_carlo

BASE = DCFAssumptions(
    base_fcf=100.0,
    growth_rates=[0.08, 0.06, 0.05],
    wacc=0.09,
    terminal_growth=0.025,
    net_debt=50.0,
    shares_outstanding=20.0,
)


def test_monte_carlo_is_centered_near_deterministic_dcf():
    deterministic = run_dcf(BASE).intrinsic_value_per_share
    mc = run_monte_carlo(BASE, MonteCarloConfig(n_trials=2000, random_seed=1))
    assert mc.median == pytest.approx(deterministic, rel=0.15)


def test_monte_carlo_is_reproducible_with_a_fixed_seed():
    mc1 = run_monte_carlo(BASE, MonteCarloConfig(n_trials=500, random_seed=7))
    mc2 = run_monte_carlo(BASE, MonteCarloConfig(n_trials=500, random_seed=7))
    assert mc1.values.tolist() == mc2.values.tolist()


def test_probability_above_is_a_valid_probability():
    mc = run_monte_carlo(BASE, MonteCarloConfig(n_trials=500, random_seed=3))
    prob = mc.probability_above(BASE.base_fcf)
    assert 0.0 <= prob <= 1.0


def test_percentiles_are_ordered():
    mc = run_monte_carlo(BASE, MonteCarloConfig(n_trials=1000, random_seed=5))
    assert mc.percentile(5) <= mc.percentile(50) <= mc.percentile(95)
