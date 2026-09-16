# Equity Valuation Engine

![CI](https://github.com/elmarfarajov/equity-valuation-engine/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An automated DCF equity valuation tool that goes beyond a single "fair value"
number: it estimates the cost of capital from first principles (CAPM/WACC),
builds a discounted cash flow model with a Gordon Growth terminal value,
stress-tests it with a 5,000-trial Monte Carlo simulation, cross-checks it
against comparable-company trading multiples, and renders the result as a
one-page equity research note.

**[View a sample report →](examples/sample_report.html)** ·
**[Read the methodology →](docs/methodology.md)**

## Why this exists

This is a follow-on to [`Portfolio-analyzer`](https://github.com/elmarfarajov/Portfolio-analyzer),
which focused on risk metrics for an existing portfolio (Sharpe/Sortino,
drawdown, bond YTM). This project asks a different question — *what should a
single stock be worth in the first place?* — and answers it the way a sell-side
equity research note would: a DCF built on an explicit cost-of-capital model,
a Monte Carlo view of how much that estimate should be trusted, and a
comparable-company cross-check, all wired end-to-end from live market data to
a rendered report.

## What it does

1. **Cost of capital from first principles** — CAPM cost of equity
   (`Rf + β·ERP`) blended with the after-tax cost of debt into WACC, rather
   than taking a discount rate as a given input.
2. **DCF valuation** — explicit multi-year FCF forecast + Gordon Growth
   terminal value, bridged from enterprise value to equity value per share.
3. **Sensitivity analysis** — a WACC × terminal-growth grid, since both are
   estimates, not facts.
4. **Monte Carlo simulation** — 5,000 re-runs of the DCF with randomized
   growth, WACC and terminal-growth assumptions, producing a distribution of
   intrinsic value (median, 5th/95th percentile, and P(fair value > price))
   instead of one number.
5. **Comparable-company analysis** — median peer P/E, EV/EBITDA and P/S
   multiples applied to the target's own fundamentals, correctly bridging
   the EV/EBITDA multiple to an equity value by netting out debt per share.
6. **Automated reporting** — a self-contained HTML equity research note with
   a sensitivity heatmap, a Monte Carlo histogram, and a "football field"
   valuation-summary chart, all generated with matplotlib.

## Architecture

```
equity-valuation-engine/
├── src/valuation_engine/
│   ├── data.py          # FundamentalsProvider protocol: YFinanceProvider (live) / StaticProvider (tests)
│   ├── capm.py          # Cost of equity (CAPM) and WACC
│   ├── dcf.py           # FCF projection, discounting, Gordon Growth terminal value
│   ├── sensitivity.py   # WACC x terminal-growth sensitivity grid
│   ├── montecarlo.py    # Monte Carlo simulation over assumption uncertainty
│   ├── comps.py         # Comparable-company trading-multiples valuation
│   ├── report.py        # Chart generation + HTML report rendering
│   └── cli.py           # `valuation-engine TICKER --peers ...` entry point
├── tests/               # pytest unit tests — pure functions, no network calls
├── docs/methodology.md  # Formula derivations behind every module
├── examples/            # A rendered sample report (illustrative data)
└── .github/workflows/   # CI: tests run on every push across Python 3.10-3.12
```

Every calculation module (`dcf`, `comps`, `montecarlo`, `sensitivity`) is a
pure function of plain dataclasses — none of them import `yfinance` or touch
the network. `data.py` isolates the one place that talks to an external data
source behind a `FundamentalsProvider` protocol, so the entire numerical core
is unit-tested against `StaticProvider` fixtures and stays fast and
deterministic in CI.

## Installation

```bash
git clone https://github.com/elmarfarajov/equity-valuation-engine.git
cd equity-valuation-engine
python -m venv .venv
.venv\Scripts\activate        # on Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"
```

## Usage

```bash
# Full valuation: DCF + sensitivity + Monte Carlo + comps against three peers
valuation-engine MSFT --peers GOOGL AAPL ORCL

# Override the default assumptions
valuation-engine MSFT --peers GOOGL AAPL \
  --growth 0.12 0.10 0.08 0.06 0.05 \
  --terminal-growth 0.025 \
  --risk-free-rate 0.042 \
  --equity-risk-premium 0.05
```

This writes `reports/MSFT/MSFT_equity_research_note.html` with the charts in
an adjacent `charts/` folder. Free cash flow, beta, shares outstanding and
trading multiples are pulled live from Yahoo Finance via `yfinance` — no API
key required.

Or use it as a library:

```python
from valuation_engine.data import StaticProvider
from valuation_engine.cli import analyze

report_path = analyze(
    ticker="MSFT",
    peer_tickers=["GOOGL", "AAPL"],
    growth_rates=[0.10, 0.08, 0.06, 0.05, 0.04],
    terminal_growth=0.025,
    risk_free_rate=0.042,
    equity_risk_premium=0.05,
    pre_tax_cost_of_debt=0.055,
    tax_rate=0.21,
    output_dir=Path("reports/MSFT"),
    provider=YFinanceProvider(),
)
```

## Testing

```bash
pytest -v
```

All 20 unit tests validate the financial math against hand-derived values
(see `docs/methodology.md`) — WACC weighting, DCF present-value sums, Gordon
Growth terminal value, the EV/EBITDA-to-equity-value bridge in comps, and
statistical properties of the Monte Carlo output (reproducibility under a
fixed seed, valid probability bounds, ordered percentiles).

## Troubleshooting

On Windows, if the project lives under a path containing non-ASCII
characters (e.g. certain localized "Desktop" folder names), the `curl_cffi`
backend used by `yfinance` can fail with a `UnicodeEncodeError` while
resolving its CA certificate path. `pytest` is unaffected (it never touches
the network), but the live CLI needs an ASCII-only path — clone the repo to
somewhere like `C:\dev\equity-valuation-engine` if you hit this.

## Roadmap

- [ ] Three-statement model integration (link DCF assumptions to a full
      income statement / balance sheet build rather than a standalone FCF growth rate)
- [ ] LBO and precedent-transaction valuation modules alongside DCF and comps
- [ ] A lightweight web dashboard (Streamlit) for interactive assumption tuning
- [ ] Correlated Monte Carlo draws (currently growth, WACC and terminal
      growth are sampled independently; see `docs/methodology.md#limitations`)

## Disclaimer

Built for educational and research purposes to explore valuation modeling and
software design together. Output is not investment advice.

## License

[MIT](LICENSE)
