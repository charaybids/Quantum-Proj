"""Generate all figures for the ISFS622 technical report:
  * rendered formula images (problem, QUBO/Ising, QAOA, metrics)
  * the ACTUAL 8-qubit QAOA quantum circuit (plus an RZZ gadget)
  * performance charts (growth, drawdown, Sharpe/return, selection frequency)
Also dumps metrics.json / circuit.json consumed by _build_report.py.
"""
import os
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

import portfolio_utils as pu
import quantum_portfolio_qaoa as quantum
import classical_portfolio_ml as classical

from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit.circuit import QuantumCircuit, Parameter
from qiskit.circuit.library import QAOAAnsatz

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "report", "figures")
os.makedirs(FIG, exist_ok=True)


def render_eq(lines, name, fontsize=19, width=7.6):
    """Render a list of mathtext strings as stacked equations -> PNG."""
    n = len(lines)
    fig = plt.figure(figsize=(width, 0.62 * n + 0.25))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    for i, line in enumerate(lines):
        ax.text(0.01, 1 - (i + 0.5) / n, line, fontsize=fontsize,
                va="center", ha="left", color="#111111")
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white",
                pad_inches=0.18)
    plt.close(fig)
    print("wrote", name)


# ----------------------------------------------------------------------
# 1. Formula images
# ----------------------------------------------------------------------
render_eq([
    r"$\mathrm{minimise}\quad f(x)\;=\;q\,x^{\mathsf{T}}\Sigma\,x\;-\;\mu^{\mathsf{T}}x$",
    r"$\mathrm{subject\ to}\quad \sum_{i=1}^{N} x_i = B,\qquad x_i \in \{0,1\}$",
], "eq_problem.png")

render_eq([
    r"$\tilde f(x)=q\,x^{\mathsf{T}}\Sigma x-\mu^{\mathsf{T}}x+\lambda\left(\sum_i x_i-B\right)^{2}$",
    r"$x_i=\frac{1-Z_i}{2}\;\;\Rightarrow\;\;H_C=\sum_i h_i Z_i+\sum_{i<j}J_{ij}Z_iZ_j+\mathrm{const}$",
], "eq_qubo.png")

render_eq([
    r"$|\psi(\gamma,\beta)\rangle=e^{-i\beta H_M}e^{-i\gamma H_C}\,H^{\otimes N}|0\rangle^{\otimes N}$",
    r"$U_C(\gamma)=e^{-i\gamma H_C}=\prod_i R_Z(2\gamma h_i)\prod_{i<j}R_{ZZ}(2\gamma J_{ij})$",
    r"$U_M(\beta)=e^{-i\beta H_M}=\prod_i R_X(2\beta),\qquad H_M=\sum_i X_i$",
    r"$(\gamma^{*},\beta^{*})=\mathrm{arg\,min}_{\gamma,\beta}\,\langle\psi(\gamma,\beta)|H_C|\psi(\gamma,\beta)\rangle$",
], "eq_qaoa.png")

render_eq([
    r"$R_{\mathrm{ann}}=(1+\bar r)^{P}-1,\qquad \sigma_{\mathrm{ann}}=\sigma_r\sqrt{P}\quad(P=12)$",
    r"$\mathrm{Sharpe}=\frac{R_{\mathrm{ann}}-r_f}{\sigma_{\mathrm{ann}}}\quad(r_f=2\%)$",
    r"$W_t=\prod_{k\leq t}(1+r_k),\qquad \mathrm{MaxDD}=\min_t\left(\frac{W_t}{\max_{s\leq t}W_s}-1\right)$",
    r"$\mathrm{Calmar}=\frac{R_{\mathrm{ann}}}{|\mathrm{MaxDD}|}$",
], "eq_metrics.png")


# ----------------------------------------------------------------------
# 2. The actual quantum circuit
# ----------------------------------------------------------------------
returns = pu.download_monthly_returns()
assets = list(returns.columns)

window = returns.iloc[-37:-1]               # a representative 36-month window
mu = window.mean().values
sigma = window.cov().values
qp = quantum.build_portfolio_qp(mu, sigma, assets, budget=4, risk_aversion=1.0)
qubo = QuadraticProgramToQubo().convert(qp)
op, offset = qubo.to_ising()

ansatz = QAOAAnsatz(cost_operator=op, reps=1)
ansatz_dec = ansatz.decompose(reps=2)       # expose H / RZ / RZZ / RX gates

# circuit composition stats (from the Ising operator)
n_qubits = op.num_qubits
n_linear = sum(1 for p in op.paulis if np.sum(p.z) == 1)
n_quad = sum(1 for p in op.paulis if np.sum(p.z) == 2)
ops = ansatz_dec.count_ops()
circuit_stats = {
    "n_qubits": int(n_qubits),
    "n_rz_linear": int(n_linear),
    "n_rzz_quadratic": int(n_quad),
    "depth": int(ansatz_dec.depth()),
    "gate_counts": {k: int(v) for k, v in ops.items()},
    "n_parameters": int(ansatz.num_parameters),
}
with open(os.path.join(FIG, "circuit.json"), "w") as fh:
    json.dump(circuit_stats, fh, indent=2)
print("circuit stats:", circuit_stats)

# draw the full circuit
fig = ansatz_dec.draw("mpl", fold=26, scale=0.65, style={"name": "clifford"})
fig.savefig(os.path.join(FIG, "circuit_qaoa.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print("wrote circuit_qaoa.png")

# RZZ gadget: how a ZZ coupling is built from CX - RZ - CX
theta = Parameter("2γJij")
gad = QuantumCircuit(2, name="Rzz")
gad.cx(0, 1)
gad.rz(theta, 1)
gad.cx(0, 1)
fig = gad.draw("mpl", scale=0.9)
fig.savefig(os.path.join(FIG, "circuit_zz_gadget.png"), dpi=200,
            bbox_inches="tight", facecolor="white")
plt.close(fig)
print("wrote circuit_zz_gadget.png")


# ----------------------------------------------------------------------
# 3. Performance charts (full backtest)
# ----------------------------------------------------------------------
print("running backtests (this takes a few minutes)...")
qres = quantum.run_quantum_backtest(returns)
cres = classical.run_classical_ml_backtest(returns)

qr = qres["strategy_returns"]
cr = cres["strategy_returns"]
dates = qr.index
aligned = returns.loc[dates]
bm6040 = pd.Series(aligned.values @ pu.benchmark_60_40(assets), index=dates,
                   name="Static 60/40")
bmeq = pd.Series(aligned.values @ pu.benchmark_equal_weight(assets), index=dates,
                 name="Equal Weight")

strategies = {
    "QAOA Quantum": qr,
    "Classical ML": cr,
    "Static 60/40": bm6040,
    "Equal Weight": bmeq,
}
perf = pu.summarise_performance(strategies)

colors = {"QAOA Quantum": "#1f77b4", "Classical ML": "#d62728",
          "Static 60/40": "#2ca02c", "Equal Weight": "#9467bd"}

# (a) growth of $1
fig, ax = plt.subplots(figsize=(9, 5))
for name, r in strategies.items():
    (1 + r).cumprod().plot(ax=ax, label=name, color=colors[name], lw=1.8)
ax.set_title("Growth of $1 (out-of-sample)")
ax.set_ylabel("Portfolio value ($)"); ax.set_xlabel("Date")
ax.legend(); ax.grid(True, alpha=0.3)
fig.savefig(os.path.join(FIG, "chart_growth.png"), dpi=200,
            bbox_inches="tight", facecolor="white"); plt.close(fig)

# (b) drawdown
fig, ax = plt.subplots(figsize=(9, 5))
for name, r in strategies.items():
    w = (1 + r).cumprod()
    (w / w.cummax() - 1).plot(ax=ax, label=name, color=colors[name], lw=1.5)
ax.set_title("Drawdown"); ax.set_ylabel("Drawdown"); ax.set_xlabel("Date")
ax.legend(); ax.grid(True, alpha=0.3)
fig.savefig(os.path.join(FIG, "chart_drawdown.png"), dpi=200,
            bbox_inches="tight", facecolor="white"); plt.close(fig)

# (c) Sharpe + annualised return bars
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
perf["Sharpe Ratio"].plot(kind="bar", ax=axes[0], color="#1f77b4")
axes[0].set_title("Sharpe ratio"); axes[0].tick_params(axis="x", rotation=25)
axes[0].grid(True, axis="y", alpha=0.3)
perf["Annualised Return"].plot(kind="bar", ax=axes[1], color="#2ca02c")
axes[1].set_title("Annualised return"); axes[1].tick_params(axis="x", rotation=25)
axes[1].grid(True, axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "chart_sharpe_return.png"), dpi=200,
            bbox_inches="tight", facecolor="white"); plt.close(fig)

# (d) selection frequency
def freq(selections):
    counts = {a: 0 for a in assets}
    for sel in selections:
        for a in sel:
            counts[a] += 1
    return pd.Series(counts) / len(selections)

frequency = pd.DataFrame({
    "QAOA Quantum": freq(qres["selections"]),
    "Classical ML": freq(cres["selections"]),
})
fig, ax = plt.subplots(figsize=(9, 4.6))
frequency.plot(kind="bar", ax=ax, color=["#1f77b4", "#d62728"])
ax.set_title("Fraction of months each asset was held")
ax.set_ylabel("Fraction of months"); ax.tick_params(axis="x", rotation=0)
ax.grid(True, axis="y", alpha=0.3)
fig.savefig(os.path.join(FIG, "chart_selection.png"), dpi=200,
            bbox_inches="tight", facecolor="white"); plt.close(fig)

# dump metrics for the report builder
metrics = {
    "performance": {name: {
        "ann_return": float(perf.loc[name, "Annualised Return"]),
        "ann_vol": float(perf.loc[name, "Annualised Volatility"]),
        "sharpe": float(perf.loc[name, "Sharpe Ratio"]),
        "max_dd": float(perf.loc[name, "Maximum Drawdown"]),
        "calmar": float(perf.loc[name, "Calmar Ratio"]),
    } for name in strategies},
    "quantum_diagnostics": qres["diagnostics"],
    "ml_diagnostics": {k: (v if not isinstance(v, (list,)) else v)
                       for k, v in cres["diagnostics"].items()},
    "n_oos_months": int(len(qr)),
}
with open(os.path.join(FIG, "metrics.json"), "w") as fh:
    json.dump(metrics, fh, indent=2, default=str)
print("wrote metrics.json")
print(perf.round(4).to_string())
print("DONE")
