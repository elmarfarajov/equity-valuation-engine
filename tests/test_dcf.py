import pytest

from valuation_engine.dcf import (
    DCFAssumptions,
    discount_factors,
    gordon_growth_terminal_value,
    project_fcf,
    run_dcf,
)


def test_project_fcf_compounds_growth():
    fcf = project_fcf(base_fcf=100.0, growth_rates=[0.10, 0.10])
    assert fcf[0] == pytest.approx(110.0)
    assert fcf[1] == pytest.approx(121.0)


def test_discount_factors():
    factors = discount_factors(rate=0.10, periods=2)
    assert factors[0] == pytest.approx(1 / 1.10)
    assert factors[1] == pytest.approx(1 / 1.10**2)


def test_gordon_growth_terminal_value():
    tv = gordon_growth_terminal_value(final_year_fcf=100.0, wacc=0.10, terminal_growth=0.02)
    assert tv == pytest.approx(100.0 * 1.02 / 0.08)


def test_run_dcf_end_to_end_matches_manual_calculation():
    assumptions = DCFAssumptions(
        base_fcf=100.0,
        growth_rates=[0.10, 0.05],
        wacc=0.10,
        terminal_growth=0.02,
        net_debt=200.0,
        shares_outstanding=50.0,
    )
    result = run_dcf(assumptions)

    fcf1 = 110.0
    fcf2 = 110.0 * 1.05
    pv1 = fcf1 / 1.10
    pv2 = fcf2 / 1.10**2
    tv = fcf2 * 1.02 / (0.10 - 0.02)
    pv_tv = tv / 1.10**2
    expected_ev = pv1 + pv2 + pv_tv
    expected_equity = expected_ev - 200.0
    expected_per_share = expected_equity / 50.0

    assert result.enterprise_value == pytest.approx(expected_ev)
    assert result.equity_value == pytest.approx(expected_equity)
    assert result.intrinsic_value_per_share == pytest.approx(expected_per_share)


def test_wacc_must_exceed_terminal_growth():
    with pytest.raises(ValueError):
        DCFAssumptions(
            base_fcf=100.0,
            growth_rates=[0.05],
            wacc=0.03,
            terminal_growth=0.05,
            net_debt=0.0,
            shares_outstanding=10.0,
        )


def test_shares_outstanding_must_be_positive():
    with pytest.raises(ValueError):
        DCFAssumptions(
            base_fcf=100.0,
            growth_rates=[0.05],
            wacc=0.10,
            terminal_growth=0.02,
            net_debt=0.0,
            shares_outstanding=0.0,
        )


def test_growth_rates_must_not_be_empty():
    with pytest.raises(ValueError):
        DCFAssumptions(
            base_fcf=100.0,
            growth_rates=[],
            wacc=0.10,
            terminal_growth=0.02,
            net_debt=0.0,
            shares_outstanding=10.0,
        )
