# Defense Script — Quantum Portfolio Optimisation (QAOA)

> **Setting:** You're defending, not pitching or examining. She listens, probes one
> question at a time, challenges vague answers, and closes with three pieces of
> feedback. She rewards **specificity, honesty, and commercial awareness**. She has
> zero patience for **jargon, oversimplification, or dodging**.
>
> **Golden rules for the room**
> - Lead with the number, then the caveat. ("9.8% a year, backtested, not guaranteed.")
> - When you don't know, say so — then say how you'd find out.
> - Never claim quantum beats classical *today at this scale*. It doesn't, and she knows it.
> - One idea per answer. Stop talking when you've answered.

---

## 1. Her opening question
> *"Tell me in one sentence what you're presenting and why it should matter to someone in my position."*

**Say:**

"I'm presenting a validated, end-to-end quantum workflow for portfolio selection —
it picks the best sub-portfolio out of a universe of assets — and it matters to you
because it's the same pipeline that will let a fund optimise huge, constraint-heavy
mandates that classical solvers can't handle, and I've already proven it produces the
mathematically optimal answer every time."

*(If she pushes for shorter:)* "It's a quantum engine that chooses the best mix of
assets, built to scale to problems classical computers choke on."

---

## 2. Why quantum works for MY specific problem

**Anchor answer:**

"My problem is: each month, pick exactly 4 of 8 ETFs to hold. Choosing B of N assets
is a *combinatorial* problem — the number of candidate portfolios is 'N choose B'. At
8 assets that's trivial, but the structure is the point. Add a realistic universe,
say 500 assets picking 30, and you get on the order of 10⁴⁸ combinations. Layer on
real constraints — sector caps, minimum lot sizes, cardinality limits, transaction
costs — and it becomes NP-hard, beyond exact classical solvers.

I formulate it as a mean-variance QUBO: minimise `q·xᵀΣx − μᵀx` subject to holding
exactly 4 assets. That maps directly onto an Ising Hamiltonian, and QAOA is
purpose-built for exactly that class of problem. Crucially, it scales with only *N*
qubits — linear in the number of assets — while the solution space grows
exponentially. That's the structural fit."

**If she says "but that's a scaling argument, not a today argument" —**

"Correct, and I want to be honest about that: at 8 qubits classical wins outright.
The value *today* is a correct, validated pipeline. The value *tomorrow* is that this
exact architecture extends into the regime where classical breaks."

---

## 3. What it costs

**Anchor answer:**

"Three cost buckets. First, quantum compute — negligible. Each monthly rebalance is a
seconds-long job; premium cloud QPU time is quoted around US$1.60 per second, so
you're talking a handful of dollars a month, and the simulator is effectively free at
this scale. Second — and this is the real cost — people and integration: quant
researchers plus quantum-software engineers to build, validate, and wire the solver
into existing systems. That's a moderate one-off. Third, talent and training, because
quantum-finance skills are genuinely scarce.

So the honest picture: the dominant near-term cost is *headcount, not hardware*."

**If she asks for a real number —**

"I don't have a firm figure — it depends on team size and integration depth, and I'd
be guessing if I gave you one. What I can defend is the *shape*: compute is trivial,
the investment is a small specialist team over roughly a year to build a reusable,
validated pipeline."

---

## 4. The benefit (commercial awareness)

**Anchor answer:**

"In the backtest — 82 out-of-sample months, walk-forward, no look-ahead — the quantum
strategy earned 9.8% a year at 11.3% volatility, a Sharpe of 0.69. That beat the
classical ML challenger at 0.46, static 60/40 at 0.52, and equal-weight at 0.51. It
had the best risk-adjusted return of all four.

To translate that: a one-percentage-point improvement on a US$1bn mandate is on the
order of US$10m of additional annual return. That's illustrative and backtested — not
guaranteed — but it's the order of magnitude that makes a specialist team pay for
itself."

**If she challenges the outperformance —**

"Fair challenge. At 8 assets I would *not* claim quantum caused that edge — a
classical solver on the same QUBO gets the identical portfolio. The outperformance
comes from the mean-variance *formulation*, not from quantum hardware. What quantum
buys me is the ability to run that same formulation when the problem gets too big for
classical exact methods."

---

## 5. What risks could cause this to fail

**Anchor answer — pick the top three, don't recite all eight:**

"The three that keep me honest:

First, **NISQ noise**. Real hardware today has two-qubit gate errors around 10⁻³ and
readout errors around 10⁻². My proof-of-concept runs on a noiseless simulator, so my
results are exact — but on real hardware they'd degrade. Near term, error mitigation
handles a shallow 8-qubit circuit; long term you need error correction, which costs
roughly 1000 physical qubits per logical qubit.

Second, **no proven advantage at small scale**. I've said it twice because it's true —
the near-term case is strategic capability-building, not a compute speed-up.

Third, **model risk**. The μ and Σ I estimate from history are noisy, and *any*
optimiser — quantum or classical — amplifies bad inputs. I mitigate with covariance
shrinkage and strict walk-forward testing, but garbage in, garbage out remains the
real-world killer."

**If she asks "which single risk is most likely to kill it?" —**

"Commercially? That fault-tolerant hardware arrives slower than expected, so the
scaling payoff stays perpetually 'five years away.' That's why I'd frame any
investment as capability-building with staged go/no-go gates, not a bet on a delivery
date."

---

## 6. The hardest part to defend (say this BEFORE she finds it)

If there's a lull, get ahead of it — she rewards this:

"The hardest thing for me to defend is this: at 8 qubits, my project proves the
workflow is *correct*, but it does not prove quantum is *better* — because at this
scale it isn't. A classical solver reproduces my exact answer instantly. So I'm not
going to pretend I've demonstrated quantum advantage. What I've demonstrated is a
validated, scalable pipeline and a clear-eyed view of when it starts to matter. I'd
rather be honest about that than oversell it."

---

## Likely probing questions & crisp answers

**Q: "You said match rate 1.0 — isn't that just proving quantum equals classical, so why bother?"**
"Exactly right at this scale — that's validation, not advantage. It proves my QUBO
mapping, circuit, and optimisation loop are correct. You need that proof *before* you
scale to where classical can't follow. Think of it as the unit test, not the product."

**Q: "When does this actually beat classical?"**
"Honestly, I can't give you a date — it depends on hardware maturity and on quantum
algorithms provably beating the best classical heuristics, which isn't settled. The
credible window is large, constraint-rich universes on fault-tolerant hardware. I'd
invest to be *ready*, not because it's ready today."

**Q: "Why should I fund this instead of a better classical optimiser?"**
"You might fund both — I would. The classical optimiser is your workhorse now. This is
an option on a structural shift: if quantum matures, the firms with a validated
pipeline and in-house skills move first. It's cheap insurance against being late."

**Q: "What's your data? Could you be overfitting?"**
"Ten years of monthly ETF data, eight ETFs across the major asset classes, 82
out-of-sample months. I use a 36-month trailing window and rebalance quarterly with no
look-ahead. But yes — 82 months is a short sample and one asset universe, so I'd treat
the outperformance as suggestive, not proven. I'd want multiple universes and regimes
before I banked on it."

**Q: "What don't you know?"**
"Three things: the real integration cost at production scale, the exact crossover point
where quantum overtakes classical, and how the strategy behaves in a regime my 82
months didn't contain — like a 2008. I'd rather flag those than paper over them."

---

## Closing posture

If she asks "why should I move forward?":

"Because the downside is bounded — a small specialist team and near-zero compute cost —
and the upside is being first-mover-ready in an area that becomes decisive if the
hardware delivers. I'm not asking you to bet the firm. I'm asking you to build a
validated option, with staged checkpoints, so you're not scrambling to catch up later.
And I've been straight with you about exactly where the limits are today."

---

### One-line reminders to keep in your head
- **Number first, caveat second.**
- **"Backtested, not guaranteed."**
- **"Validation today, advantage at scale."**
- **The outperformance is the *formulation*, not the hardware.**
- **When you don't know: say so, then say how you'd find out.**
