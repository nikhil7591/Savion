import re
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from . import db
from .models import Transaction
from .ml import categorize_descriptions, forecast, detect_anomalies

class ConversationalAgent:
    """Handles natural language queries about financial data"""
    
    def __init__(self):
        pass
        
    def process_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Process natural language query and return structured response"""
        query_lower = query.lower().strip()
        
        # Route to appropriate handler based on query intent
        if any(word in query_lower for word in ['spend', 'spent', 'expense', 'cost']):
            return self._handle_spending_query(user_id, query)
        elif any(word in query_lower for word in ['budget', 'overspend', 'exceed']):
            return self._handle_budget_query(user_id, query)
        elif any(word in query_lower for word in ['predict', 'forecast', 'future', 'next month']):
            return self._handle_prediction_query(user_id, query)
        elif any(word in query_lower for word in ['anomaly', 'unusual', 'suspicious', 'strange']):
            return self._handle_anomaly_query(user_id, query)
        elif any(word in query_lower for word in ['save', 'goal', 'target', 'plan']):
            return self._handle_goal_query(user_id, query)
        elif any(word in query_lower for word in ['summary', 'overview', 'total', 'balance']):
            return self._handle_summary_query(user_id, query)
        else:
            return self._handle_general_query(user_id, query)
    
    def _handle_spending_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle spending-related queries"""
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        
        category = self._extract_category(query)
        if category:
            transactions = [t for t in transactions if t.get('category', '').lower() == category.lower()]
        
        total_spent = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'expense')
        
        response = {
            "type": "spending_analysis",
            "query": query,
            "total_spent": total_spent,
            "period": time_period,
            "category": category,
            "transaction_count": len(transactions),
            "insights": self._generate_spending_insights(transactions, total_spent)
        }
        
        return response
    
    def _handle_budget_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle budget-related queries"""
        budget_amount = self._extract_amount(query)
        time_period = self._extract_time_period(query)
        
        transactions = self._get_transactions(user_id, time_period)
        total_spent = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'expense')
        
        if budget_amount:
            overspend = total_spent - budget_amount
            status = "over" if overspend > 0 else "under"
        else:
            historical_avg = self._get_historical_average(user_id, time_period)
            overspend = total_spent - historical_avg
            status = "over" if overspend > 0 else "under"
            budget_amount = historical_avg
        
        response = {
            "type": "budget_analysis",
            "query": query,
            "total_spent": total_spent,
            "budget_amount": budget_amount,
            "overspend_amount": abs(overspend),
            "status": status,
            "percentage": (total_spent / budget_amount * 100) if budget_amount > 0 else 0,
            "recommendations": self._generate_budget_recommendations(total_spent, budget_amount, status)
        }
        
        return response
    
    def _handle_prediction_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle prediction-related queries"""
        transactions = self._get_transactions(user_id, "all")
        expense_values = [t.get('amount', 0) for t in transactions if t.get('type') == 'expense']
        
        if len(expense_values) < 4:
            return {
                "type": "prediction",
                "query": query,
                "error": "Insufficient data for prediction. Need at least 4 transactions.",
                "forecast": []
            }
        
        forecast_values = forecast(expense_values, periods=4)
        
        budget_limit = self._extract_amount(query)
        will_exceed = False
        if budget_limit:
            will_exceed = any(f > budget_limit for f in forecast_values)
        
        response = {
            "type": "prediction",
            "query": query,
            "forecast": forecast_values,
            "average_predicted": sum(forecast_values) / len(forecast_values) if forecast_values else 0,
            "budget_limit": budget_limit,
            "will_exceed_budget": will_exceed,
            "recommendations": self._generate_prediction_recommendations(forecast_values, budget_limit)
        }
        
        return response
    
    def _handle_anomaly_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle anomaly detection queries"""
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        expense_values = [t.get('amount', 0) for t in transactions if t.get('type') == 'expense']
        
        if len(expense_values) < 3:
            return {
                "type": "anomaly_detection",
                "query": query,
                "error": "Insufficient data for anomaly detection. Need at least 3 transactions.",
                "anomalies": []
            }
        
        anomaly_indices = detect_anomalies(expense_values)
        anomalies = []
        
        for idx in anomaly_indices:
            if idx < len(transactions):
                anomalies.append({
                    "transaction": transactions[idx],
                    "amount": expense_values[idx],
                    "reason": "Unusually high expense compared to your spending pattern"
                })
        
        response = {
            "type": "anomaly_detection",
            "query": query,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "recommendations": self._generate_anomaly_recommendations(anomalies)
        }
        
        return response
    
    def _handle_goal_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle goal-setting queries"""
        goal_amount = self._extract_amount(query)
        timeframe = self._extract_timeframe(query)
        
        if not goal_amount or not timeframe:
            return {
                "type": "goal_setting",
                "query": query,
                "error": "Could not extract goal amount or timeframe from query",
                "suggestions": self._generate_goal_suggestions(user_id)
            }
        
        transactions = self._get_transactions(user_id, "all")
        total_income = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'income')
        total_expenses = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'expense')
        current_savings = total_income - total_expenses
        
        months = self._timeframe_to_months(timeframe)
        required_monthly = goal_amount / months if months > 0 else 0
        
        response = {
            "type": "goal_setting",
            "query": query,
            "goal_amount": goal_amount,
            "timeframe": timeframe,
            "required_monthly_savings": required_monthly,
            "current_savings": current_savings,
            "feasible": required_monthly <= (total_income * 0.3),
            "recommendations": self._generate_goal_recommendations(goal_amount, required_monthly, current_savings)
        }
        
        return response
    
    def _handle_summary_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle summary/overview queries"""
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        
        total_income = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'income')
        total_expenses = sum(t.get('amount', 0) for t in transactions if t.get('type') == 'expense')
        balance = total_income - total_expenses
        
        # Category breakdown
        category_summary = {}
        for t in transactions:
            cat = t.get('category', 'Other')
            if cat not in category_summary:
                category_summary[cat] = 0
            category_summary[cat] += t.get('amount', 0)
        
        response = {
            "type": "summary",
            "query": query,
            "period": time_period,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "transaction_count": len(transactions),
            "category_breakdown": category_summary,
            "insights": self._generate_summary_insights(total_income, total_expenses, balance)
        }
        
        return response
    
    def _handle_general_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle general queries"""
        return {
            "type": "general",
            "query": query,
            "message": "I understand you're asking about your finances. Could you be more specific? You can ask about spending, budget, predictions, or goals.",
            "suggestions": [
                "How much did I spend this month?",
                "Am I over budget?",
                "What will my spending be next month?",
                "Do I have any unusual transactions?",
                "Can I save 10000 rupees in 6 months?"
            ]
        }
    
    def _get_transactions(self, user_id: str, time_period: str) -> List[Dict[str, Any]]:
        """Get transactions from MongoDB"""
        transactions = db.get_transactions(user_id)
        
        if time_period == "all":
            return transactions
        
        now = datetime.now()
        cutoff_date = None
        
        if time_period == "today":
            cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == "this_week":
            cutoff_date = now - timedelta(days=now.weekday())
        elif time_period == "this_month":
            cutoff_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_period == "last_month":
            first_day = now.replace(day=1)
            last_month = first_day - timedelta(days=1)
            cutoff_date = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = first_day
        elif time_period == "last_3_months":
            cutoff_date = now - timedelta(days=90)
        elif time_period == "last_6_months":
            cutoff_date = now - timedelta(days=180)
        elif time_period == "this_year":
            cutoff_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if cutoff_date:
            transactions = [
                t for t in transactions 
                if isinstance(t.get('date'), datetime) and t['date'] >= cutoff_date
            ]
        
        return transactions
    
    def _extract_time_period(self, query: str) -> str:
        """Extract time period from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['today', 'today']):
            return "today"
        elif any(word in query_lower for word in ['week', 'weekly']):
            return "this_week"
        elif any(word in query_lower for word in ['month', 'monthly']):
            if 'last' in query_lower:
                return "last_month"
            return "this_month"
        elif any(word in query_lower for word in ['3 months', 'three months', 'quarter']):
            return "last_3_months"
        elif any(word in query_lower for word in ['6 months', 'six months']):
            return "last_6_months"
        elif any(word in query_lower for word in ['year', 'yearly', 'annual']):
            return "this_year"
        else:
            return "this_month"
    
    def _extract_amount(self, query: str) -> Optional[float]:
        """Extract amount from query"""
        match = re.search(r'(\d+(?:\.\d{1,2})?)', query)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None
    
    def _extract_category(self, query: str) -> Optional[str]:
        """Extract category from query"""
        categories = [
            'food', 'transport', 'shopping', 'utilities', 'rent', 
            'entertainment', 'healthcare', 'salary', 'groceries'
        ]
        
        for cat in categories:
            if cat in query.lower():
                return cat
        
        return None
    
    def _extract_timeframe(self, query: str) -> Optional[str]:
        """Extract timeframe from query"""
        match = re.search(r'(\d+)\s*(month|months|year|years|week|weeks|day|days)', query.lower())
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None
    
    def _timeframe_to_months(self, timeframe: str) -> int:
        """Convert timeframe to months"""
        if not timeframe:
            return 1
        
        match = re.search(r'(\d+)\s*(month|year|week|day)', timeframe.lower())
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if 'year' in unit:
                return value * 12
            elif 'week' in unit:
                return max(1, value // 4)
            elif 'day' in unit:
                return max(1, value // 30)
            else:
                return value
        
        return 1
    
    def _get_historical_average(self, user_id: str, time_period: str) -> float:
        """Get historical average spending"""
        transactions = self._get_transactions(user_id, "last_6_months")
        if not transactions:
            return 0
        
        expenses = [t.get('amount', 0) for t in transactions if t.get('type') == 'expense']
        if not expenses:
            return 0
        
        return sum(expenses) / len(expenses)
    
    def _generate_spending_insights(self, transactions: List[Dict], total_spent: float) -> List[str]:
        """Generate insights about spending"""
        insights = []
        
        if not transactions:
            insights.append("No transactions in this period")
            return insights
        
        if total_spent > 0:
            avg_transaction = total_spent / len(transactions)
            insights.append(f"Average transaction: ₹{avg_transaction:.0f}")
        
        # Category analysis
        categories = {}
        for t in transactions:
            cat = t.get('category', 'Other')
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += t.get('amount', 0)
        
        if categories:
            top_category = max(categories, key=categories.get)
            insights.append(f"Top spending category: {top_category} (₹{categories[top_category]:.0f})")
        
        return insights
    
    def _generate_budget_recommendations(self, total_spent: float, budget: float, status: str) -> List[str]:
        """Generate budget recommendations"""
        recommendations = []
        
        if status == "over":
            percentage_over = ((total_spent - budget) / budget) * 100
            recommendations.append(f"You are {percentage_over:.0f}% over budget")
            recommendations.append("Consider reducing expenses in high-spending categories")
        else:
            percentage_under = ((budget - total_spent) / budget) * 100
            recommendations.append(f"You are {percentage_under:.0f}% under budget")
            recommendations.append("Good spending control! Consider increasing savings")
        
        return recommendations
    
    def _generate_prediction_recommendations(self, forecast: List[float], budget: Optional[float]) -> List[str]:
        """Generate prediction recommendations"""
        recommendations = []
        
        if forecast:
            avg_forecast = sum(forecast) / len(forecast)
            recommendations.append(f"Predicted average spending: ₹{avg_forecast:.0f}")
            
            if budget and avg_forecast > budget:
                recommendations.append(f"Predicted spending may exceed budget of ₹{budget:.0f}")
        
        return recommendations
    
    def _generate_anomaly_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """Generate anomaly recommendations"""
        recommendations = []
        
        if anomalies:
            recommendations.append(f"Found {len(anomalies)} unusual transaction(s)")
            recommendations.append("Review these transactions for accuracy")
        else:
            recommendations.append("No unusual transactions detected")
        
        return recommendations
    
    def _generate_goal_recommendations(self, goal: float, required_monthly: float, current_savings: float) -> List[str]:
        """Generate goal recommendations"""
        recommendations = []
        
        recommendations.append(f"Required monthly savings: ₹{required_monthly:.0f}")
        
        if current_savings >= required_monthly:
            recommendations.append("Current savings rate is sufficient to achieve this goal")
        else:
            shortfall = required_monthly - current_savings
            recommendations.append(f"You need to increase savings by ₹{shortfall:.0f} per month")
        
        return recommendations
    
    def _generate_goal_suggestions(self, user_id: str) -> List[str]:
        """Generate goal suggestions"""
        return [
            "Example: Save ₹50000 in 6 months",
            "Example: Save ₹100000 in 1 year",
            "Example: Save ₹10000 in 3 months"
        ]
    
    def _generate_summary_insights(self, income: float, expenses: float, balance: float) -> List[str]:
        """Generate summary insights"""
        insights = []
        
        insights.append(f"Total income: ₹{income:.0f}")
        insights.append(f"Total expenses: ₹{expenses:.0f}")
        
        if balance > 0:
            savings_rate = (balance / income * 100) if income > 0 else 0
            insights.append(f"Savings rate: {savings_rate:.1f}%")
        else:
            insights.append("Negative balance - spending exceeds income")
        
        return insights


class CategorizationAgent:
    """Handles transaction categorization"""
    
    def correct_classification(self, transaction_id: str, new_category: str) -> Dict[str, Any]:
        """Correct transaction categorization"""
        return {
            "transaction_id": transaction_id,
            "new_category": new_category,
            "message": "Category updated successfully"
        }


class PredictionAgent:
    """Handles spending predictions"""
    
    def predict_spending(self, user_id: str, expense_values: List[float], periods: int) -> Dict[str, Any]:
        """Predict future spending"""
        if not expense_values or len(expense_values) < 4:
            return {
                "error": "Insufficient data for prediction"
            }
        
        forecast_values = forecast(expense_values, periods=periods)
        
        return {
            "forecast": forecast_values,
            "average_forecast": sum(forecast_values) / len(forecast_values) if forecast_values else 0
        }


class AnomalyAgent:
    """Handles anomaly detection"""
    
    def detect_anomalies(self, user_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """Detect anomalies in transactions"""
        expense_values = [t.get('amount', 0) for t in transactions if t.get('type') == 'expense']
        
        if len(expense_values) < 3:
            return {
                "anomalies": [],
                "message": "Insufficient data for anomaly detection"
            }
        
        anomaly_indices = detect_anomalies(expense_values)
        
        return {
            "anomalies": [
                {
                    "index": idx,
                    "amount": expense_values[idx]
                }
                for idx in anomaly_indices
            ],
            "count": len(anomaly_indices)
        }


class GoalSettingAgent:
    """Handles financial goal setting"""
    
    def create_savings_goal(self, user_id: str, goal_amount: float, timeframe_months: int) -> Dict[str, Any]:
        """Create a savings goal"""
        return {
            "goal_amount": goal_amount,
            "timeframe_months": timeframe_months,
            "required_monthly": goal_amount / timeframe_months if timeframe_months > 0 else 0,
            "message": "Savings goal created successfully"
        }
    
    def get_expense_reduction_suggestions(self, user_id: str, target_reduction_percent: float) -> Dict[str, Any]:
        """Get expense reduction suggestions"""
        transactions = db.get_transactions(user_id)
        
        categories = {}
        for t in transactions:
            cat = t.get('category', 'Other')
            if cat not in categories:
                categories[cat] = 0
            if t.get('type') == 'expense':
                categories[cat] += t.get('amount', 0)
        
        suggestions = []
        for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]:
            reduction_amount = (amount * target_reduction_percent) / 100
            suggestions.append(f"Reduce {cat} spending by ₹{reduction_amount:.0f}")
        
        return {
            "target_reduction_percent": target_reduction_percent,
            "suggestions": suggestions
        }


class NotificationAgent:
    """Handles notifications and alerts"""
    
    def check_spending_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Check for spending alerts"""
        transactions = db.get_transactions(user_id)
        
        month_expenses = [
            t for t in transactions
            if t.get('type') == 'expense' and 
            isinstance(t.get('date'), datetime) and
            t['date'].month == datetime.now().month
        ]
        
        total_spent = sum(t.get('amount', 0) for t in month_expenses)
        
        alerts = []
        
        if total_spent > 50000:
            alerts.append({
                "type": "high_spending",
                "message": f"High spending detected: ₹{total_spent:.0f}",
                "severity": "high"
            })
        
        return alerts
    
    def generate_weekly_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate weekly insights"""
        transactions = db.get_transactions(user_id)
        
        this_week = [
            t for t in transactions
            if isinstance(t.get('date'), datetime) and
            t['date'] >= datetime.now() - timedelta(days=7)
        ]
        
        weekly_expense = sum(t.get('amount', 0) for t in this_week if t.get('type') == 'expense')
        
        return {
            "weekly_expense": weekly_expense,
            "transaction_count": len(this_week),
            "insights": [f"You spent ₹{weekly_expense:.0f} this week"]
        }


class RiskAssessmentAgent:
    """Advanced Risk Assessment Engine"""

    # ---------------- HELPERS ---------------- #

    def _to_dt(self, d):
        if isinstance(d, datetime):
            return d
        try:
            return datetime.fromisoformat(d)
        except:
            try:
                import pandas as pd
                ts = pd.to_datetime(d, errors="coerce")
                if not pd.isna(ts):
                    return ts.to_pydatetime()
            except:
                return None
        return None

    def _safe_float(self, v):
        try:
            return float(v)
        except:
            return 0.0

    def _monthly_series(self, txs):
        """Aggregate transactions into month buckets"""
        buckets = {}
        categories = {}

        for t in txs:
            dt = self._to_dt(t.get("date"))
            if not dt:
                continue
            key = (dt.year, dt.month)

            if key not in buckets:
                buckets[key] = {"income": 0, "expense": 0}

            amt = self._safe_float(t.get("amount"))
            if t.get("type") == "income":
                buckets[key]["income"] += amt
            else:
                buckets[key]["expense"] += amt
                cat = t.get("category", "Other")
                categories[cat] = categories.get(cat, 0) + amt

        # Sort by year, month
        series = []
        for (y, m) in sorted(buckets.keys()):
            series.append({
                "year": y,
                "month": m,
                "income": buckets[(y, m)]["income"],
                "expense": buckets[(y, m)]["expense"]
            })

        return series, categories

    # --------------- STAT METRICS ---------------- #

    def _coefficient_of_variation(self, values):
        if not values:
            return 0
        import statistics
        mean = statistics.mean(values)
        if mean == 0:
            return 0
        stdev = statistics.pstdev(values)
        return stdev / mean

    def _entropy(self, amounts):
        total = sum(amounts)
        if total <= 0:
            return 0
        import math
        probs = [a / total for a in amounts]
        ent = -sum(p * math.log(p + 1e-12) for p in probs)
        max_ent = math.log(len(amounts)) if len(amounts) > 0 else 1
        return ent / max_ent if max_ent > 0 else 1

    # --------------- MAIN CALC ---------------- #

    def assess(self, user_id: str):
        txs = db.get_transactions(user_id)
        series, cat_map = self._monthly_series(txs)

        months = len(series)
        if months == 0:
            return {
                "overall_risk_score": 0.3,
                "risk_level": "medium",
                "credit_risk": {},
                "liquidity_risk": {},
                "market_risk": {},
                "operational_risk": {},
                "recommendations": ["Add more transaction history for accurate assessment"]
            }

        avg_income = sum(m["income"] for m in series) / months
        avg_expense = sum(m["expense"] for m in series) / months
        avg_savings = max(0, avg_income - avg_expense)

        # ---- credit risk ---- #
        dti = avg_expense / (avg_income + 1e-9)
        dti_norm = min(1, dti / 1.0)

        income_months = sum(1 for m in series if m["income"] > 0)
        payment_consistency = income_months / months

        credit_sub = 0.6 * dti_norm + 0.4 * (1 - payment_consistency)

        # ---- liquidity ---- #
        emergency_months = (avg_savings / (avg_expense + 1e-9)) * 3 if avg_expense > 0 else 6
        liquidity_sub = 1 - min(emergency_months, 6) / 6

        # ---- market ---- #
        exp_values = [m["expense"] for m in series]
        vol = self._coefficient_of_variation(exp_values)
        vol_norm = min(1, vol)

        diversification = self._entropy(list(cat_map.values()))
        market_sub = 0.6 * vol_norm + 0.4 * (1 - diversification)

        # ---- operational ---- #
        discipline = avg_savings / (avg_income + 1e-9)
        discipline = min(max(discipline, 0), 1)
        spending_consistency = 1 - vol_norm
        operational_sub = 0.6 * (1 - discipline) + 0.4 * (1 - spending_consistency)

        # ---- final weighted score ---- #
        weights = {
            "credit": 0.30,
            "liquidity": 0.30,
            "market": 0.20,
            "operational": 0.20
        }

        overall = (
            weights["credit"] * credit_sub +
            weights["liquidity"] * liquidity_sub +
            weights["market"] * market_sub +
            weights["operational"] * operational_sub
        )

        if overall < 0.25:
            level = "low"
        elif overall < 0.6:
            level = "medium"
        else:
            level = "high"

        # ---- recommendations ---- #
        recs = []
        if dti > 0.5:
            recs.append("DTI ratio is high. Reduce recurring expenses.")
        if emergency_months < 1:
            recs.append("Emergency fund is too low.")
        if vol > 0.4:
            recs.append("Spending is highly volatile.")
        if diversification < 0.35:
            recs.append("Expenses are concentrated in few categories.")
        if avg_savings <= 0:
            recs.append("No positive monthly savings recorded.")
        if not recs:
            recs.append("Your finances look healthy. Keep it up!")

        return {
            "overall_risk_score": overall,
            "risk_level": level,
            "credit_risk": {
                "dti_ratio": dti,
                "payment_consistency": payment_consistency,
                "risk_level": "high" if credit_sub > 0.66 else ("medium" if credit_sub > 0.33 else "low")
            },
            "liquidity_risk": {
                "emergency_fund_months": emergency_months,
                "income_stability": payment_consistency,
                "liquidity_ratio": avg_income / (avg_expense + 1e-9),
                "risk_level": "high" if liquidity_sub > 0.66 else ("medium" if liquidity_sub > 0.33 else "low")
            },
            "market_risk": {
                "spending_volatility": vol,
                "diversification_score": diversification,
                "market_exposure": "high" if diversification < 0.35 else ("medium" if diversification < 0.6 else "low"),
                "risk_level": "high" if market_sub > 0.66 else ("medium" if market_sub > 0.33 else "low")
            },
            "operational_risk": {
                "financial_discipline": discipline,
                "spending_consistency": spending_consistency,
                "goal_achievement_rate": 0.5,
                "risk_level": "high" if operational_sub > 0.66 else ("medium" if operational_sub > 0.33 else "low")
            },
            "recommendations": recs
        }


class PredictiveAnalyticsAgent:
    """Handles predictive analytics"""
    
    def comprehensive_prediction(self, user_id: str) -> Dict[str, Any]:
        """Comprehensive prediction"""
        transactions = db.get_transactions(user_id)
        
        expenses = [t.get('amount', 0) for t in transactions if t.get('type') == 'expense']
        
        if not expenses or len(expenses) < 4:
            return {
                "forecast": [],
                "message": "Insufficient data for predictions"
            }
        
        forecast_values = forecast(expenses, periods=4)
        
        return {
            "forecast": forecast_values,
            "average_forecast": sum(forecast_values) / len(forecast_values) if forecast_values else 0
        }
