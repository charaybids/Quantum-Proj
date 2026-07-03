# ============================================================
# Quantum-Assisted Multi-Asset Portfolio Optimisation
# Asset-selection mean-variance QUBO solved with Qiskit QAOA
# ============================================================
#
# Business problem
# ----------------
# From a universe of N exchange-traded funds, choose exactly B of them
# to hold (equal-weighted) for the next month so as to minimise
#
#       q * x^T S x  -  mu^T x        subject to   sum(x) = B,   x_i in {0,1}
#
# where mu is the vector of expected (mean) returns over a trailing
# look-back window, S is the return covariance matrix and q is the
# investor's risk-aversion. Choosing B of N assets is a combinatorial
# (C(N, B)) optimisation problem -- exactly the class of problem QAOA
# targets -- which is why this is a genuine quantum use-case rather
# than a trivial "pick the best of a short list".
#
# Each monthly decision is a fresh QUBO solved by QAOA on the local
# state-vector simulator (8 assets -> 8 qubits, milliseconds per solve).
#
# Install first (already in the qml-classiq env):
#   pip install yfinance pandas numpy qiskit qiskit-optimization
#               qiskit-algorithms qiskit-aer scikit-learn matplotlib scipy

import time
import warnings
import numpy as np
import pandas as pd

from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit_algorithms import QAOA, NumPyMinimumEigensolver
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals
from qiskit.primitives import StatevectorSampler
from scipy.sparse import SparseEfficiencyWarning

import portfolio_utils as pu

# The exact eigensolver and QUBO converter work on sparse matrices and emit
# noisy (harmless) efficiency warnings -- silence them so the backtest log
# stays readable.
warnings.filterwarnings("ignore", category=SparseEfficiencyWarning)


# ------------------------------------------------------------
# QUBO construction
# ------------------------------------------------------------
def build_portfolio_qp(mu, sigma, assets, budget, risk_aversion):
    """Mean-variance asset-selection problem as a QuadraticProgram."""
    qp = QuadraticProgram(name="portfolio_selection")

    for asset in assets:
        qp.binary_var(asset)

    # minimise  q * x^T S x  -  mu^T x
    linear = {asset: -mu[i] for i, asset in enumerate(assets)}
    quadratic = {}
    for i, ai in enumerate(assets):
        for j, aj in enumerate(assets):
            quadratic[(ai, aj)] = risk_aversion * sigma[i, j]

    qp.minimize(linear=linear, quadratic=quadratic)

    # hold exactly `budget` assets
    qp.linear_constraint(
        linear={asset: 1 for asset in assets},
        sense="==",
        rhs=budget,
        name="budget",
    )
    return qp


# ------------------------------------------------------------
# Solvers
# ------------------------------------------------------------
def make_qaoa(reps, maxiter, seed, shots=1024):
    # Seed the global RNG so QAOA's random initial point is reproducible;
    # without this the COBYLA start varies run-to-run and the solution
    # quality (match rate) drifts between identical runs.
    algorithm_globals.random_seed = seed
    sampler = StatevectorSampler(default_shots=shots, seed=seed)
    return QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps)


def _qubo_objective(selected, assets, mu, sigma, risk_aversion):
    """Evaluate q*x^T S x - mu^T x for a 0/1 selection (lower is better)."""
    idx = [assets.index(a) for a in selected]
    x = np.zeros(len(assets))
    x[idx] = 1.0
    return float(risk_aversion * x @ sigma @ x - mu @ x)


def _selection_from_result(result, assets, mu, sigma, budget, risk_aversion):
    """Read the chosen assets off a solver result, with a feasibility repair.

    The budget constraint is enforced through a penalty term, so a sampled
    bitstring can occasionally hold the wrong number of assets. When that
    happens we fall back to the best `budget` assets by risk-adjusted mean.
    """
    selected = [a for a, xi in zip(assets, result.x) if round(xi) == 1]
    if len(selected) != budget:
        score = mu - risk_aversion * np.diag(sigma)
        order = np.argsort(score)[::-1]
        selected = [assets[i] for i in order[:budget]]
    return selected


def solve_window(train_returns, assets, budget, risk_aversion,
                 reps, maxiter, seed, shots=1024, with_exact=True):
    """Solve one monthly QUBO with QAOA (and optionally the exact solver).

    Returns the QAOA-selected assets plus a small record comparing the QAOA
    solution to the classical optimum on the same problem.
    """
    mu = train_returns.mean().values
    sigma = train_returns.cov().values
    qp = build_portfolio_qp(mu, sigma, assets, budget, risk_aversion)

    start = time.perf_counter()
    qaoa_res = MinimumEigenOptimizer(make_qaoa(reps, maxiter, seed, shots)).solve(qp)
    qaoa_seconds = time.perf_counter() - start
    qaoa_sel = _selection_from_result(qaoa_res, assets, mu, sigma,
                                      budget, risk_aversion)

    record = {"qaoa_seconds": qaoa_seconds}

    if with_exact:
        exact_res = MinimumEigenOptimizer(NumPyMinimumEigensolver()).solve(qp)
        exact_sel = _selection_from_result(exact_res, assets, mu, sigma,
                                           budget, risk_aversion)
        # Compare the actual budget-feasible selections both engines use.
        qaoa_obj = _qubo_objective(qaoa_sel, assets, mu, sigma, risk_aversion)
        exact_obj = _qubo_objective(exact_sel, assets, mu, sigma, risk_aversion)
        record["matched"] = set(qaoa_sel) == set(exact_sel)
        # optimality gap >= 0; 0.0 means QAOA found the optimal subset.
        record["optimality_gap"] = max(0.0, qaoa_obj - exact_obj)

    return qaoa_sel, record


def circuit_diagnostics(train_returns, assets, budget, risk_aversion,
                        reps, maxiter, seed, shots=1024):
    """Characterise the QAOA ansatz (qubits, depth) on one window."""
    mu = train_returns.mean().values
    sigma = train_returns.cov().values
    qp = build_portfolio_qp(mu, sigma, assets, budget, risk_aversion)

    qubo = QuadraticProgramToQubo().convert(qp)
    n_qubits = qubo.get_num_binary_vars()

    qaoa_res = MinimumEigenOptimizer(make_qaoa(reps, maxiter, seed, shots)).solve(qp)
    depth = None
    try:
        circuit = qaoa_res.min_eigen_solver_result.optimal_circuit
        depth = circuit.decompose().depth()
    except Exception:
        depth = None

    return {"n_qubits": n_qubits, "circuit_depth": depth}


# ------------------------------------------------------------
# Walk-forward backtest
# ------------------------------------------------------------
def run_quantum_backtest(monthly_returns, budget=4, risk_aversion=1.0,
                         lookback=36, reps=1, maxiter=80, rebalance=3,
                         seed=42, shots=1024, verbose=False):
    """Roll a QAOA-selected, equal-weighted portfolio through history.

    Parameters
    ----------
    monthly_returns : DataFrame  (rows = months, cols = assets)
    budget          : number of assets to hold each period
    risk_aversion   : weight on variance in the objective (q in q*var - mean)
    lookback        : trailing months used to estimate mu and S
    reps            : QAOA layers (p)
    maxiter         : COBYLA iterations per solve
    rebalance       : re-optimise every `rebalance` months (1 = monthly)

    At every rebalance the same QUBO is also solved exactly (NumPy eigensolver)
    so we can report how often QAOA reproduces the classical optimum.
    """
    assets = list(monthly_returns.columns)

    strategy_returns = []
    selections = []
    dates = []
    records = []

    current_selection = None

    for i in range(lookback, len(monthly_returns) - 1):
        # re-optimise only on rebalancing months; otherwise hold
        if current_selection is None or (i - lookback) % rebalance == 0:
            train_data = monthly_returns.iloc[i - lookback:i]
            current_selection, record = solve_window(
                train_data, assets, budget, risk_aversion,
                reps, maxiter, seed, shots, with_exact=True,
            )
            records.append(record)
            if verbose:
                tag = "==" if record["matched"] else "!="
                print(f"{monthly_returns.index[i].date()}  {tag}  {current_selection}")

        weights = pu.equal_weights(current_selection, assets)
        next_month = monthly_returns.iloc[i + 1]

        strategy_returns.append(float(next_month.values @ weights))
        selections.append(tuple(current_selection))
        dates.append(monthly_returns.index[i + 1])

    strategy_returns = pd.Series(strategy_returns, index=dates,
                                 name="QAOA_Quantum")

    # aggregate solution-quality stats across every rebalance
    n_rebalances = len(records)
    match_rate = np.mean([r["matched"] for r in records])
    mean_optimality_gap = float(np.mean([r["optimality_gap"] for r in records]))
    total_qaoa_seconds = float(np.sum([r["qaoa_seconds"] for r in records]))

    circuit = circuit_diagnostics(
        monthly_returns.iloc[-lookback - 1:-1], assets, budget,
        risk_aversion, reps, maxiter, seed, shots,
    )

    diagnostics = {
        "n_qubits": circuit["n_qubits"],
        "circuit_depth": circuit["circuit_depth"],
        "qaoa_reps": reps,
        "cobyla_maxiter": maxiter,
        "shots": shots,
        "risk_aversion": risk_aversion,
        "n_rebalances": n_rebalances,
        "match_rate": float(match_rate),
        "mean_optimality_gap": mean_optimality_gap,
        "total_qaoa_seconds": total_qaoa_seconds,
    }

    return {
        "strategy_returns": strategy_returns,
        "selections": selections,
        "diagnostics": diagnostics,
    }


# ------------------------------------------------------------
# Stand-alone demo
# ------------------------------------------------------------
if __name__ == "__main__":
    returns = pu.download_monthly_returns()
    print(f"Loaded {returns.shape[0]} months x {returns.shape[1]} assets\n")

    result = run_quantum_backtest(returns, verbose=True)

    perf = pu.summarise_performance({
        "QAOA Quantum": result["strategy_returns"],
    })
    print("\nPerformance:")
    print(perf.round(4).to_string())

    print("\nQuantum circuit diagnostics:")
    for k, v in result["diagnostics"].items():
        print(f"  {k}: {v}")
