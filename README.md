# Quantum vs Classical Portfolio Optimisation

**ISFS622 – Quantum Computing in Financial Services · Assignment 2 (Group Project)**

A proof of concept that frames monthly multi-asset portfolio selection as a
**cardinality-constrained mean-variance QUBO** and solves it with the **Quantum
Approximate Optimisation Algorithm (QAOA)** in Qiskit. The quantum engine is
benchmarked against a classical machine-learning challenger and two passive
benchmarks through an identical walk-forward backtest.

---

## Business problem

Each month, choose **exactly 4 of 8 ETFs** to hold (equal-weighted) until the
next rebalance, so as to maximise risk-adjusted return. The universe spans the
major asset classes:

| Ticker | Exposure | Ticker | Exposure |
|--------|----------|--------|----------|
| SPY | US large-cap equity | LQD | Investment-grade credit |
| QQQ | US growth equity | TLT | Long-term Treasuries |
| EFA | Developed intl. equity | GLD | Gold |
| EEM | Emerging-market equity | DBC | Broad commodities |

Choosing *B* of *N* assets is a combinatorial problem (`C(N, B)` candidates) –
exactly the class of problem QAOA targets.

---

## Approach

Both engines use the **same** rule (hold 4 of 8, equal-weighted) so the
comparison isolates the *selection method*.

- **Quantum (QAOA)** — minimise `q·xᵀΣx − μᵀx` subject to `Σxᵢ = 4`, `xᵢ ∈ {0,1}`,
  where `μ`/`Σ` are the mean/covariance over a trailing 36-month window and
  `q = 1.0` is the risk-aversion. Solved as a `QuadraticProgram` →
  `MinimumEigenOptimizer(QAOA(...))`. A classical `NumPyMinimumEigensolver`
  solves the same problem **exactly at every rebalance** to validate the
  quantum solution.
- **Classical ML** — a `RandomForestRegressor` predicts each asset's next-month
  return from momentum / volatility features; the top 4 are held.
- **Benchmarks** — static 60/40 (SPY/TLT) and equal-weight-all.

The backtest is walk-forward (36-month lookback, quarterly rebalancing, ~10
years of monthly data, 82 out-of-sample months) with **no look-ahead bias**.

---

## Results

| Strategy | Ann. Return | Ann. Volatility | Sharpe | Max Drawdown |
|----------|-------------|-----------------|--------|--------------|
| **QAOA Quantum** | **9.8 %** | 11.3 % | **0.69** | −20.5 % |
| Classical ML (Random Forest) | 8.5 % | 14.2 % | 0.46 | −17.7 % |
| Static 60/40 | 8.7 % | 12.9 % | 0.52 | −26.2 % |
| Equal-Weight | 7.9 % | 11.5 % | 0.51 | −20.3 % |

**Solution quality:** across all 28 rebalances the 8-qubit QAOA circuit
reproduced the exact optimal asset subset every time (`match_rate = 1.0`,
`mean_optimality_gap = 0.0`). The quantum strategy delivered the **best
risk-adjusted return** of all four strategies.

---

## Project structure

```
Project/
├── portfolio_utils.py          # Data download/caching + performance metrics + benchmarks
├── quantum_portfolio_qaoa.py   # QUBO construction, QAOA solver, walk-forward backtest
├── classical_portfolio_ml.py   # Random-Forest return predictor + backtest (challenger)
├── comparison.ipynb            # End-to-end comparison: runs both engines, tables & plots
├── requirements.txt            # Pinned dependencies
├── data/                       # Cached monthly_returns.csv (auto-created on first run)
└── report/
    ├── QCTechSpecTemplate.docx          # Provided template
    ├── ISFS622_TechnicalSpecification.docx  # Filled technical specification report
    └── _build_report.py                 # Script that generates the report from the template
```

---

## Setup

Tested in a conda environment named `qml-classiq` (Python 3.11).

```powershell
conda activate qml-classiq
pip install -r requirements.txt
```

Key pinned versions: `qiskit==2.4.1`, `qiskit-optimization==0.7.0`,
`qiskit-algorithms==0.4.0`, `yfinance==1.4.1`, `scikit-learn==1.8.0`.

> **Note:** Qiskit 2.x uses the V2 primitives — the solver uses
> `qiskit.primitives.StatevectorSampler`. Do **not** use Qiskit Aer for the QAOA
> ansatz here.

---

## How to run

**Option A — notebook (recommended):**
1. Open `comparison.ipynb` and select the **qml-classiq** kernel (top-right).
2. Run all cells top-to-bottom. Price data is downloaded once and cached to `data/`.
   The full run takes a few minutes (the quantum backtest is the slow part).

**Option B — scripts:**
```powershell
python quantum_portfolio_qaoa.py    # standalone quantum backtest + diagnostics
python classical_portfolio_ml.py    # standalone classical backtest + diagnostics
```

**Reproducibility:** all randomness is seeded (`seed=42`), including the QAOA
initial point, so results are deterministic across runs.

---

## Notes

- The first run downloads ~10 years of monthly ETF data via `yfinance` and
  caches it to `data/monthly_returns.csv`; subsequent runs load from cache.
- At 8 qubits the problem is classically trivial — the value of the PoC is
  demonstrating a **correct, validated, end-to-end quantum workflow** that
  scales to large, constraint-rich universes where classical optimisation
  becomes intractable. See the technical specification in `report/` for the
  hardware, error-correction and commercial cost/benefit discussion.
