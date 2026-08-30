"""
Step 2: Diagnose step for the AI Revenue Recovery agent.

For each failed payment, ask an LLM (Claude) to:
  1. Identify the likely root cause category
  2. Judge whether it's recoverable
  3. Suggest how soon to retry (if at all)
  4. Give a one-line reasoning (for the audit trail)

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 diagnose.py

If no ANTHROPIC_API_KEY is set, falls back to a simple rule-based
diagnosis so you can see the pipeline shape end-to-end without a key.
Swap in the real API call for your actual submission.
"""

import csv
import json
import os
import time

INPUT_CSV = "../data/failed_payments_dataset.csv"
OUTPUT_CSV = "../data/diagnosed_cases.csv"

USE_REAL_API = bool(os.environ.get("ANTHROPIC_API_KEY"))

if USE_REAL_API:
    import anthropic
    client = anthropic.Anthropic()

DIAGNOSIS_SYSTEM_PROMPT = """You are a payments recovery analyst. Given details of a \
failed subscription payment, classify it and respond with ONLY a JSON object, no other text.

JSON shape:
{
  "root_cause_category": one of ["temporary_bank_issue", "expired_or_invalid_instrument", "user_action_needed", "unrecoverable"],
  "is_recoverable": true or false,
  "recommended_action": one of ["retry_now", "retry_in_3_days", "send_reminder_update_method", "escalate_human", "stop_no_action"],
  "confidence": a number from 0 to 1,
  "reasoning": a short one-sentence explanation
}

Rules of thumb:
- card_reported_stolen, account_closed -> unrecoverable, stop_no_action
- expired_card, mandate_expired -> expired_or_invalid_instrument, send_reminder_update_method
- insufficient_funds, daily_limit_exceeded -> user_action_needed, retry_in_3_days
- network_timeout, bank_server_error, issuer_declined_generic -> temporary_bank_issue, retry_now
- wrong_otp -> user_action_needed, retry_now (if first attempt) else send_reminder_update_method
"""


def diagnose_with_api(case: dict) -> dict:
    user_prompt = f"""Failed payment case:
- Amount: INR {case['amount_inr']}
- Payment method: {case['payment_method']}
- Failure reason code: {case['failure_reason']}
- Decline type: {case['decline_type']}
- Prior retry count: {case['prior_retry_count']}
- Days since signup: {case['days_since_signup']}
- Plan: {case['plan_name']}
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system=DIAGNOSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text.strip()
    # Strip accidental code fences
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def diagnose_with_rules(case: dict) -> dict:
    """Fallback used only when no API key is set, so the pipeline is runnable end to end."""
    reason = case["failure_reason"]
    retries = int(case["prior_retry_count"])

    table = {
        "card_reported_stolen": ("unrecoverable", False, "stop_no_action",
                                  "Card reported stolen; no legitimate retry path."),
        "account_closed": ("unrecoverable", False, "stop_no_action",
                            "Account closed; nothing to recover."),
        "expired_card": ("expired_or_invalid_instrument", True, "send_reminder_update_method",
                          "Card has expired; customer needs to update payment method."),
        "mandate_expired": ("expired_or_invalid_instrument", True, "send_reminder_update_method",
                             "UPI mandate expired; needs re-authorization."),
        "insufficient_funds": ("user_action_needed", True, "retry_in_3_days",
                                "Likely temporary cash-flow issue; wait before retrying."),
        "daily_limit_exceeded": ("user_action_needed", True, "retry_in_3_days",
                                  "Daily transaction limit hit; retry after reset."),
        "network_timeout": ("temporary_bank_issue", True, "retry_now",
                             "Transient network error; safe to retry immediately."),
        "bank_server_error": ("temporary_bank_issue", True, "retry_now",
                               "Bank-side server error; safe to retry immediately."),
        "issuer_declined_generic": ("temporary_bank_issue", True, "retry_now",
                                     "Generic issuer decline; often resolves on retry."),
        "wrong_otp": ("user_action_needed", True,
                       "retry_now" if retries == 0 else "send_reminder_update_method",
                       "OTP entry issue; retry once, then prompt customer."),
    }
    category, recoverable, action, reasoning = table.get(
        reason, ("unrecoverable", False, "escalate_human", "Unknown failure reason; escalate.")
    )
    return {
        "root_cause_category": category,
        "is_recoverable": recoverable,
        "recommended_action": action,
        "confidence": 0.9,
        "reasoning": reasoning,
    }


def main():
    with open(INPUT_CSV, newline="") as f:
        cases = list(csv.DictReader(f))

    results = []
    for i, case in enumerate(cases, 1):
        try:
            if USE_REAL_API:
                diagnosis = diagnose_with_api(case)
                time.sleep(0.2)  # gentle on rate limits
            else:
                diagnosis = diagnose_with_rules(case)
        except Exception as e:
            diagnosis = {
                "root_cause_category": "error",
                "is_recoverable": False,
                "recommended_action": "escalate_human",
                "confidence": 0.0,
                "reasoning": f"Diagnosis failed: {e}",
            }

        merged = {**case, **diagnosis}
        results.append(merged)
        print(f"[{i}/{len(cases)}] {case['case_id']} ({case['failure_reason']}) "
              f"-> {diagnosis['root_cause_category']} / {diagnosis['recommended_action']}")

    fieldnames = list(results[0].keys())
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nMode used: {'REAL Claude API' if USE_REAL_API else 'rule-based fallback (no API key set)'}")
    print(f"Wrote {len(results)} diagnosed cases to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
