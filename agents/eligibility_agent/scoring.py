### agents/eligibility/scoring.py
def score_eligibility(income, credit_score, emi_pct, avg_balance, overdrafts, itr_years):
    criteria = []

    # Income Stability
    s = 10 if income >= 50000 else 7 if income >= 25000 else 4
    criteria.append({"name": "Income Stability", "score": s, "weight": 25, "comments": f"Income: ₹{income}"})

    # Credit History
    s = 10 if credit_score >= 750 else 7 if credit_score >= 650 else 4
    criteria.append({"name": "Credit History", "score": s, "weight": 30, "comments": f"Score: {credit_score}"})

    # EMI/Income Ratio
    s = 10 if emi_pct < 30 else 7 if emi_pct <= 50 else 4
    criteria.append({"name": "EMI-to-Income Ratio", "score": s, "weight": 20, "comments": f"EMI: {emi_pct}%"})

    # Banking Hygiene
    s = 10 if avg_balance >= 20000 and overdrafts == 0 else 7 if overdrafts <= 1 else 4
    criteria.append({"name": "Banking Hygiene", "score": s, "weight": 15, "comments": f"Avg: ₹{avg_balance}, overdrafts: {overdrafts}"})

    # ITR Filing
    s = 10 if itr_years == 3 else 7 if itr_years == 2 else 4
    criteria.append({"name": "Tax Filing Consistency", "score": s, "weight": 10, "comments": f"Years filed: {itr_years}"})

    total_score = sum(c["score"] * c["weight"] / 100 for c in criteria)
    decision = "Yes" if total_score >= 8.5 else "Needs Review" if total_score >= 7.0 else "No"

    return {
        "decision": decision,
        "confidence_score": round(total_score, 1),
        "criteria": criteria,
    }
