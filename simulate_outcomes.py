"""
Step 4: Simulate outcomes + build the audit trail for the AI Revenue Recovery agent.

Since we're working with synthetic test-mode data, we can't actually charge
real cards. Instead we simulate whether each action "succeeds" using the
hidden ground-truth recovery probability (_true_recover_prob) that was
baked into the dataset in step 1 — the agent itself never sees this column,
only the simulator does, to keep it an honest test rather than a rigged one.

Outputs:
  - audit_trail.csv: one row per case with the full decision + outcome trail
  - summary.json: the headline numbers for your dashboard/pitch

Usage:
    python3 simulate_outcomes.py
"""

import csv
import json
import random
from collections import defaultdict

random.seed(7)  # reproducible simulation for consistent demo numbers

INPUT_CSV = "../data/decided_actions.csv"
AUDIT_CSV = "../data/audit_trail.csv"
SUMMARY_JSON = "../data/summary.json"

# Actions that represent a genuine attempt to recover money right now.
ACTIVE_RECOVERY_ACTIONS = {"retry_now", "retry_in_3_days", "send_reminder_update_method"}
# Actions that are explicitly NOT an attempt (safety stops or handoffs).
NO_ATTEMPT_ACTIONS = {"stop_no_action", "escalate_human"}


def simulate_case_outcome(case: dict) -> dict:
    action = case["final_action"]
    amount = float(case["amount_inr"])
    true_prob = float(case["_true_recover_prob"])

    if action in NO_ATTEMPT_ACTIONS:
        # No money movement attempted. escalate_human is "pending", not a
        # loss — but for this batch's numbers we count it as not-yet-recovered.
        return {
            "attempted": False,
            "outcome": "pending_human_review" if action == "escalate_human" else "no_action_taken",
            "recovered_amount": 0.0,
        }

    # For active recovery actions, roll against the true recovery probability.
    # send_reminder_update_method gets a slightly different (usually higher)
    # effective chance since it fixes the root problem rather than just retrying.
    effective_prob = true_prob
    if action == "send_reminder_update_method":
        effective_prob = min(true_prob + 0.15, 0.85)

    success = random.random() < effective_prob
    return {
        "attempted": True,
        "outcome": "recovered" if success else "attempt_failed",
        "recovered_amount": amount if success else 0.0,
    }


def main():
    with open(INPUT_CSV, newline="") as f:
        cases = list(csv.DictReader(f))

    audit_rows = []
    total_at_risk = 0.0
    total_recovered = 0.0
    by_reason = defaultdict(lambda: {"count": 0, "at_risk": 0.0, "recovered": 0.0})

    for case in cases:
        amount = float(case["amount_inr"])
        total_at_risk += amount

        sim = simulate_case_outcome(case)
        total_recovered += sim["recovered_amount"]

        reason = case["failure_reason"]
        by_reason[reason]["count"] += 1
        by_reason[reason]["at_risk"] += amount
        by_reason[reason]["recovered"] += sim["recovered_amount"]

        audit_rows.append({
            "case_id": case["case_id"],
            "customer_id": case["customer_id"],
            "amount_inr": amount,
            "failure_reason": case["failure_reason"],
            "root_cause_category": case["root_cause_category"],
            "llm_recommended_action": case["llm_recommended_action"],
            "final_action": case["final_action"],
            "stopping_rule_triggered": case["stopping_rule_triggered"],
            "stopping_rule_reason": case["stopping_rule_reason"],
            "diagnosis_reasoning": case["reasoning"],
            "outcome": sim["outcome"],
            "recovered_amount_inr": sim["recovered_amount"],
        })

    with open(AUDIT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        writer.writeheader()
        writer.writerows(audit_rows)

    recovery_rate_by_reason = {
        reason: {
            "count": stats["count"],
            "at_risk_inr": round(stats["at_risk"], 2),
            "recovered_inr": round(stats["recovered"], 2),
            "recovery_rate_pct": round(100 * stats["recovered"] / stats["at_risk"], 1) if stats["at_risk"] else 0.0,
        }
        for reason, stats in sorted(by_reason.items())
    }

    outcome_counts = defaultdict(int)
    for row in audit_rows:
        outcome_counts[row["outcome"]] += 1

    summary = {
        "total_cases": len(cases),
        "total_at_risk_inr": round(total_at_risk, 2),
        "total_recovered_inr": round(total_recovered, 2),
        "overall_recovery_rate_pct": round(100 * total_recovered / total_at_risk, 1) if total_at_risk else 0.0,
        "outcome_breakdown": dict(outcome_counts),
        "recovery_by_failure_reason": recovery_rate_by_reason,
        "stopping_rule_overrides": sum(1 for c in cases if str(c["stopping_rule_triggered"]).lower() == "true"),
    }

    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nWrote audit trail to {AUDIT_CSV}")
    print(f"Wrote summary to {SUMMARY_JSON}")


if __name__ == "__main__":
    main()
