import pytest

from valuation_engine.comps import PeerMultiples, comps_valuation


def test_comps_valuation_uses_median_multiples():
    peers = [
        PeerMultiples(ticker="A", pe_ratio=20.0, ev_ebitda=12.0, ps_ratio=4.0),
        PeerMultiples(ticker="B", pe_ratio=24.0, ev_ebitda=14.0, ps_ratio=5.0),
        PeerMultiples(ticker="C", pe_ratio=22.0, ev_ebitda=13.0, ps_ratio=4.5),
    ]
    result = comps_valuation(
        peers,
        target_eps=5.0,
        target_ebitda_per_share=8.0,
        target_sales_per_share=15.0,
        net_debt_per_share=10.0,
    )

    assert result.peers_used == ["A", "B", "C"]
    assert result.median_pe == pytest.approx(22.0)
    assert result.implied_value_pe == pytest.approx(110.0)
    assert result.median_ev_ebitda == pytest.approx(13.0)
    # EV/EBITDA gives an enterprise-value multiple; net debt per share bridges it to equity value.
    assert result.implied_value_ev_ebitda == pytest.approx(13.0 * 8.0 - 10.0)
    assert result.median_ps == pytest.approx(4.5)
    assert result.implied_value_ps == pytest.approx(4.5 * 15.0)


def test_comps_valuation_tolerates_missing_multiples():
    peers = [
        PeerMultiples(ticker="A", pe_ratio=20.0, ev_ebitda=None, ps_ratio=4.0),
        PeerMultiples(ticker="B", pe_ratio=24.0, ev_ebitda=None, ps_ratio=5.0),
    ]
    result = comps_valuation(peers, target_eps=5.0, target_ebitda_per_share=8.0, target_sales_per_share=15.0)
    assert result.median_ev_ebitda is None
    assert result.implied_value_ev_ebitda is None
    assert result.median_pe == pytest.approx(22.0)


def test_comps_valuation_requires_at_least_one_peer():
    with pytest.raises(ValueError):
        comps_valuation([], target_eps=1.0, target_ebitda_per_share=1.0, target_sales_per_share=1.0)
