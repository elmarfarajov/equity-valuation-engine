"""Discounted cash flow (DCF) valuation: explicit forecast + Gordon Growth terminal value."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DCFAssumptions:
    base_fcf: float
    """Most recent trailing unlevered free cash flow, used as the base for projections."""

    growth_rates: list[float]
    """Explicit forecast-period FCF growth rates, one entry per forecast year."""

    wacc: float
    """Discount rate applied to forecast cash flows and the terminal value."""

    terminal_growth: float
    """Perpetuity growth rate applied to cash flows after the explicit forecast window."""

    net_debt: float
    """Total debt minus cash and equivalents, used to bridge enterprise value to equity value."""

    shares_outstanding: float

    def __post_init__(self) -> None:
        if self.wacc <= self.terminal_growth:
            raise ValueError("WACC must exceed the terminal growth rate for the perpetuity to converge")
        if self.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")
        if not self.growth_rates:
            raise ValueError("growth_rates must contain at least one forecast year")


@dataclass(frozen=True)
class DCFResult:
    projected_fcf: list[float]
    discounted_fcf: list[float]
    terminal_value: float
    discounted_terminal_value: float
    enterprise_value: float
    equity_value: float
    intrinsic_value_per_share: float

    @property
    def pv_of_forecast_fcf(self) -> float:
        return sum(self.discounted_fcf)


def project_fcf(base_fcf: float, growth_rates: list[float]) -> list[float]:
    """Compound the base FCF forward year over year using the given growth rates."""
    projected = []
    fcf = base_fcf
    for g in growth_rates:
        fcf = fcf * (1.0 + g)
        projected.append(fcf)
    return projected


def discount_factors(rate: float, periods: int) -> list[float]:
    """Present-value factors 1 / (1 + rate)^t for t = 1..periods."""
    return [1.0 / ((1.0 + rate) ** t) for t in range(1, periods + 1)]


def gordon_growth_terminal_value(final_year_fcf: float, wacc: float, terminal_growth: float) -> float:
    """TV = FCF_(n+1) / (WACC - g), with FCF_(n+1) = final_year_fcf * (1 + g)."""
    return final_year_fcf * (1.0 + terminal_growth) / (wacc - terminal_growth)


def run_dcf(assumptions: DCFAssumptions) -> DCFResult:
    projected = project_fcf(assumptions.base_fcf, assumptions.growth_rates)
    factors = discount_factors(assumptions.wacc, len(projected))
    discounted = [fcf * f for fcf, f in zip(projected, factors)]

    terminal_value = gordon_growth_terminal_value(projected[-1], assumptions.wacc, assumptions.terminal_growth)
    discounted_terminal_value = terminal_value * factors[-1]

    enterprise_value = sum(discounted) + discounted_terminal_value
    equity_value = enterprise_value - assumptions.net_debt
    intrinsic_value_per_share = equity_value / assumptions.shares_outstanding

    return DCFResult(
        projected_fcf=projected,
        discounted_fcf=discounted,
        terminal_value=terminal_value,
        discounted_terminal_value=discounted_terminal_value,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        intrinsic_value_per_share=intrinsic_value_per_share,
    )
