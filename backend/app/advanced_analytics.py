# backend/app/advanced_analytics.py
"""
Advanced analytics endpoints — compute real analytics from transactions in MongoDB.

Produces JSON with:
{
  "risk_assessment": { ... },
  "predictions": { ... },
  "weekly_insights": { ... }
}

This file expects your existing db module to expose `get_db()` which returns a pymongo database instance.
"""

from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import List, Dict, Any
import math

from .db import get_db

def _to_month_key(dt: datetime):
    return dt.year, dt.month

def _safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def compute_basic_aggregates(transactions: List[Dict[str, Any]]):
    """
    Compute per-month income/expense totals, overall totals and per-category sums.
    Returns dict with monthly series and aggregates.
    
    IMPORTANT: Detects and excludes ONE-TIME OUTLIER EXPENSES (> 10x median)
    to provide accurate risk assessment.
    """
    # ensure dates are datetime
    for tx in transactions:
        if isinstance(tx.get("date"), str):
            try:
                tx["date"] = datetime.fromisoformat(tx["date"])
            except Exception:
                try:
                    tx["date"] = datetime.strptime(tx["date"], "%Y-%m-%d")
                except Exception:
                    tx["date"] = None

    # 🔥 FIX: Identify outlier expenses for one-time purchases
    expense_amounts = [
        _safe_float(tx.get("amount", 0)) 
        for tx in transactions 
        if (tx.get("type") or "").lower() == "expense"
    ]
    
    outlier_amounts = set()
    if expense_amounts and len(expense_amounts) > 2:
        median_expense = sorted(expense_amounts)[len(expense_amounts) // 2]
        outlier_threshold = max(median_expense * 10, 50000)  # 10x median or ₹50k minimum
        outlier_amounts = {amt for amt in expense_amounts if amt > outlier_threshold}
    
    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "outlier_expense": 0.0})
    categories = defaultdict(float)
    total_income = 0.0
    total_expense = 0.0
    total_outlier_expense = 0.0  # Track one-time purchases separately
    amounts = []

    for tx in transactions:
        ttype = (tx.get("type") or "").lower()
        amount = _safe_float(tx.get("amount") or 0)
        is_outlier = (ttype == "expense" and amount in outlier_amounts)
        
        amounts.append(amount if ttype == "expense" else -amount if ttype == "income" else amount)
        cat = tx.get("category") or "Other"
        
        if ttype == "expense" and not is_outlier:
            categories[cat] += amount

        d = tx.get("date")
        if isinstance(d, datetime):
            key = (d.year, d.month)
            if ttype == "income":
                monthly[key]["income"] += amount
                total_income += amount
            elif is_outlier:
                # Track one-time purchases separately
                monthly[key]["outlier_expense"] += amount
                total_outlier_expense += amount
            else:
                # Regular expenses
                monthly[key]["expense"] += amount
                total_expense += amount
        else:
            # fallback: aggregate to 'unknown'
            if ttype == "income":
                total_income += amount
            elif is_outlier:
                total_outlier_expense += amount
            else:
                total_expense += amount

    # Convert monthly to sorted list
    monthly_keys = sorted(list(monthly.keys()))
    monthly_series = []
    for (y, m) in monthly_keys:
        monthly_series.append({
            "year": y,
            "month": m,
            "income": monthly[(y, m)]["income"],
            "expense": monthly[(y, m)]["expense"],
            "outlier_expense": monthly[(y, m)]["outlier_expense"],
        })

    return {
        "monthly_series": monthly_series,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_outlier_expense": total_outlier_expense,
        "categories": dict(categories),
        "amounts": amounts,
    }

def compute_spending_volatility(monthly_series: List[Dict[str, Any]]):
    """
    Compute spending volatility as coefficient of variation of monthly expenses.
    """
    expenses = [m["expense"] for m in monthly_series if m.get("expense") is not None]
    if not expenses:
        return 0.0
    mean = sum(expenses) / len(expenses)
    if mean == 0:
        return 0.0
    variance = sum((x - mean) ** 2 for x in expenses) / len(expenses)
    stddev = math.sqrt(variance)
    cov = stddev / mean
    return cov  # e.g., 0.2 = 20% volatility

def simple_linear_forecast(monthly_series: List[Dict[str, Any]], periods: int = 4):
    """
    Forecast next `periods` values for expense using simple linear regression on monthly totals.
    Returns list of floats (predicted expenses).
    """
    # Build x (0..n-1) and y (monthly expense)
    ys = [m["expense"] for m in monthly_series]
    n = len(ys)
    if n == 0:
        return [0.0] * periods

    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((xi - mean_x) ** 2 for xi in xs)
    if denom == 0:
        slope = 0.0
    else:
        slope = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x

    preds = []
    for p in range(n, n + periods):
        preds.append(max(0.0, intercept + slope * p))
    return preds

def compute_diversification_score(categories: Dict[str, float]):
    """
    Compute a simple diversification score (0..1) where 1 means perfectly diversified.
    Uses normalized entropy of category shares.
    """
    total = sum(categories.values()) or 1.0
    shares = [v / total for v in categories.values() if v > 0]
    if not shares:
        return 0.0
    import math
    entropy = -sum(s * math.log(s + 1e-12) for s in shares)
    max_entropy = math.log(len(shares))
    if max_entropy <= 0:
        return 1.0
    score = entropy / max_entropy
    return score

def estimate_credit_score_from_behaviour(payment_consistency: float, dti: float):
    """
    Heuristic estimated credit score from DTI and payment consistency.
    Returns a plausible credit score (300-850).
    """
    base = 650
    # payment consistency: 0..1
    base += (payment_consistency - 0.7) * 200  # reward consistency
    # dti: higher dti reduces score
    base -= (dti - 0.3) * 200
    return int(max(300, min(850, base)))

def compute_weekly_insights(transactions: List[Dict[str, Any]]):
    """
    Compute simple weekly insights for the most recent 7-day window.
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    recent = [tx for tx in transactions if isinstance(tx.get("date"), datetime) and tx["date"] >= week_start]
    total_spent = sum(_safe_float(tx.get("amount") or 0) for tx in recent if (tx.get("type") or "").lower() != "income")
    # category breakdown
    cat_counter = Counter()
    for tx in recent:
        if (tx.get("type") or "").lower() != "income":
            cat_counter[tx.get("category") or "Other"] += _safe_float(tx.get("amount") or 0)
    insights = []
    if total_spent == 0:
        insights.append("No expenses in the last 7 days.")
    else:
        # top category
        top_cat, top_val = cat_counter.most_common(1)[0] if cat_counter else (None, 0)
        if top_cat:
            insights.append(f"Top spending category in last 7 days: {top_cat} (₹{int(top_val)})")
        # check spikes: compare last 7 days average to previous 7 days
        prev_start = week_start - timedelta(days=7)
        prev = [tx for tx in transactions if isinstance(tx.get("date"), datetime) and prev_start <= tx["date"] < week_start]
        prev_spent = sum(_safe_float(tx.get("amount") or 0) for tx in prev if (tx.get("type") or "").lower() != "income")
        prev_avg = prev_spent / 7 if prev_spent else 0
        curr_avg = total_spent / 7
        if prev_avg > 0 and curr_avg > prev_avg * 1.3:
            insights.append("Spending increased significantly vs previous week.")
    recommendations = []
    if total_spent > 0:
        recommendations.append("Review top categories to reduce discretionary spending.")
    return {
        "total_spending": total_spent,
        "insights": insights,
        "recommendations": recommendations,
    }

def build_advanced_analytics(user_id: str) -> Dict[str, Any]:
    """
    Main function to gather transactions and compute analytics for a user.
    """
    db = get_db()
    # Fetch transactions for user_id
    # user_id stored as string (in your DB implementation it may be string)
    try:
        txs_cursor = db.transactions.find({"user_id": user_id}).sort("date", -1)
        transactions = list(txs_cursor)
    except Exception:
        # Fallback: return empty analytics
        transactions = []

    # Convert BSON ObjectId dates etc if needed — assume db stores date as datetime already.

    aggregates = compute_basic_aggregates(transactions)
    monthly_series = aggregates["monthly_series"]
    total_income = aggregates["total_income"]
    total_expense = aggregates["total_expense"]
    total_outlier_expense = aggregates.get("total_outlier_expense", 0)  # 🔥 FIX: Get outlier expense
    categories = aggregates["categories"]

    # Monthly averages (EXCLUDING OUTLIER ONE-TIME PURCHASES)
    months_count = max(1, len(monthly_series))
    avg_monthly_income = total_income / months_count
    avg_monthly_expense = total_expense / months_count
    avg_monthly_savings = max(0.0, avg_monthly_income - avg_monthly_expense)
    
    # 🔥 DEBUG: Log calculations for verification
    print(f"📊 Analytics Debug:")
    print(f"   Total Income: ₹{total_income:,.0f}")
    print(f"   Total Expense (regular): ₹{total_expense:,.0f}")
    print(f"   Total Outlier Expense: ₹{total_outlier_expense:,.0f}")
    print(f"   Months: {months_count}")
    print(f"   Avg Monthly Income: ₹{avg_monthly_income:,.0f}")
    print(f"   Avg Monthly Expense: ₹{avg_monthly_expense:,.0f}")
    print(f"   Avg Monthly Savings: ₹{avg_monthly_savings:,.0f}")
    print(f"   Annual Savings: ₹{avg_monthly_savings * 12:,.0f}")

    # DTI (Debt to income) approximate: if user records debt as category 'Debt' or 'Loan' we can incorporate,
    # but fallback to expense/income.
    dti = (avg_monthly_expense / avg_monthly_income) if avg_monthly_income > 0 else 1.0
    dti = min(max(dti, 0.0), 10.0)

    # Payment consistency: heuristic based on months with income present vs months without
    income_months = sum(1 for m in monthly_series if m.get("income", 0) > 0)
    payment_consistency = income_months / months_count if months_count > 0 else 0.0

    # Liquidity: emergency fund months estimated as (avg_monthly_savings * 3) / avg_monthly_expense
    emergency_fund_months = 0.0
    if avg_monthly_expense > 0 and avg_monthly_savings > 0:
        # estimate: how many months could we cover by 3 months saved (approx)
        emergency_fund_months = (avg_monthly_savings * 3) / avg_monthly_expense
    elif avg_monthly_savings > 0:
        emergency_fund_months = 3.0
    else:
        emergency_fund_months = 0.0

    # Spending volatility
    volatility = compute_spending_volatility(monthly_series)

    # Diversification score
    diversification_score = compute_diversification_score(categories)

    # Estimated credit score
    estimated_credit_score = estimate_credit_score_from_behaviour(payment_consistency, dti)

    # Overall risk score: combine metrics into 0..1 (higher means more risk)
    # We combine: normalized dti, inverse payment_consistency, volatility, and inverse diversification
    norm_dti = min(1.0, dti)  # higher is worse
    inv_payment = 1.0 - min(1.0, payment_consistency)
    inv_diversification = 1.0 - diversification_score
    overall_risk_score = (
        0.4 * norm_dti +
        0.25 * inv_payment +
        0.2 * volatility +
        0.15 * inv_diversification
    )
    overall_risk_score = max(0.0, min(1.0, overall_risk_score))

    # risk level bucket
    if overall_risk_score < 0.33:
        risk_level = "low"
    elif overall_risk_score < 0.66:
        risk_level = "medium"
    else:
        risk_level = "high"

    # Forecast next 4 months spending
    forecast = simple_linear_forecast(monthly_series, periods=4)

    # Weekly insights
    weekly = compute_weekly_insights(transactions)

    # Build structured output
    analytics = {
        "risk_assessment": {
            "overall_risk_score": overall_risk_score,
            "risk_level": risk_level,
            "credit_risk": {
                "dti_ratio": dti,
                "estimated_credit_score": estimated_credit_score,
                "payment_consistency": payment_consistency,
                "risk_level": "high" if dti > 0.6 else ("medium" if dti > 0.4 else "low"),
            },
            "liquidity_risk": {
                "emergency_fund_months": emergency_fund_months,
                "income_stability": payment_consistency,
                "liquidity_ratio": (avg_monthly_income / (avg_monthly_expense + 1e-9)) if avg_monthly_expense > 0 else 0,
                "risk_level": "high" if emergency_fund_months < 1 else ("medium" if emergency_fund_months < 3 else "low"),
            },
            "market_risk": {
                "spending_volatility": volatility,
                "diversification_score": diversification_score,
                "market_exposure": "high" if diversification_score < 0.3 else ("medium" if diversification_score < 0.6 else "low"),
                "risk_level": "high" if volatility > 0.5 else ("medium" if volatility > 0.25 else "low"),
            },
            "operational_risk": {
                "financial_discipline": min(1.0, avg_monthly_savings / (avg_monthly_income + 1e-9)) if avg_monthly_income>0 else 0.0,
                "spending_consistency": 1.0 - volatility,
                "goal_achievement_rate": 0.5,  # placeholder (requires goal data)
                "risk_level": "high" if avg_monthly_savings < 0 else ("low" if avg_monthly_savings > avg_monthly_expense * 0.2 else "medium"),
            },
            "recommendations": [
                # simple recommendations based on computed values
            ],
        },
        "predictions": {
            "forecast": forecast,
            "average_predicted": sum(forecast) / len(forecast) if forecast else 0.0,
            "financial_trajectory": {
                "income_trend": min(1.0, max(-1.0, (monthly_series[-1]["income"] - monthly_series[0]["income"]) / (monthly_series[0]["income"] + 1e-9))) if len(monthly_series) > 1 and monthly_series[0]["income"] > 0 else 0.0,
                "expense_trend": min(1.0, max(-1.0, (monthly_series[-1]["expense"] - monthly_series[0]["expense"]) / (monthly_series[0]["expense"] + 1e-9))) if len(monthly_series) > 1 and monthly_series[0]["expense"] > 0 else 0.0,
                "annual_projection": {
                    "total_income": int(avg_monthly_income * 12),
                    "total_expenses": int(avg_monthly_expense * 12),
                    "total_savings": int(max(0, (avg_monthly_income - avg_monthly_expense) * 12)),
                },
            },
            "recommendations": [],
        },
        "weekly_insights": weekly,
        # Include some raw aggregates for the frontend, if needed
        "aggregates": {
            "total_income": total_income,
            "total_expense": total_expense,
            "monthly_series": monthly_series,
            "top_categories": sorted(categories.items(), key=lambda kv: kv[1], reverse=True)[:6],
        },
    }

    # Add dynamic recommendations
    recs = analytics["risk_assessment"]["recommendations"]
    if dti > 0.5:
        recs.append("Consider lowering recurring liabilities — your DTI is relatively high.")
    if emergency_fund_months < 1:
        recs.append("Build an emergency fund covering at least 1–3 months of expenses.")
    if volatility > 0.4:
        recs.append("Your spending is volatile — consider stabilizing discretionary spending.")
    if diversification_score < 0.4:
        recs.append("Your spending is concentrated in a few categories — review diversification.")
    if avg_monthly_savings <= 0:
        recs.append("Increase savings or reduce expenses to achieve positive monthly savings.")

    analytics["risk_assessment"]["recommendations"] = recs
    analytics["predictions"]["recommendations"] = analytics["risk_assessment"]["recommendations"]

    return analytics
