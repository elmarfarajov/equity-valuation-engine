# Methodology

This document derives the formulas implemented in `src/valuation_engine/`, so the
numbers in a generated report can be checked by hand.

## 1. Cost of equity — CAPM

The Capital Asset Pricing Model estimates the return equity investors require
given the stock's systematic (non-diversifiable) risk:

$$ R_e = R_f + \beta \cdot ERP $$

- $R_f$ — risk-free rate (defaults to the 10-year Treasury yield)
- $\beta$ — the stock's beta versus the market
- $ERP$ — equity risk premium, $E[R_m] - R_f$

Implemented in [`capm.cost_of_equity_capm`](../src/valuation_engine/capm.py).

## 2. Weighted-average cost of capital (WACC)

WACC blends the cost of equity and the after-tax cost of debt, weighted by
each source's share of the firm's total capitalization:

$$ WACC = \frac{E}{E+D} R_e + \frac{D}{E+D} R_d (1 - T_c) $$

- $E$ — market capitalization
- $D$ — total debt
- $R_d$ — pre-tax cost of debt
- $T_c$ — marginal corporate tax rate (interest is tax-deductible, hence the
  $(1-T_c)$ shield)

Implemented in [`capm.wacc`](../src/valuation_engine/capm.py).

## 3. Discounted cash flow (DCF)

Free cash flow is projected for an explicit forecast window using
analyst-supplied growth rates, then discounted back to the present at WACC:

$$ FCF_t = FCF_0 \prod_{i=1}^{t}(1+g_i), \qquad PV(FCF_t) = \frac{FCF_t}{(1+WACC)^t} $$

Cash flows beyond the forecast window are valued with the Gordon Growth
(perpetuity growth) model, which assumes cash flow grows at a constant rate
$g_\infty$ forever:

$$ TV_n = \frac{FCF_n (1+g_\infty)}{WACC - g_\infty} $$

which is itself discounted back $n$ periods. Enterprise value is the sum of
the discounted forecast cash flows and the discounted terminal value; equity
value subtracts net debt (total debt minus cash):

$$ EV = \sum_{t=1}^{n} PV(FCF_t) + PV(TV_n), \qquad
   \text{Equity Value} = EV - \text{Net Debt}, \qquad
   \text{Value/Share} = \frac{\text{Equity Value}}{\text{Shares Outstanding}} $$

The model requires $WACC > g_\infty$ for the perpetuity sum to converge; the
engine raises a `ValueError` rather than silently returning a negative or
infinite terminal value. Implemented in
[`dcf.run_dcf`](../src/valuation_engine/dcf.py).

## 4. Sensitivity analysis

A single DCF run reflects one specific (WACC, terminal growth) pair, but both
are estimates, not observed facts. `sensitivity.sensitivity_table` reruns the
DCF across a grid of WACC and terminal-growth values so the report shows how
much the "point estimate" actually moves as those assumptions change.

## 5. Monte Carlo simulation

Rather than treating growth, WACC and terminal growth as fixed inputs, the
Monte Carlo module treats them as random variables:

- each forecast-year growth rate gets an independent $N(0, \sigma_g)$ shock
- WACC is drawn from $N(WACC_0, \sigma_{wacc})$
- terminal growth is drawn from $N(g_{\infty,0}, \sigma_g^{\infty})$, re-drawn
  below the sampled WACC on the rare trial where it would otherwise violate
  convergence

Re-running the deterministic DCF thousands of times over these draws produces
an empirical distribution of intrinsic value per share, from which the report
extracts the median, the 5th/95th percentiles, and $P(\text{fair value} >
\text{market price})$ — a rough, model-based proxy for the probability the
stock is undervalued given the stated assumptions. Implemented in
[`montecarlo.run_monte_carlo`](../src/valuation_engine/montecarlo.py).

## 6. Comparable company analysis (comps)

DCF is sensitive to long-horizon assumptions, so the report cross-checks it
against how the market currently prices similar companies. For a set of
peers, the engine takes the **median** (robust to outliers) of each trading
multiple and applies it to the target's own fundamentals:

$$ \text{Implied Value}_{P/E} = \text{median}(P/E_{\text{peers}}) \times EPS_{\text{target}} $$

$$ \text{Implied Value}_{P/S} = \text{median}(P/S_{\text{peers}}) \times \text{Sales/Share}_{\text{target}} $$

EV/EBITDA is an **enterprise-value** multiple, so applying it yields an
implied enterprise value per share; net debt per share is subtracted to
bridge back to an implied **equity** value per share — a detail that is easy
to get wrong and is covered explicitly by `tests/test_comps.py`:

$$ \text{Implied Value}_{EV/EBITDA} = \text{median}(EV/EBITDA_{\text{peers}}) \times \text{EBITDA/Share}_{\text{target}} - \text{Net Debt/Share}_{\text{target}} $$

Implemented in [`comps.comps_valuation`](../src/valuation_engine/comps.py).

## Limitations

- Growth-rate and WACC uncertainty are modeled as independent normal shocks
  for tractability; in reality these are correlated (e.g. a lower discount
  rate environment often coincides with different growth expectations).
- The comps model uses a fixed ±10% band around a single implied value for
  the football-field chart, since a point multiple has no native
  distribution — it is a display simplification, not a modeled uncertainty.
- Free cash flow, beta and multiples come directly from Yahoo Finance via
  `yfinance`; the engine does not attempt to normalize for one-off items,
  buybacks, or accounting differences across peers.
