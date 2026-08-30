# Recovery Ledger — AI Revenue Recovery Agent
Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery

## What it does

An agent that takes a batch of failed subscription payments, diagnoses the
root cause of each failure, decides on a bounded recovery action, executes
it (simulated, since this runs on synthetic test data), and logs a full
audit trail of what it did and why — including every time its own safety
rules overrode the model's suggestion. A baseline comparison quantifies how
much better this targeted approach is than blindly retrying everything.

## Repo structure

```
recovery-ledger/
├── README.md
├── requirements.txt
├── scripts/
│   ├── gen_data.py             # synthetic data generator
│   ├── diagnose.py             # LLM reasoning step
│   ├── decide_act.py           # bounded decision + stopping rules
│   ├── simulate_outcomes.py    # outcome simulation + audit trail
│   └── baseline_comparison.py  # agent vs. naive-retry-everything
├── dashboard/
│   └── recovery_dashboard.html # visualizes everything below
└── data/
    ├── failed_payments_dataset.csv
    ├── diagnosed_cases.csv
    ├── decided_actions.csv
    ├── audit_trail.csv
    ├── summary.json
    └── baseline_comparison.json
```

## Architecture

```
 data/failed_payments_dataset.csv
              │
              ▼
   scripts/diagnose.py         Claude API call per case:
   (LLM reasoning)              root cause + is it recoverable?
              │
              ▼  data/diagnosed_cases.csv
   scripts/decide_act.py       hard-coded safety rules override
   (bounded action)             the LLM's suggestion when needed
              │
              ▼  data/decided_actions.csv
   scripts/simulate_outcomes.py  simulates success/failure per
   (evaluation)                   action, builds audit trail + summary
              │
              ▼  data/audit_trail.csv + data/summary.json
   scripts/baseline_comparison.py  quantifies the value of targeted
   (counterfactual)                 diagnosis vs. blind retries
              │
              ▼  data/baseline_comparison.json
   dashboard/recovery_dashboard.html   (visualization)
```

## Why the decide+act step is separate from diagnosis

The LLM is good at reasoning about *why* a payment failed, but it shouldn't
be the last word on *whether to act*. `decide_act.py` applies deterministic,
auditable rules on top of the LLM's suggestion — and these aren't arbitrary
numbers, they're grounded in real NPCI/RBI recurring-payment rules:

1. **Never act further on an unrecoverable case** (stolen card, closed
   account), even if the model somehow suggests otherwise.
2. **Never retry more than 3 times.** As of August 2025, NPCI limits UPI
   AutoPay mandates to one original execution attempt plus a maximum of
   three retries per cycle — after that, the payment is marked failed and
   must be escalated (to the customer or to a human), not retried further.
   `MAX_RETRIES = 3` mirrors this network-level constraint rather than
   being an invented threshold.
3. **Never fire two immediate retries back-to-back on the same
   instrument.** RBI/NPCI guidance expects retries to be spaced out (e.g.
   roughly 24 hours, then 72 hours, then around day 7) rather than
   attempted in rapid succession — firing all retries immediately looks
   like spamming the payment rails and works against the network's intent.
   Our "anti-hammering" rule enforces this by forcing a delay
   (`retry_in_3_days`) whenever the LLM suggests an immediate retry on a
   case that's already been retried once.

In our test batch of 90 cases, **11 of them had a stopping rule override
the LLM's raw suggestion.** This is also what "compliant escalation" means
in practice for this project: escalation happens only after the
NPCI-aligned retry ceiling is hit, never before, and never on cases that
are provably unrecoverable.

## Does targeted diagnosis actually help?

`baseline_comparison.py` answers this directly by computing the **expected
value** (amount × recovery probability, not a single random draw — kept
deterministic and reproducible on purpose) for two policies over the same
90 cases:

| | Naive: retry everything | Agent: diagnose + route + bound |
|---|---|---|
| Recovered (expected) | ₹66,893 | **₹78,979** |
| Attempts made | 90 | **67** |
| Unsafe retries (stolen/closed accounts) | 23 | **0** |

Targeted diagnosis recovers **₹12,086 more**, with **23 fewer attempts**,
and **zero** blind retries on cases that were never recoverable in the
first place.

## What broke during development (and how we fixed it)

**1. LLM responses aren't always clean JSON.**
Early on, `diagnose.py` called `json.loads()` directly on the model's
response text. Real models sometimes wrap JSON in markdown code fences
(` ```json ... ``` `), which breaks a naive parse. Fix: strip code fences
before parsing. We also stress-tested a harder failure mode — a response
with a trailing comma, which is invalid JSON and *will* throw regardless of
fence-stripping. Rather than trying to patch every possible malformed-JSON
shape, we wrapped the whole diagnosis call in a try/except that falls back
to a safe default: `root_cause_category: "error"`, `is_recoverable: False`,
`recommended_action: "escalate_human"`.

**2. That fallback needed to survive the *next* stage too, not just get logged.**
It's not enough for `diagnose.py` to catch the error — we had to confirm
`decide_act.py`'s stopping rules treat an "error" diagnosis the same as an
"unrecoverable" one, so a failed API call safely falls through to
`stop_no_action` instead of the agent taking a blind action on a case it
couldn't actually reason about. We tested this explicitly by injecting a
simulated JSON-parsing failure and confirming the case correctly reached
`stop_no_action` rather than crashing or defaulting to a retry.

**3. No API key during early development.**
We built and tested the full pipeline shape before wiring in real API calls,
using a rule-based fallback (`diagnose_with_rules`) that mirrors the same
prompt logic. This let us validate the downstream decide/simulate/audit
stages independently of API access.

## Running it

```bash
pip install -r requirements.txt

cd scripts

# without a key: runs end-to-end using rule-based fallback diagnosis
python3 gen_data.py
python3 diagnose.py
python3 decide_act.py
python3 simulate_outcomes.py
python3 baseline_comparison.py

# with a real key: diagnosis step uses actual Claude reasoning
export ANTHROPIC_API_KEY=sk-ant-...
python3 diagnose.py
python3 decide_act.py
python3 simulate_outcomes.py
python3 baseline_comparison.py
```

Then open `dashboard/recovery_dashboard.html` in a browser to view the
results.

## Honest limitations

- This is a **batch, offline simulation** on synthetic data, not a live
  integration with Razorpay's payment APIs or a real notification/retry
  system.
- Outcome simulation and the baseline comparison use a hidden ground-truth
  recovery probability baked into the synthetic dataset — they test whether
  the agent's *decisions* track realistic recoverability, not real-world
  payment success.
- The rule-based fallback in `diagnose.py` exists only for offline testing
  without an API key — the real submission's reasoning comes from the
  Claude API call.

## Regulatory context for the stopping rules

- NPCI's UPI AutoPay retry limit (max 3 retries per cycle after the
  original attempt), effective August 2025.
- RBI's Digital Payments E-Mandate Framework, 2026 — governs pre-debit
  notifications, mandate validity, and revocation for recurring
  transactions on cards, UPI, and PPIs.

These are cited for design rationale, not as a legal compliance claim —
always verify current rules against RBI/NPCI's official circulars before
using this logic in production.
