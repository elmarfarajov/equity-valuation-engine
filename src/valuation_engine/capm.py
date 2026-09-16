"""Cost of capital: CAPM cost of equity and weighted-average cost of capital (WACC)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalStructure:
    """A company's financing mix, used to weight the cost of equity and debt in WACC."""

    market_cap: float
    total_debt: float
    cash_and_equivalents: float = 0.0

    @property
    def net_debt(self) -> float:
        return max(self.total_debt - self.cash_and_equivalents, 0.0)

    @property
    def enterprise_value_weight_equity(self) -> float:
        total = self.market_cap + self.total_debt
        if total <= 0:
            raise ValueError("Capital structure has non-positive total value")
        return self.market_cap / total

    @property
    def enterprise_value_weight_debt(self) -> float:
        return 1.0 - self.enterprise_value_weight_equity


def cost_of_equity_capm(risk_free_rate: float, beta: float, equity_risk_premium: float) -> float:
    """CAPM: Re = Rf + beta * ERP."""
    return risk_free_rate + beta * equity_risk_premium


def after_tax_cost_of_debt(pre_tax_cost_of_debt: float, tax_rate: float) -> float:
    """Interest is tax-deductible, so the effective cost of debt is Rd * (1 - Tc)."""
    return pre_tax_cost_of_debt * (1.0 - tax_rate)


def wacc(
    capital_structure: CapitalStructure,
    cost_of_equity: float,
    pre_tax_cost_of_debt: float,
    tax_rate: float,
) -> float:
    """WACC = (E/V) * Re + (D/V) * Rd * (1 - Tc)."""
    we = capital_structure.enterprise_value_weight_equity
    wd = capital_structure.enterprise_value_weight_debt
    rd_after_tax = after_tax_cost_of_debt(pre_tax_cost_of_debt, tax_rate)
    return we * cost_of_equity + wd * rd_after_tax
