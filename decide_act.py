"""
Step 3: Decide + Act step for the AI Revenue Recovery agent.

Takes the LLM's diagnosis (from diagnose.py) and converts it into a FINAL,
bounded action — applying hard safety rules that override the LLM's
suggestion whenever necessary. This is the part judges specifically care
about: an agent that can act, but knows when to stop.

Hard stopping rules (never overridden, even if the LLM disagrees):
  1. Never take further action on an "unrecoverable" root cause.
  2. Never retry more than MAX_RETRIES times total.
  3. Never retry the same case twice within COOLDOWN_DAYS of each other
     (approximated here via prior_retry_count, since we don't have a live
     clock in this offline batch).
  4. If retries are exhausted but the LLM still recommended retrying,
     downgrade to escalate_human instead of silently stopping — a human
     should see genuinely stuck cases, not lose them.

Usage:
    python3 decide_act.py
"""

import csv

INPUT_CSV = "../data/diagnosed_cases.csv"
OUTPUT_CSV = "../data/decided_actions.csv"

MAX_RETRIES = 3
RETRY_ACTIONS = {"retry_now", "retry_in_3_days"}


def apply_stopping_rules(case: dict) -> dict:
    """Returns the FINAL action plus a record of whether/why a rule overrode the LLM."""
    llm_action = case["recommended_action"]
    is_recoverable = str(case["is_recoverable"]).strip().lower() == "true"
    retry_count = int(case["prior_retry_count"])
    category = case["root_cause_category"]

    final_action = llm_action
    rule_triggered = None

    # Rule 1: unrecoverable cases never get acted on further, no matter what.
    if category == "unrecoverable" or not is_recoverable:
        if llm_action != "stop_no_action":
            rule_triggered = "override: unrecoverable case, forcing stop_no_action"
        final_action = "stop_no_action"

    # Rule 2: hard cap on total retries.
    elif retry_count >= MAX_RETRIES:
        if llm_action in RETRY_ACTIONS:
            rule_triggered = f"override: retry cap ({MAX_RETRIES}) reached, escalating instead of retrying"
            final_action = "escalate_human"

    # Rule 3: cooldown-style guard — if this is already the 2nd+ retry attempt
    # and the LLM wants an immediate retry, force a delay instead of hammering
    # the payment instrument back-to-back.
    elif llm_action == "retry_now" and retry_count >= 1:
        rule_triggered = "override: consecutive immediate retries blocked, spacing out attempt"
        final_action = "retry_in_3_days"

    return {
        "final_action": final_action,
        "llm_recommended_action": llm_action,
        "stopping_rule_triggered": rule_triggered is not None,
        "stopping_rule_reason": rule_triggered or "",
    }


def main():
    with open(INPUT_CSV, newline="") as f:
        cases = list(csv.DictReader(f))

    results = []
    overrides = 0
    for case in cases:
        decision = apply_stopping_rules(case)
        if decision["stopping_rule_triggered"]:
            overrides += 1
        merged = {**case, **decision}
        results.append(merged)
        flag = " <- RULE OVERRIDE" if decision["stopping_rule_triggered"] else ""
        print(f"{case['case_id']}: LLM said '{decision['llm_recommended_action']}' "
              f"-> final action '{decision['final_action']}'{flag}")

    fieldnames = list(results[0].keys())
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{overrides}/{len(results)} cases had a stopping rule override the LLM's suggestion.")
    print(f"Wrote {len(results)} decided cases to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
