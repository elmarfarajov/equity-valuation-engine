"""Comparable-company (trading multiples) valuation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class PeerMultiples:
    ticker: str
    pe_ratio: float | None
    ev_ebitda: float | None
    ps_ratio: float | None


@dataclass(frozen=True)
class CompsResult:
    peers_used: list[str]
    median_pe: float | None
    median_ev_ebitda: float | None
    median_ps: float | None
    implied_value_pe: float | None
    implied_value_ev_ebitda: float | None
    implied_value_ps: float | None

    @property
    def implied_values(self) -> list[float]:
        return [v for v in (self.implied_value_pe, self.implied_value_ev_ebitda, self.implied_value_ps) if v is not None]


def _median_or_none(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return median(clean) if clean else None


def comps_valuation(
    peers: list[PeerMultiples],
    target_eps: float,
    target_ebitda_per_share: float,
    target_sales_per_share: float,
    net_debt_per_share: float = 0.0,
) -> CompsResult:
    """Apply peer-median multiples to the target's own fundamentals.

    P/E and P/S multiples are equity multiples and translate directly into an
    implied equity value per share. EV/EBITDA is an enterprise-value multiple,
    so the implied enterprise value per share is first computed and then
    net debt per share is subtracted to arrive at an implied equity value.
    """
    if not peers:
        raise ValueError("At least one peer is required for a comps analysis")

    median_pe = _median_or_none([p.pe_ratio for p in peers])
    median_ev_ebitda = _median_or_none([p.ev_ebitda for p in peers])
    median_ps = _median_or_none([p.ps_ratio for p in peers])

    implied_value_pe = median_pe * target_eps if median_pe is not None else None
    implied_value_ps = median_ps * target_sales_per_share if median_ps is not None else None

    implied_value_ev_ebitda = None
    if median_ev_ebitda is not None:
        implied_ev_per_share = median_ev_ebitda * target_ebitda_per_share
        implied_value_ev_ebitda = implied_ev_per_share - net_debt_per_share

    return CompsResult(
        peers_used=[p.ticker for p in peers],
        median_pe=median_pe,
        median_ev_ebitda=median_ev_ebitda,
        median_ps=median_ps,
        implied_value_pe=implied_value_pe,
        implied_value_ev_ebitda=implied_value_ev_ebitda,
        implied_value_ps=implied_value_ps,
    )
