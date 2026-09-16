"""Command-line entry point: `valuation-engine TICKER --peers PEER1 PEER2 ...`"""

from __future__ import annotations

import argparse
from pathlib import Path

from .capm import CapitalStructure, cost_of_equity_capm
from .capm import wacc as compute_wacc
from .comps import PeerMultiples, comps_valuation
from .data import CompanyFundamentals, FundamentalsProvider, YFinanceProvider
from .dcf import DCFAssumptions, run_dcf
from .montecarlo import MonteCarloConfig, run_monte_carlo
from .report import ReportInputs, render_report
from .sensitivity import sensitivity_table


def build_dcf_assumptions(
    fundamentals: CompanyFundamentals,
    growth_rates: list[float],
    terminal_growth: float,
    risk_free_rate: float,
    equity_risk_premium: float,
    pre_tax_cost_of_debt: float,
    tax_rate: float,
) -> DCFAssumptions:
    capital_structure = CapitalStructure(
        market_cap=fundamentals.market_cap,
        total_debt=fundamentals.total_debt,
        cash_and_equivalents=fundamentals.cash_and_equivalents,
    )
    cost_of_equity = cost_of_equity_capm(risk_free_rate, fundamentals.beta, equity_risk_premium)
    discount_rate = compute_wacc(capital_structure, cost_of_equity, pre_tax_cost_of_debt, tax_rate)

    return DCFAssumptions(
        base_fcf=fundamentals.free_cash_flow,
        growth_rates=growth_rates,
        wacc=discount_rate,
        terminal_growth=terminal_growth,
        net_debt=capital_structure.net_debt,
        shares_outstanding=fundamentals.shares_outstanding,
    )


def analyze(
    ticker: str,
    peer_tickers: list[str],
    growth_rates: list[float],
    terminal_growth: float,
    risk_free_rate: float,
    equity_risk_premium: float,
    pre_tax_cost_of_debt: float,
    tax_rate: float,
    output_dir: Path,
    provider: FundamentalsProvider,
) -> Path:
    target = provider.get(ticker)
    assumptions = build_dcf_assumptions(
        target, growth_rates, terminal_growth, risk_free_rate, equity_risk_premium, pre_tax_cost_of_debt, tax_rate
    )
    dcf_result = run_dcf(assumptions)

    wacc_range = sorted({round(assumptions.wacc + delta, 4) for delta in (-0.02, -0.01, 0.0, 0.01, 0.02)})
    growth_range = sorted({round(terminal_growth + delta, 4) for delta in (-0.01, -0.005, 0.0, 0.005, 0.01)})
    sensitivity = sensitivity_table(assumptions, wacc_range, growth_range)

    mc_result = run_monte_carlo(assumptions, MonteCarloConfig())

    peers = []
    for peer_ticker in peer_tickers:
        peer_fundamentals = provider.get(peer_ticker)
        peers.append(
            PeerMultiples(
                ticker=peer_ticker.upper(),
                pe_ratio=peer_fundamentals.pe_ratio,
                ev_ebitda=peer_fundamentals.ev_ebitda,
                ps_ratio=peer_fundamentals.ps_ratio,
            )
        )

    comps_result = comps_valuation(
        peers,
        target_eps=target.eps,
        target_ebitda_per_share=target.ebitda_per_share,
        target_sales_per_share=target.sales_per_share,
        net_debt_per_share=assumptions.net_debt / assumptions.shares_outstanding,
    )

    report_inputs = ReportInputs(
        ticker=target.ticker,
        current_price=target.price,
        dcf_assumptions=assumptions,
        dcf_result=dcf_result,
        sensitivity=sensitivity,
        monte_carlo=mc_result,
        comps=comps_result,
    )
    return render_report(report_inputs, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated DCF equity valuation with Monte Carlo risk analysis and comps."
    )
    parser.add_argument("ticker", help="Target company ticker, e.g. AAPL")
    parser.add_argument("--peers", nargs="*", default=[], help="Peer tickers for the comparable-company analysis")
    parser.add_argument(
        "--growth",
        nargs="+",
        type=float,
        default=[0.10, 0.08, 0.06, 0.05, 0.04],
        help="Explicit forecast-period FCF growth rates, one per year",
    )
    parser.add_argument("--terminal-growth", type=float, default=0.025)
    parser.add_argument("--risk-free-rate", type=float, default=0.042)
    parser.add_argument("--equity-risk-premium", type=float, default=0.05)
    parser.add_argument("--cost-of-debt", type=float, default=0.055)
    parser.add_argument("--tax-rate", type=float, default=0.21)
    parser.add_argument("--output", type=Path, default=Path("reports"))
    args = parser.parse_args()

    report_path = analyze(
        ticker=args.ticker,
        peer_tickers=args.peers,
        growth_rates=args.growth,
        terminal_growth=args.terminal_growth,
        risk_free_rate=args.risk_free_rate,
        equity_risk_premium=args.equity_risk_premium,
        pre_tax_cost_of_debt=args.cost_of_debt,
        tax_rate=args.tax_rate,
        output_dir=args.output / args.ticker.upper(),
        provider=YFinanceProvider(),
    )
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
