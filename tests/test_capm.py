import pytest

from valuation_engine.capm import CapitalStructure, after_tax_cost_of_debt, cost_of_equity_capm, wacc


def test_cost_of_equity_capm():
    re = cost_of_equity_capm(risk_free_rate=0.04, beta=1.2, equity_risk_premium=0.05)
    assert re == pytest.approx(0.10)


def test_after_tax_cost_of_debt():
    assert after_tax_cost_of_debt(0.06, 0.25) == pytest.approx(0.045)


def test_capital_structure_weights():
    cs = CapitalStructure(market_cap=800.0, total_debt=200.0, cash_and_equivalents=50.0)
    assert cs.enterprise_value_weight_equity == pytest.approx(0.8)
    assert cs.enterprise_value_weight_debt == pytest.approx(0.2)
    assert cs.net_debt == pytest.approx(150.0)


def test_net_debt_floors_at_zero_when_cash_exceeds_debt():
    cs = CapitalStructure(market_cap=800.0, total_debt=50.0, cash_and_equivalents=200.0)
    assert cs.net_debt == 0.0


def test_wacc_matches_manual_calculation():
    cs = CapitalStructure(market_cap=800.0, total_debt=200.0)
    result = wacc(cs, cost_of_equity=0.10, pre_tax_cost_of_debt=0.06, tax_rate=0.25)
    expected = 0.8 * 0.10 + 0.2 * 0.06 * 0.75
    assert result == pytest.approx(expected)
