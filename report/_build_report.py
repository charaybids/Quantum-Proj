"""Build the ISFS622 technical specification report from the Word template,
embedding rendered formulas, the actual QAOA quantum circuit, and the
performance charts produced by _make_figures.py.
"""
import os
import json
import docx
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
TEMPLATE = os.path.join(HERE, "QCTechSpecTemplate.docx")
OUTPUT = os.path.join(HERE, "Technical Report.docx")

with open(os.path.join(FIG, "metrics.json")) as fh:
    M = json.load(fh)
with open(os.path.join(FIG, "circuit.json")) as fh:
    C = json.load(fh)

perf = M["performance"]
qd = M["quantum_diagnostics"]
md = M["ml_diagnostics"]


def pct(x):
    return f"{x * 100:.1f}%"


doc = docx.Document(TEMPLATE)


# ----------------------------------------------------------------------
# Insertion helpers
# ----------------------------------------------------------------------
def _is_heading1(el):
    if el.tag != qn("w:p"):
        return False
    pPr = el.find(qn("w:pPr"))
    if pPr is None:
        return False
    pStyle = pPr.find(qn("w:pStyle"))
    return pStyle is not None and pStyle.get(qn("w:val")) in ("Heading1", "Heading 1")


def heading1_paragraph(text):
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p.text.strip() == text:
            return p
    raise ValueError(f"Heading not found: {text}")


def clear_section(heading_p):
    el = heading_p._p.getnext()
    while el is not None and not _is_heading1(el):
        nxt = el.getnext()
        el.getparent().remove(el)
        el = nxt


def fill_section(heading_text, blocks):
    heading_p = heading1_paragraph(heading_text)
    clear_section(heading_p)
    anchor = heading_p._p
    for block in blocks:
        kind = block[0]
        if kind == "table":
            _, header, rows = block
            tbl = doc.add_table(rows=1, cols=len(header))
            tbl.style = "Table Grid"
            for j, h in enumerate(header):
                cell = tbl.rows[0].cells[j]
                cell.text = ""
                run = cell.paragraphs[0].add_run(h)
                run.bold = True
            for row in rows:
                cells = tbl.add_row().cells
                for j, val in enumerate(row):
                    cells[j].text = str(val)
            anchor.addnext(tbl._tbl)
            anchor = tbl._tbl
        elif kind == "img":
            _, fname, width, caption = block
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(os.path.join(FIG, fname), width=Inches(width))
            anchor.addnext(p._p)
            anchor = p._p
            if caption:
                cap = doc.add_paragraph(caption, style="Caption")
                cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                anchor.addnext(cap._p)
                anchor = cap._p
        else:
            if kind == "h2":
                p = doc.add_paragraph(block[1], style="Heading 2")
            elif kind == "b":
                p = doc.add_paragraph("\u2022  " + block[1])
            else:
                p = doc.add_paragraph(block[1])
            anchor.addnext(p._p)
            anchor = p._p


def set_label(label, value):
    for p in doc.paragraphs:
        if p.text.strip().lower().startswith(label.lower()):
            p.add_run(" " + value)
            return


# ----------------------------------------------------------------------
# Title block
# ----------------------------------------------------------------------
set_label("Topic:",
          "Quantum-Assisted Multi-Asset Portfolio Optimisation \u2013 "
          "Cardinality-Constrained Mean-Variance Asset Selection with QAOA")
set_label("Student Names:", "[Group member names]")


# ----------------------------------------------------------------------
# 1. Technical Solution Overview
# ----------------------------------------------------------------------
fill_section("Technical Solution Overview", [
    ("p", "This solution automates tactical asset allocation: every month it "
          "selects a diversified sub-portfolio from a multi-asset ETF universe. "
          "From eight ETFs spanning the major asset classes, the engine chooses "
          "exactly four assets to hold (equal-weighted) until the next "
          "rebalance. Choosing B assets from N is a cardinality-constrained "
          "combinatorial optimisation \u2013 the class of problem the quantum "
          "algorithm targets."),
    ("table",
     ["Ticker", "Exposure", "Ticker", "Exposure"],
     [["SPY", "US large-cap equity", "LQD", "Investment-grade credit"],
      ["QQQ", "US growth / technology", "TLT", "Long-dated Treasuries"],
      ["EFA", "Developed intl. equity", "GLD", "Gold"],
      ["EEM", "Emerging-market equity", "DBC", "Broad commodities"]]),
    ("p", "Business-case link: as the investable universe and the number of "
          "real-world constraints grow, the count of candidate portfolios "
          "explodes and classical optimisers struggle. The goal is better "
          "risk-adjusted returns and the ability to optimise large, "
          "constraint-rich portfolios that are intractable for exact classical "
          "methods. The proof of concept (PoC) implements the full pipeline and "
          "benchmarks the quantum engine against a classical machine-learning "
          "challenger and two passive benchmarks over roughly ten years of "
          "monthly data."),
    ("h2", "High-level system architecture"),
    ("b", "Data layer (portfolio_utils.py): downloads and caches monthly "
          "total-return series for the eight ETFs and computes the performance "
          "metrics."),
    ("b", "Model layer: at each rebalance a trailing 36-month window estimates "
          "the expected-return vector \u03bc and covariance matrix \u03a3, which define "
          "the optimisation problem."),
    ("b", "Quantum solver (quantum_portfolio_qaoa.py): the problem is mapped to "
          "a QUBO / Ising Hamiltonian and solved with QAOA; a classical "
          "optimiser (COBYLA) tunes the circuit parameters in a hybrid loop, and "
          "a classical exact eigensolver validates every solution."),
    ("b", "Application layer (comparison.ipynb): holds the selected assets, "
          "rolls the walk-forward backtest and compares all strategies. Only the "
          "solver call uses quantum hardware, so the architecture is unchanged "
          "at scale."),
])


# ----------------------------------------------------------------------
# 2. Quantum algorithms
# ----------------------------------------------------------------------
fill_section("Quantum algorithms", [
    ("h2", "Step 1 \u2013 Mean-variance problem formulation"),
    ("p", "Each asset i carries a binary decision variable x\u1d62 \u2208 {0,1} (1 if the "
          "asset is held). The monthly decision minimises a mean-variance "
          "objective subject to a cardinality (budget) constraint:"),
    ("img", "eq_problem.png", 5.4, "Figure 1. The asset-selection objective and budget constraint."),
    ("p", "Symbols: \u03bc is the vector of expected (mean) monthly returns and \u03a3 "
          "the return covariance matrix, both estimated over the trailing "
          "36-month window; q is the risk-aversion coefficient (q = 1.0); and "
          "B = 4 is the number of assets to hold. The term \u2212\u03bc\u1d40x rewards "
          "expected return, while q\u00b7x\u1d40\u03a3x penalises portfolio variance and "
          "rewards diversification through the off-diagonal covariances."),
    ("h2", "Step 2 \u2013 QUBO and Ising mapping"),
    ("p", "The equality constraint is folded into the objective as a quadratic "
          "penalty (weight \u03bb), giving an unconstrained binary problem (a QUBO). "
          "Substituting x\u1d62 = (1 \u2212 Z\u1d62)/2 maps the QUBO onto an Ising cost "
          "Hamiltonian H_C whose ground state encodes the optimal portfolio:"),
    ("img", "eq_qubo.png", 6.0, "Figure 2. Penalised QUBO and its mapping to an Ising Hamiltonian."),
    ("p", "Here Z\u1d62 is the Pauli-Z operator on qubit i, h\u1d62 are the local fields "
          "(from the linear \u2212\u03bc and penalty terms) and J\u1d62\u2c7c are the pairwise "
          "couplings (from \u03a3 and the penalty). Because the covariance matrix is "
          "dense, every asset pair couples \u2013 giving a fully connected "
          "interaction graph."),
    ("h2", "Step 3 \u2013 QAOA"),
    ("p", "QAOA is a hybrid quantum-classical variational algorithm. Starting "
          "from a uniform superposition, it applies p alternating layers of a "
          "cost unitary U_C(\u03b3) and a mixer unitary U_M(\u03b2); a classical "
          "optimiser tunes (\u03b3, \u03b2) to minimise the measured energy:"),
    ("img", "eq_qaoa.png", 5.8, "Figure 3. The QAOA ansatz state, its cost / mixer unitaries and the classical objective."),
    ("p", "U_C applies a Z-rotation R_Z(2\u03b3h\u1d62) per qubit and a two-qubit "
          "R_ZZ(2\u03b3J\u1d62\u2c7c) per coupled pair; U_M applies an X-rotation R_X(2\u03b2) "
          "per qubit. The PoC uses p = 1 (one layer), 1024 measurement shots and "
          "COBYLA (max 80 iterations) with a seeded initial point for "
          "reproducibility. After convergence the most probable bitstring is "
          "decoded into the selected assets."),
    ("h2", "The quantum circuit"),
    ("p", "With eight ETFs the circuit uses eight qubits. Figure 4 is the actual "
          "p = 1 QAOA circuit generated for one rebalance: a Hadamard layer "
          "(drawn as U(\u03c0/2,0,\u03c0)) creates the uniform superposition; the cost "
          "layer applies eight R_Z rotations (each labelled with its real h\u1d62 "
          "coefficient) and 28 R_ZZ couplings (labelled with \u03b3); and the mixer "
          "layer applies eight R_X(2\u03b2) rotations. The two free parameters are "
          "\u03b3 and \u03b2."),
    ("img", "circuit_qaoa.png", 4.6,
     "Figure 4. The actual 8-qubit, p = 1 QAOA circuit for one monthly rebalance "
     "(Hadamard layer \u2192 R_Z / R_ZZ cost layer \u2192 R_X mixer)."),
    ("table",
     ["Circuit property", "Value"],
     [["Qubits", str(C["n_qubits"])],
      ["Hadamard gates (superposition)", str(C["gate_counts"].get("u", 8))],
      ["R_Z rotations (linear / local fields)", str(C["n_rz_linear"])],
      ["R_ZZ couplings (quadratic = C(8,2))", str(C["n_rzz_quadratic"])],
      ["R_X rotations (mixer)", str(C["gate_counts"].get("rx", 8))],
      ["Variational parameters (\u03b3, \u03b2)", str(C["n_parameters"])],
      ["Gate-level depth", str(C["depth"])]]),
    ("p", "The 28 R_ZZ couplings equal C(8,2) = 28 \u2013 one for every asset pair \u2013 "
          "because the covariance matrix is fully dense. R_ZZ is not a native "
          "hardware gate; it is compiled from two CNOTs and one R_Z, as shown "
          "below. This is why dense couplings drive the two-qubit gate count and "
          "circuit depth, and why hardware connectivity matters at scale."),
    ("img", "circuit_zz_gadget.png", 2.6,
     "Figure 5. An R_ZZ(2\u03b3J\u1d62\u2c7c) coupling compiled into CNOT \u2013 R_Z \u2013 CNOT."),
    ("h2", "Error correction, mitigation and hardware"),
    ("p", "The PoC runs on a noiseless state-vector simulator, so results are "
          "exact. On real NISQ hardware, two-qubit gate errors (~10\u207b\u00b3), readout "
          "errors (~10\u207b\u00b2) and decoherence corrupt the measured energies. Near "
          "term, error mitigation (measurement-error mitigation, zero-noise "
          "extrapolation, dynamical decoupling) suffices for this shallow "
          "eight-qubit circuit. Long term, quantum error correction (surface "
          "codes, ~1000 physical qubits per logical qubit) is required as the "
          "universe and circuit depth grow. Hardware: the PoC needs only a "
          "workstation and simulator; near-term production uses cloud NISQ QPUs "
          "(superconducting IBM Heron, or trapped-ion IonQ / Quantinuum whose "
          "all-to-all connectivity suits the dense coupling graph); large, "
          "constrained portfolios are the long-term fault-tolerant target."),
])


# ----------------------------------------------------------------------
# 3. Quantum Advantages
# ----------------------------------------------------------------------
fill_section("Quantum Advantages", [
    ("h2", "Backtest methodology"),
    ("p", f"All strategies run through one walk-forward backtest: a 36-month "
          f"trailing window, quarterly rebalancing, and {M['n_oos_months']} "
          "out-of-sample months. There is no look-ahead \u2013 each decision uses "
          "only past data. Both engines obey the same rule (hold 4 of 8, "
          "equal-weighted), so the comparison isolates the selection method. The "
          "classical challenger is a Random Forest that predicts each asset's "
          "next-month return from momentum and volatility features and holds the "
          "top four."),
    ("h2", "Performance metrics \u2013 definitions"),
    ("p", "Metrics are computed from the monthly strategy returns r\u209c "
          "(\u0072\u0304 = mean, \u03c3_r = standard deviation, P = 12 periods/year):"),
    ("img", "eq_metrics.png", 6.0, "Figure 6. Definitions of the performance metrics."),
    ("b", "Annualised return R_ann compounds the mean monthly return to a yearly "
          "figure."),
    ("b", "Annualised volatility \u03c3_ann scales the monthly standard deviation by "
          "\u221aP."),
    ("b", "Sharpe ratio = excess return over volatility (risk-free rate "
          "r_f = 2%); the headline risk-adjusted measure."),
    ("b", "Maximum drawdown (MaxDD) is the worst peak-to-trough fall of the "
          "cumulative wealth curve W\u209c."),
    ("b", "Calmar ratio = annualised return divided by the absolute maximum "
          "drawdown."),
    ("h2", "Solution quality: QAOA vs the exact optimum"),
    ("p", f"Because eight qubits is small, a classical exact eigensolver finds "
          f"the true optimum and serves as ground truth. Across all "
          f"{qd['n_rebalances']} rebalances the QAOA circuit reproduced the exact "
          f"optimal asset subset every time (match rate = {qd['match_rate']:.2f}, "
          f"mean optimality gap = {qd['mean_optimality_gap']:.1f}), validating "
          "the QUBO mapping, the circuit and the optimisation loop."),
    ("h2", "Results"),
    ("table",
     ["Strategy", "Ann. Return", "Ann. Vol", "Sharpe", "Max Drawdown", "Calmar"],
     [["QAOA Quantum", pct(perf["QAOA Quantum"]["ann_return"]),
       pct(perf["QAOA Quantum"]["ann_vol"]), f"{perf['QAOA Quantum']['sharpe']:.2f}",
       pct(perf["QAOA Quantum"]["max_dd"]), f"{perf['QAOA Quantum']['calmar']:.2f}"],
      ["Classical ML (Random Forest)", pct(perf["Classical ML"]["ann_return"]),
       pct(perf["Classical ML"]["ann_vol"]), f"{perf['Classical ML']['sharpe']:.2f}",
       pct(perf["Classical ML"]["max_dd"]), f"{perf['Classical ML']['calmar']:.2f}"],
      ["Static 60/40", pct(perf["Static 60/40"]["ann_return"]),
       pct(perf["Static 60/40"]["ann_vol"]), f"{perf['Static 60/40']['sharpe']:.2f}",
       pct(perf["Static 60/40"]["max_dd"]), f"{perf['Static 60/40']['calmar']:.2f}"],
      ["Equal-Weight", pct(perf["Equal Weight"]["ann_return"]),
       pct(perf["Equal Weight"]["ann_vol"]), f"{perf['Equal Weight']['sharpe']:.2f}",
       pct(perf["Equal Weight"]["max_dd"]), f"{perf['Equal Weight']['calmar']:.2f}"]]),
    ("p", f"The quantum-selected portfolio earns the highest Sharpe ratio "
          f"({perf['QAOA Quantum']['sharpe']:.2f}) and the highest return at the "
          "lowest-but-one volatility, beating the ML challenger "
          f"({perf['Classical ML']['sharpe']:.2f}) and both passive benchmarks "
          f"({perf['Static 60/40']['sharpe']:.2f} / "
          f"{perf['Equal Weight']['sharpe']:.2f}). The charts below show the "
          "growth of $1, the drawdown profile and the metric comparison."),
    ("img", "chart_growth.png", 5.8, "Figure 7. Out-of-sample growth of $1."),
    ("img", "chart_drawdown.png", 5.8, "Figure 8. Drawdown profile (quantum has the shallowest deep-drawdowns of the active strategies)."),
    ("img", "chart_sharpe_return.png", 6.0, "Figure 9. Sharpe ratio and annualised return by strategy."),
    ("h2", "What each engine chose"),
    ("p", "The quantum optimiser and the ML predictor express different "
          "'personalities' \u2013 Figure 10 shows how often each asset was held. The "
          "mean-variance QAOA favours diversifying, lower-correlation assets, "
          "whereas the return-chasing Random Forest concentrates differently."),
    ("img", "chart_selection.png", 5.8, "Figure 10. Fraction of months each asset was held."),
    ("h2", "Why quantum is the right long-term solution"),
    ("p", "The decisive advantage is in scaling. Selecting B of N assets has "
          "C(N, B) combinations \u2013 for example C(500, 30) \u2248 10\u2074\u2078 \u2013 and adding "
          "realistic constraints (sector caps, cardinality, lot sizes, "
          "transaction costs) makes the problem NP-hard, beyond exact classical "
          "solvers. QAOA and quantum annealing explore this space with only N "
          "qubits (linear in assets), offering a credible route to high-quality "
          "solutions where classical heuristics degrade. The PoC demonstrates "
          "the complete, validated workflow that extends directly to that "
          "regime."),
])


# ----------------------------------------------------------------------
# 4. Commercial Cost and Benefits
# ----------------------------------------------------------------------
fill_section("Commercial Cost and Benefits", [
    ("p", "The cost profile is modest at PoC scale, but it is dominated by "
          "people and integration, not quantum compute. The figures below are "
          "indicative planning ranges (fully-loaded, US$) for a single-desk "
          "deployment inside an existing asset manager; they are order-of-"
          "magnitude, not quotes, and would be firmed up in a costed pilot."),
    ("h2", "Total cost of ownership (indicative)"),
    ("table",
     ["Item", "One-off", "Annual run", "Basis / notes"],
     [["Quantum compute (cloud QPU)", "\u2013", "~$2k\u2013$5k",
       "A single 8-qubit rebalance solves in seconds. Premium superconducting "
       "QPU time is priced on a per-second basis (order of US$1.60/sec, "
       "~US$96/min) [10]; a handful of jobs per rebalance over ~12 rebalances/yr "
       "is minor. The state-vector simulator is effectively free at N = 8. QPU "
       "cost scales with shots x circuit depth x jobs, so it grows with the "
       "universe, not linearly with AUM."],
      ["Development (build & validate)", "~$0.5m\u2013$1.5m", "\u2013",
       "2\u20134 FTE (quant researcher + quantum-software engineer + data/infra "
       "support) over ~6\u201312 months to build, validate and integrate the solver. "
       "Specialist quantum-finance engineers are scarce and carry a salary "
       "premium [4,5]."],
      ["Data feeds & classical infrastructure", "Low", "Low\u2013Moderate",
       "Market-data subscriptions and standard compute, largely reused from "
       "existing systems; incremental cost is small."],
      ["Talent, training & governance", "Moderate", "Moderate",
       "Upskilling the quant team, plus model-risk, compliance and audit "
       "overhead that any client-facing model attracts."]]),
    ("p", "Indicative all-in Year-1 cost is therefore on the order of "
          "US$1m\u2013US$2m, roughly 90% of which is headcount; quantum compute is a "
          "rounding error at this scale. Ongoing run-rate (compute + maintenance "
          "+ a partial team) is order US$0.3m\u2013US$0.6m/yr."),
    ("h2", "Benefits"),
    ("p", "Benefits fall into financial and strategic categories:"),
    ("b", f"Higher risk-adjusted return (gross, backtested): the quantum "
          f"strategy earned {pct(perf['QAOA Quantum']['ann_return'])} per year "
          f"versus {pct(perf['Static 60/40']['ann_return'])} for 60/40 at lower "
          f"volatility (Sharpe {perf['QAOA Quantum']['sharpe']:.2f} vs "
          f"{perf['Static 60/40']['sharpe']:.2f}). These figures are gross of "
          "transaction costs, taxes and slippage, which are not modelled and "
          "would reduce the live net edge."),
    ("b", "Scalability to large, constrained universes that classical exact "
          "optimisers handle poorly [4,5,9] \u2013 the capability that justifies the "
          "investment as mandates and constraint sets grow."),
    ("b", "Strategic differentiation and intellectual property ahead of the "
          "fault-tolerant era."),
    ("h2", "Break-even and cost-benefit assessment"),
    ("p", "On a US$1bn mandate, each sustained +1 percentage point of net "
          "annual return is ~US$10m; even +0.25\u20130.50 pt (~US$2.5m\u2013US$5m) "
          "covers the indicative Year-1 cost and recurring run-rate several times "
          "over. So the investment pays back inside a year IF a real, net-of-cost "
          "edge persists out of sample \u2013 which the current 82-month, gross, "
          "single-universe backtest does not yet establish (see Risks). "
          "Critically, at today\u2019s 8-qubit scale the measured edge comes from the "
          "mean-variance formulation, not from any quantum speed-up: a classical "
          "solver on the same QUBO returns the identical portfolio. The "
          "commercial rationale for investing now is therefore option value \u2013 "
          "building a validated, scalable, low-compute-cost pipeline and scarce "
          "in-house skills [4,5] so the firm can capture genuine quantum "
          "advantage once larger, constraint-rich problems and better hardware "
          "make it decisive."),
])


# ----------------------------------------------------------------------
# 5. Risks and Challenges
# ----------------------------------------------------------------------
fill_section("Risks and Challenges", [
    ("p", "Risks span three layers: the quantum technology, the stability of "
          "the model itself, and the risk borne by end clients. Each is managed "
          "by a staged adoption roadmap with parallel classical validation."),
    ("h2", "Technical and implementation risks"),
    ("b", "NISQ noise and decoherence limit circuit depth and solution quality "
          "on real hardware. Mitigation: error mitigation near term; error "
          "correction once fault-tolerant devices exist."),
    ("b", "Trainability / barren plateaus: variational gradients can vanish as "
          "qubits and depth grow [7]. Mitigation: problem-aware ansatze, seeded "
          "initial points (already used) and layer-wise training."),
    ("b", "Limited qubit count and connectivity: the dense covariance graph "
          "needs near all-to-all interaction; sparse hardware adds SWAP "
          "overhead. Mitigation: trapped-ion all-to-all hardware; efficient "
          "embeddings."),
    ("b", "No proven advantage at small scale: at eight qubits classical solvers "
          "win, so near-term value is strategic. Mitigation: treat as "
          "capability-building with a clear path to scale."),
    ("b", "Vendor / technology risk: fast-moving hardware and SDKs. Mitigation: "
          "pinned dependencies (Qiskit 2.4.1) and a solver abstraction layer."),
    ("b", "Talent scarcity: quantum-finance expertise is rare. Mitigation: "
          "targeted hiring and internal upskilling."),
    ("h2", "Model stability and robustness"),
    ("p", "Stability must be judged on two axes \u2013 the stability of the quantum "
          "solver and the stability of the underlying statistical model \u2013 because "
          "an unstable model erodes client trust even when the solver is exact."),
    ("b", f"Solver stability: QAOA is a stochastic, variational method whose "
          f"measured energy varies with shots and the initial point. In this PoC "
          f"(p = 1, {qd['shots']} shots, seeded COBYLA) it is deterministic and "
          f"reproduced the exact optimum at every one of {qd['n_rebalances']} "
          f"rebalances (match rate {qd['match_rate']:.2f}). At scale, rugged "
          "energy landscapes and barren plateaus [7] threaten this. Mitigation: "
          "fixed seeds, warm-starts, multiple restarts, CVaR objectives and "
          "always-on classical validation."),
    ("b", "Estimation stability (the dominant real-world risk): the mean-return "
          "vector and covariance matrix are estimated from a rolling 36-month "
          "window and are noisy. Mean-variance optimisation is notoriously "
          "input-sensitive \u2013 small estimate changes can flip the selected set and "
          "drive turnover, and naive diversification can rival optimised weights "
          "out of sample [8]. Mitigation: Ledoit-Wolf covariance shrinkage [6], "
          "robust/Bayesian estimation, turnover penalties and holding-period "
          "smoothing."),
    ("b", f"Sample and regime stability: results rest on {M['n_oos_months']} "
          "out-of-sample months, one asset universe and a limited span of market "
          "regimes; they may not persist out of sample or survive a stress event "
          "(e.g. a 2008-style crash). Mitigation: longer histories, multiple "
          "universes, and regime-conditioned bootstrap / Monte-Carlo stress "
          "testing before any capital is committed."),
    ("b", "Reproducibility and auditability: seeded runs, pinned dependencies "
          "and a parallel classical solver make every decision deterministic and "
          "fully logged \u2013 a prerequisite for model governance."),
    ("h2", "Risk to clients"),
    ("p", "Because this would ultimately allocate client capital, client-facing "
          "risks are treated as first-class, not a footnote."),
    ("b", f"Capital loss and drawdown: the backtest shows a maximum drawdown of "
          f"{pct(perf['QAOA Quantum']['max_dd'])}; clients can and will lose "
          "money in adverse periods, and past performance does not guarantee "
          "future results. Mitigation: explicit disclosure, drawdown limits and "
          "per-mandate risk budgeting."),
    ("b", "Backtest-to-live gap: reported returns are gross \u2013 transaction costs, "
          "taxes, slippage and capacity are not modelled \u2013 so live net returns "
          "will be lower. Mitigation: cost-aware backtesting and paper trading "
          "before live capital."),
    ("b", "Model risk: any optimiser amplifies bad inputs, so estimation error "
          "translates into real misallocation. Mitigation: independent model-risk "
          "review, challenger models and human sign-off on allocations."),
    ("b", "Suitability and fiduciary duty: allocations must match each client\u2019s "
          "mandate, risk tolerance and liquidity needs; the novelty of a quantum "
          "method is never itself a reason to deploy. Mitigation: suitability "
          "checks and explicit mandate alignment."),
    ("b", "Explainability and governance: quantum outputs are probabilistic and "
          "hard to explain to clients and regulators. Mitigation: parallel "
          "classical validation, plain-language rationale, seeded determinism "
          "and full decision logging."),
    ("b", "Operational and vendor risk: dependence on cloud-QPU availability and "
          "evolving SDKs could disrupt a scheduled rebalance. Mitigation: a "
          "classical fallback solver behind a solver-abstraction layer, plus "
          "vendor SLAs."),
])


# ----------------------------------------------------------------------
# 6. Conclusion
# ----------------------------------------------------------------------
fill_section("Conclusion", [
    ("p", f"This specification presented a working proof of concept that casts "
          f"monthly portfolio selection as a cardinality-constrained "
          f"mean-variance QUBO and solves it with QAOA. The eight-qubit circuit "
          f"(Hadamard \u2192 R_Z / R_ZZ cost layer \u2192 R_X mixer, two variational "
          f"parameters) was validated against a classical exact solver at every "
          f"rebalance, reproducing the optimum exactly (match rate "
          f"{qd['match_rate']:.2f}), and delivered the best out-of-sample "
          f"risk-adjusted performance (Sharpe "
          f"{perf['QAOA Quantum']['sharpe']:.2f}) over roughly a decade of data, "
          "ahead of a Random-Forest challenger and both passive benchmarks."),
    ("p", "The architecture is modular \u2013 only the solver call moves to quantum "
          "hardware \u2013 and extends directly to large, constraint-rich universes "
          "where classical optimisation becomes intractable and quantum "
          "advantage is expected to emerge. Near-term value lies in building a "
          "validated, scalable capability at low quantum-compute cost; the main "
          "risks (NISQ noise, trainability and the absence of a proven "
          "small-scale speed-up) are managed through error mitigation, robust "
          "estimation, reproducible seeded runs and a staged path toward "
          "fault-tolerant hardware."),
])


# ----------------------------------------------------------------------
# 7. References
# ----------------------------------------------------------------------
REFERENCES = [
    "Markowitz, H. (1952). Portfolio Selection. The Journal of Finance, "
    "7(1), 77-91.",
    "Farhi, E., Goldstone, J., & Gutmann, S. (2014). A Quantum Approximate "
    "Optimization Algorithm. arXiv:1411.4028.",
    "Preskill, J. (2018). Quantum Computing in the NISQ era and beyond. "
    "Quantum, 2, 79.",
    "Egger, D. J., et al. (2020). Quantum Computing for Finance: State-of-the-"
    "Art and Future Prospects. IEEE Transactions on Quantum Engineering, 1, 1-24.",
    "Herman, D., et al. (2023). Quantum computing for finance. Nature Reviews "
    "Physics, 5, 450-465.",
    "Ledoit, O., & Wolf, M. (2004). A well-conditioned estimator for large-"
    "dimensional covariance matrices. Journal of Multivariate Analysis, "
    "88(2), 365-411.",
    "McClean, J. R., et al. (2018). Barren plateaus in quantum neural network "
    "training landscapes. Nature Communications, 9, 4812.",
    "DeMiguel, V., Garlappi, L., & Uppal, R. (2009). Optimal Versus Naive "
    "Diversification: How Inefficient is the 1/N Portfolio Strategy? The Review "
    "of Financial Studies, 22(5), 1915-1953.",
    "Mugel, S., et al. (2022). Dynamic portfolio optimization with real "
    "datasets using quantum processors and quantum-inspired tensor networks. "
    "Physical Review Research, 4, 013006.",
    "IBM Quantum / AWS Braket pay-as-you-go pricing documentation (2024). "
    "Per-second and per-task quantum-hardware access rates.",
]

ref_heading = doc.add_paragraph("References", style="Heading 1")
for i, ref in enumerate(REFERENCES, start=1):
    doc.add_paragraph(f"[{i}]  {ref}")


doc.save(OUTPUT)
print("Saved", os.path.basename(OUTPUT))
print("Headings:", [p.text for p in doc.paragraphs if p.style.name == "Heading 1"])
print("Images embedded:", len(doc.inline_shapes))
print("Tables:", len(doc.tables))
