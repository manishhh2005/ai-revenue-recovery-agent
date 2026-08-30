import csv
import random
from datetime import datetime, timedelta

random.seed(42)

failure_reasons = [
    ("insufficient_funds", "soft_decline", 0.55),
    ("expired_card", "hard_decline", 0.15),
    ("bank_server_error", "soft_decline", 0.60),
    ("card_reported_stolen", "hard_decline", 0.0),
    ("mandate_expired", "hard_decline", 0.10),
    ("wrong_otp", "soft_decline", 0.40),
    ("account_closed", "hard_decline", 0.0),
    ("issuer_declined_generic", "soft_decline", 0.35),
    ("network_timeout", "soft_decline", 0.70),
    ("daily_limit_exceeded", "soft_decline", 0.50),
]

payment_methods = ["UPI", "Credit Card", "Debit Card", "Netbanking", "Wallet"]
plan_names = ["Basic Monthly", "Pro Monthly", "Pro Annual", "Team Monthly", "Premium Monthly"]

rows = []
start_date = datetime(2026, 7, 1)

for i in range(1, 91):
    reason, decline_type, recover_prob = random.choice(failure_reasons)
    customer_id = f"CUST{1000+i}"
    amount = random.choice([199, 299, 499, 999, 1499, 2999, 4999, 9999])
    method = random.choice(payment_methods)
    plan = random.choice(plan_names)
    fail_date = start_date + timedelta(days=random.randint(0, 55))
    retry_count = random.randint(0, 2)
    days_since_signup = random.randint(5, 400)

    rows.append({
        "case_id": f"CASE{i:04d}",
        "customer_id": customer_id,
        "plan_name": plan,
        "amount_inr": amount,
        "payment_method": method,
        "failure_reason": reason,
        "decline_type": decline_type,
        "failure_date": fail_date.strftime("%Y-%m-%d"),
        "prior_retry_count": retry_count,
        "days_since_signup": days_since_signup,
        "_true_recover_prob": recover_prob,  # hidden ground truth for simulating outcomes later
    })

with open("../data/failed_payments_dataset.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows")
print("Failure reason distribution:")
from collections import Counter
c = Counter(r["failure_reason"] for r in rows)
for k, v in c.items():
    print(f"  {k}: {v}")
