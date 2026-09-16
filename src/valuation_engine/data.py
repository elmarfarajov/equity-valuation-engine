"""Fundamental data providers.

The valuation engine never talks to a data source directly — every
calculation module consumes a plain `CompanyFundamentals` record. This keeps
`dcf.py`, `comps.py` and `montecarlo.py` fully unit-testable with
`StaticProvider` and free of network access, while `YFinanceProvider` supplies
real, no-API-key-required market data for live analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CompanyFundamentals:
    ticker: str
    price: float
    shares_outstanding: float
    market_cap: float
    total_debt: float
    cash_and_equivalents: float
    beta: float
    free_cash_flow: float
    """Most recent trailing twelve-month unlevered free cash flow."""
    eps: float
    ebitda_per_share: float
    sales_per_share: float
    pe_ratio: float | None
    ev_ebitda: float | None
    ps_ratio: float | None


class FundamentalsProvider(Protocol):
    def get(self, ticker: str) -> CompanyFundamentals: ...


class StaticProvider:
    """In-memory provider for tests and offline demos."""

    def __init__(self, records: dict[str, CompanyFundamentals]) -> None:
        self._records = records

    def get(self, ticker: str) -> CompanyFundamentals:
        try:
            return self._records[ticker.upper()]
        except KeyError as exc:
            raise KeyError(f"No fundamentals registered for {ticker}") from exc


class YFinanceProvider:
    """Live provider backed by Yahoo Finance via the `yfinance` package.

    `yfinance` is imported lazily inside `get()` so importing this module (and
    the rest of the package) never requires network access or the package to
    be installed for users who only run the offline tests/examples.
    """

    def get(self, ticker: str) -> CompanyFundamentals:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info
        cashflow = stock.cashflow

        operating_cf = _first_available(cashflow, ["Total Cash From Operating Activities", "Operating Cash Flow"])
        capex = _first_available(cashflow, ["Capital Expenditures"])
        free_cash_flow = operating_cf + capex  # yfinance stores capex as a negative number

        shares = info.get("sharesOutstanding") or 0.0
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0

        return CompanyFundamentals(
            ticker=ticker.upper(),
            price=price,
            shares_outstanding=shares,
            market_cap=info.get("marketCap") or 0.0,
            total_debt=info.get("totalDebt") or 0.0,
            cash_and_equivalents=info.get("totalCash") or 0.0,
            beta=info.get("beta") or 1.0,
            free_cash_flow=free_cash_flow,
            eps=info.get("trailingEps") or 0.0,
            ebitda_per_share=(info.get("ebitda") or 0.0) / shares if shares else 0.0,
            sales_per_share=(info.get("totalRevenue") or 0.0) / shares if shares else 0.0,
            pe_ratio=info.get("trailingPE"),
            ev_ebitda=info.get("enterpriseToEbitda"),
            ps_ratio=info.get("priceToSalesTrailing12Months"),
        )


def _first_available(frame, row_names: list[str]) -> float:
    if frame is None:
        return 0.0
    for name in row_names:
        if name in getattr(frame, "index", []):
            return float(frame.loc[name].iloc[0])
    return 0.0
