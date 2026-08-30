# Recovery Ledger

> AI-powered revenue recovery agent for Razorpay AI Buildathon — Track 03: AI Revenue Recovery.

## Overview

**Recovery Ledger** is an AI-driven payment recovery system designed to diagnose failed payments, select a bounded recovery action, execute the simulated intervention, and maintain an auditable record of every decision.

The project is designed around the Track 03 agent loop:

**Detect → Diagnose → Decide → Act → Recover → Escalate**

The goal is not to blindly retry failed payments. Instead, the system uses payment context and diagnosed failure reasons to choose an appropriate recovery strategy while applying explicit safety and stopping rules.

## Key Features

- **Failed-payment detection** — identifies payments that require recovery.
- **AI diagnosis** — analyzes why a payment failed, such as timing issues, payment-method problems, or other recoverable conditions.
- **Bounded decision-making** — maps diagnoses to predefined recovery actions rather than allowing unrestricted agent behavior.
- **Recovery simulation** — evaluates the outcome of selected interventions.
- **Escalation handling** — cases that cannot be safely recovered are flagged instead of being repeatedly retried.
- **Audit trail** — records the diagnosis, selected action, outcome, and relevant reasoning for each case.
- **Baseline comparison** — compares the agentic recovery strategy with a simpler/blind retry baseline.
- **Dashboard** — provides a visual way to inspect recovery performance and individual cases.

## Architecture

```text
                    ┌─────────────────────┐
                    │ Failed Payments     │
                    │ Dataset             │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Detect Failed       │
                    │ Payments             │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ AI Diagnosis        │
                    │ "Why did it fail?"  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Decide Recovery     │
                    │ Action              │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
        ┌──────────────────┐       ┌──────────────────┐
        │ Safe Recovery    │       │ Escalate / Stop  │
        │ Action           │       │                  │
        └────────┬─────────┘       └────────┬─────────┘
                 │                          │
                 └────────────┬─────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Simulate Outcome    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Audit Trail +       │
                    │ Metrics             │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Recovery Dashboard  │
                    └─────────────────────┘
```

## Agent Workflow

### 1. Detect

The system identifies failed or at-risk payments from the input dataset.

### 2. Diagnose

Each case is analyzed to determine the likely reason for failure. The diagnosis is used as decision context rather than treating every failed payment identically.

### 3. Decide

The agent selects a recovery action from a bounded set of allowed interventions.

This is intentionally constrained: the AI should recommend or select an action within predefined business and safety rules.

### 4. Act

The selected action is passed to the recovery simulator, which models whether the intervention succeeds.

### 5. Recover

Successful interventions contribute to the total recovered amount and recovery metrics.

### 6. Escalate / Stop

If a case cannot be safely or confidently recovered, the system records it as an exception instead of performing unlimited retries.

## Project Structure

```text
recovery-ledger/
├── README.md
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── gen_data.py
│   ├── diagnose.py
│   ├── decide_act.py
│   ├── simulate_outcomes.py
│   └── baseline_comparison.py
├── dashboard/
│   └── recovery_dashboard.html
└── data/
    ├── failed_payments_dataset.csv
    ├── diagnosed_cases.csv
    ├── decided_actions.csv
    ├── audit_trail.csv
    ├── summary.json
    └── baseline_comparison.json
```

## Scripts

| Script | Purpose |
|---|---|
| `gen_data.py` | Generates the synthetic failed-payment dataset |
| `diagnose.py` | Diagnoses failed-payment cases |
| `decide_act.py` | Selects bounded recovery actions |
| `simulate_outcomes.py` | Simulates recovery outcomes |
| `baseline_comparison.py` | Compares the agent against the baseline strategy |

## Data Flow

```text
failed_payments_dataset.csv
              │
              ▼
     diagnosed_cases.csv
              │
              ▼
      decided_actions.csv
              │
              ▼
        audit_trail.csv
              │
       ┌──────┴──────┐
       ▼             ▼
  summary.json   baseline_comparison.json
       │
       ▼
recovery_dashboard.html
```

## Evaluation

The project should be evaluated using measurable outcomes rather than only the visual quality of the demo.

Important metrics include:

- **Total amount recovered (₹)**
- **Recovery rate**
- **Successful recovery count**
- **Failure / exception count**
- **Action-level success rate**
- **Comparison against blind retries**
- **Auditability of decisions**
- **Safe stopping / escalation behavior**

A key comparison is:

```text
Agentic Recovery
       vs.
Blind Retry Baseline
```

The objective is to demonstrate that diagnosis-driven, bounded interventions can recover more value than indiscriminate retries while maintaining transparent exception handling.

## Safety & Guardrails

The recovery agent is deliberately bounded.

### Guardrail principles

1. The agent cannot invent arbitrary recovery actions.
2. Recovery actions should come from an explicit allowed-action set.
3. Failed or uncertain cases should be escalated or stopped.
4. Every decision should be recorded in the audit trail.
5. Performance claims should be calculated from the complete evaluation dataset, not selected examples.
6. The system should expose failures and exceptions honestly.

## Dashboard

The dashboard is intended to make the agent's performance easy to understand during the buildathon demo.

Recommended views include:

- Total payments analyzed
- Total amount at risk
- Total amount recovered
- Recovery rate
- Agent vs. baseline performance
- Recovery actions selected
- Successful vs. failed interventions
- Exception cases
- Individual case audit trail

## Running the Project

Create and activate a Python environment, then install the dependencies:

```bash
pip install -r requirements.txt
```

Generate the synthetic data:

```bash
python scripts/gen_data.py
```

Run diagnosis:

```bash
python scripts/diagnose.py
```

Select recovery actions:

```bash
python scripts/decide_act.py
```

Simulate recovery outcomes:

```bash
python scripts/simulate_outcomes.py
```

Run the baseline comparison:

```bash
python scripts/baseline_comparison.py
```

Then open:

```text
dashboard/recovery_dashboard.html
```

> Adjust the commands above if the final implementation uses a different entry point or dependency setup.

## Buildathon Context

This project is intended for the **Razorpay AI Buildathon — Track 03: AI Revenue Recovery**.

The project focuses on an end-to-end agent loop rather than a simple chatbot:

```text
Detect
  ↓
Diagnose
  ↓
Choose intervention
  ↓
Execute
  ↓
Measure recovery
  ↓
Escalate / stop when required
```

The central pitch is:

> **Recover more payment value with explainable, bounded AI actions instead of blind retries.**

## Repository

Recommended GitHub repository name:

```text
recovery-ledger
```

Suggested GitHub description:

> AI agent that diagnoses failed payments, decides a bounded recovery action, and recovers more than blind retries — Razorpay AI Buildathon Track 03.

## GitHub Setup

```bash
git init
git add .
git commit -m "AI Revenue Recovery agent — Razorpay Buildathon Track 03"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/recovery-ledger.git
git push -u origin main
```

Make the repository **public** if required by the buildathon submission rules.

## Disclaimer

This repository is a buildathon prototype using synthetic/simulated payment data. It is not intended to process real customer payment information or execute real financial transactions.
