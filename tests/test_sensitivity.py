import math

import pytest

from valuation_engine.dcf import DCFAssumptions, run_dcf
from valuation_engine.sensitivity import sensitivity_table

BASE = DCFAssumptions(
    base_fcf=100.0,
    growth_rates=[0.08, 0.06],
    wacc=0.09,
    terminal_growth=0.02,
    net_debt=0.0,
    shares_outstanding=10.0,
)


def test_sensitivity_table_matches_run_dcf_at_the_base_case():
    table = sensitivity_table(BASE, wacc_range=[0.09], terminal_growth_range=[0.02])
    assert table[0.09][0.02] == pytest.approx(run_dcf(BASE).intrinsic_value_per_share)


def test_sensitivity_table_flags_non_convergent_pairs_as_nan():
    table = sensitivity_table(BASE, wacc_range=[0.02], terminal_growth_range=[0.05])
    assert math.isnan(table[0.02][0.05])


def test_higher_wacc_lowers_intrinsic_value():
    table = sensitivity_table(BASE, wacc_range=[0.08, 0.10], terminal_growth_range=[0.02])
    assert table[0.10][0.02] < table[0.08][0.02]


def test_higher_terminal_growth_raises_intrinsic_value():
    table = sensitivity_table(BASE, wacc_range=[0.09], terminal_growth_range=[0.01, 0.03])
    assert table[0.09][0.03] > table[0.09][0.01]
