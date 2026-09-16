"""Monte Carlo simulation of DCF intrinsic value under assumption uncertainty.

A single DCF run produces one point estimate, which hides how sensitive that
estimate is to the analyst's assumptions. This module re-runs the DCF
thousands of times with randomly perturbed growth, WACC and terminal-growth
inputs to produce a distribution of plausible fair values instead of a
single number.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .dcf import DCFAssumptions, run_dcf


@dataclass(frozen=True)
class MonteCarloConfig:
    n_trials: int = 5_000
    growth_std: float = 0.03
    """Std dev of the normal shock applied independently to each forecast-year growth rate."""
    wacc_std: float = 0.01
    terminal_growth_std: float = 0.005
    random_seed: int | None = 42


@dataclass(frozen=True)
class MonteCarloResult:
    values: np.ndarray

    def percentile(self, q: float) -> float:
        return float(np.percentile(self.values, q))

    @property
    def mean(self) -> float:
        return float(np.mean(self.values))

    @property
    def median(self) -> float:
        return self.percentile(50)

    def probability_above(self, price: float) -> float:
        """Share of simulated fair values that exceed a given price (e.g. the market price)."""
        return float(np.mean(self.values > price))


def run_monte_carlo(base: DCFAssumptions, config: MonteCarloConfig = MonteCarloConfig()) -> MonteCarloResult:
    rng = np.random.default_rng(config.random_seed)
    n_years = len(base.growth_rates)

    growth_shocks = rng.normal(0.0, config.growth_std, size=(config.n_trials, n_years))
    wacc_draws = rng.normal(base.wacc, config.wacc_std, size=config.n_trials)
    terminal_draws = rng.normal(base.terminal_growth, config.terminal_growth_std, size=config.n_trials)

    values = np.empty(config.n_trials)
    for i in range(config.n_trials):
        w = max(float(wacc_draws[i]), 0.001)
        g = float(terminal_draws[i])
        if g >= w:
            g = w - 0.005  # keep the perpetuity convergent for this draw
        scenario_growth = [base.growth_rates[y] + float(growth_shocks[i, y]) for y in range(n_years)]
        scenario = replace(base, growth_rates=scenario_growth, wacc=w, terminal_growth=g)
        values[i] = run_dcf(scenario).intrinsic_value_per_share

    return MonteCarloResult(values=values)
