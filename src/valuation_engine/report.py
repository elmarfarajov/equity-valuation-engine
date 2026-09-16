"""Equity research report generation: matplotlib charts + a self-contained HTML note."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .comps import CompsResult
from .dcf import DCFAssumptions, DCFResult
from .montecarlo import MonteCarloResult


@dataclass(frozen=True)
class ReportInputs:
    ticker: str
    current_price: float
    dcf_assumptions: DCFAssumptions
    dcf_result: DCFResult
    sensitivity: dict[float, dict[float, float]]
    monte_carlo: MonteCarloResult
    comps: CompsResult


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _money(x: float) -> str:
    return f"${x:,.2f}"


def plot_sensitivity_heatmap(sensitivity: dict[float, dict[float, float]], out_path: Path) -> None:
    wacc_values = sorted(sensitivity.keys())
    growth_values = sorted(next(iter(sensitivity.values())).keys())
    grid = np.array([[sensitivity[w][g] for g in growth_values] for w in wacc_values])

    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(grid, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(growth_values)))
    ax.set_xticklabels([_pct(g) for g in growth_values])
    ax.set_yticks(range(len(wacc_values)))
    ax.set_yticklabels([_pct(w) for w in wacc_values])
    ax.set_xlabel("Terminal growth rate")
    ax.set_ylabel("WACC")
    ax.set_title("Intrinsic value sensitivity ($/share)")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            if not np.isnan(grid[i, j]):
                ax.text(j, i, f"{grid[i, j]:.0f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, label="$/share")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_monte_carlo_histogram(mc: MonteCarloResult, current_price: float, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(mc.values, bins=60, color="#2b6cb0", alpha=0.85)
    ax.axvline(current_price, color="black", linestyle="--", label=f"Current price {_money(current_price)}")
    ax.axvline(mc.median, color="#c53030", linestyle="-", label=f"Median fair value {_money(mc.median)}")
    ax.set_xlabel("Simulated intrinsic value ($/share)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Monte Carlo distribution ({len(mc.values):,} trials)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_football_field(
    current_price: float,
    dcf_low: float,
    dcf_high: float,
    comps: CompsResult,
    out_path: Path,
) -> None:
    rows = [("DCF (Monte Carlo 5th-95th pct.)", dcf_low, dcf_high)]
    if comps.implied_value_pe is not None:
        rows.append(("P/E comps (+/-10%)", comps.implied_value_pe * 0.9, comps.implied_value_pe * 1.1))
    if comps.implied_value_ev_ebitda is not None:
        rows.append(("EV/EBITDA comps (+/-10%)", comps.implied_value_ev_ebitda * 0.9, comps.implied_value_ev_ebitda * 1.1))

    fig, ax = plt.subplots(figsize=(6, 0.8 * len(rows) + 1))
    for i, (_, low, high) in enumerate(rows):
        ax.barh(i, high - low, left=low, height=0.5, color="#2b6cb0", alpha=0.8)
    ax.axvline(current_price, color="black", linestyle="--", label=f"Current price {_money(current_price)}")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel("Value per share ($)")
    ax.set_title("Valuation summary - football field")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{ticker} - Equity Research Note</title>
<style>
  body {{ font-family: 'Georgia', 'Times New Roman', serif; max-width: 900px; margin: 40px auto; color: #1a202c; line-height: 1.5; padding: 0 16px; }}
  h1 {{ font-size: 26px; border-bottom: 3px solid #2b6cb0; padding-bottom: 8px; }}
  h2 {{ font-size: 18px; color: #2b6cb0; margin-top: 32px; }}
  .summary {{ display: flex; gap: 24px; flex-wrap: wrap; background: #f7fafc; padding: 16px 20px; border-radius: 8px; }}
  .stat {{ min-width: 140px; }}
  .stat .label {{ font-size: 11px; text-transform: uppercase; color: #718096; letter-spacing: 0.05em; }}
  .stat .value {{ font-size: 20px; font-weight: bold; }}
  .upside {{ color: #276749; }}
  .downside {{ color: #c53030; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 6px 10px; text-align: right; }}
  th {{ background: #edf2f7; }}
  td:first-child, th:first-child {{ text-align: left; }}
  img {{ max-width: 100%; border: 1px solid #e2e8f0; border-radius: 4px; margin: 8px 0; }}
  .disclaimer {{ font-size: 11px; color: #a0aec0; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
</style>
</head>
<body>
  <h1>{ticker} - Equity Research Note</h1>
  <p>Automated valuation generated by the Equity Valuation Engine.</p>

  <div class="summary">
    <div class="stat"><div class="label">Current price</div><div class="value">{current_price}</div></div>
    <div class="stat"><div class="label">DCF fair value</div><div class="value">{dcf_value}</div></div>
    <div class="stat"><div class="label">Upside / downside</div><div class="value {updown_class}">{updown}</div></div>
    <div class="stat"><div class="label">Monte Carlo median</div><div class="value">{mc_median}</div></div>
    <div class="stat"><div class="label">P(fair value &gt; price)</div><div class="value">{prob_above}</div></div>
  </div>

  <h2>1. Discounted Cash Flow</h2>
  <table>
    <tr><th>Year</th>{fcf_year_headers}</tr>
    <tr><td>Projected FCF</td>{fcf_row}</tr>
    <tr><td>Discounted FCF</td>{disc_fcf_row}</tr>
  </table>
  <p>PV of forecast FCF: <b>{pv_forecast}</b> &nbsp;|&nbsp; Terminal value (discounted): <b>{pv_terminal}</b>
     &nbsp;|&nbsp; Enterprise value: <b>{ev}</b> &nbsp;|&nbsp; Equity value: <b>{equity_value}</b></p>
  <p>Assumptions: WACC {wacc}, terminal growth {tg}, net debt {net_debt}.</p>

  <h2>2. Sensitivity - WACC x Terminal Growth</h2>
  <img src="charts/sensitivity.png" alt="Sensitivity heatmap">

  <h2>3. Monte Carlo Simulation</h2>
  <img src="charts/monte_carlo.png" alt="Monte Carlo histogram">
  <p>5th percentile: <b>{mc_p5}</b> &nbsp;|&nbsp; Median: <b>{mc_median}</b> &nbsp;|&nbsp; 95th percentile: <b>{mc_p95}</b></p>

  <h2>4. Comparable Companies</h2>
  <table>
    <tr><th>Peers used</th><td>{peers}</td></tr>
    <tr><th>Median P/E</th><td>{med_pe}</td></tr>
    <tr><th>Median EV/EBITDA</th><td>{med_ev_ebitda}</td></tr>
    <tr><th>Implied value (P/E)</th><td>{implied_pe}</td></tr>
    <tr><th>Implied value (EV/EBITDA)</th><td>{implied_ev}</td></tr>
  </table>

  <h2>5. Valuation Summary</h2>
  <img src="charts/football_field.png" alt="Football field chart">

  <p class="disclaimer">
    Generated automatically for educational and research purposes from public market data and the modeling
    assumptions supplied on the command line. This is not investment advice.
  </p>
</body>
</html>
"""


def render_report(inputs: ReportInputs, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(exist_ok=True)

    plot_sensitivity_heatmap(inputs.sensitivity, charts_dir / "sensitivity.png")
    plot_monte_carlo_histogram(inputs.monte_carlo, inputs.current_price, charts_dir / "monte_carlo.png")
    plot_football_field(
        inputs.current_price,
        inputs.monte_carlo.percentile(5),
        inputs.monte_carlo.percentile(95),
        inputs.comps,
        charts_dir / "football_field.png",
    )

    upside = inputs.dcf_result.intrinsic_value_per_share / inputs.current_price - 1.0
    years = range(1, len(inputs.dcf_result.projected_fcf) + 1)

    html = HTML_TEMPLATE.format(
        ticker=inputs.ticker,
        current_price=_money(inputs.current_price),
        dcf_value=_money(inputs.dcf_result.intrinsic_value_per_share),
        updown=_pct(upside),
        updown_class="upside" if upside >= 0 else "downside",
        mc_median=_money(inputs.monte_carlo.median),
        prob_above=_pct(inputs.monte_carlo.probability_above(inputs.current_price)),
        fcf_year_headers="".join(f"<th>Y{y}</th>" for y in years),
        fcf_row="".join(f"<td>{_money(v)}</td>" for v in inputs.dcf_result.projected_fcf),
        disc_fcf_row="".join(f"<td>{_money(v)}</td>" for v in inputs.dcf_result.discounted_fcf),
        pv_forecast=_money(inputs.dcf_result.pv_of_forecast_fcf),
        pv_terminal=_money(inputs.dcf_result.discounted_terminal_value),
        ev=_money(inputs.dcf_result.enterprise_value),
        equity_value=_money(inputs.dcf_result.equity_value),
        wacc=_pct(inputs.dcf_assumptions.wacc),
        tg=_pct(inputs.dcf_assumptions.terminal_growth),
        net_debt=_money(inputs.dcf_assumptions.net_debt),
        mc_p5=_money(inputs.monte_carlo.percentile(5)),
        mc_p95=_money(inputs.monte_carlo.percentile(95)),
        peers=", ".join(inputs.comps.peers_used),
        med_pe=f"{inputs.comps.median_pe:.1f}x" if inputs.comps.median_pe else "n/a",
        med_ev_ebitda=f"{inputs.comps.median_ev_ebitda:.1f}x" if inputs.comps.median_ev_ebitda else "n/a",
        implied_pe=_money(inputs.comps.implied_value_pe) if inputs.comps.implied_value_pe else "n/a",
        implied_ev=_money(inputs.comps.implied_value_ev_ebitda) if inputs.comps.implied_value_ev_ebitda else "n/a",
    )

    report_path = output_dir / f"{inputs.ticker}_equity_research_note.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path
