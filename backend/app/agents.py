import re
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import select, Session
from .models import Transaction
from .ml import categorize_descriptions, forecast, detect_anomalies

class ConversationalAgent:
    """Handles natural language queries about financial data"""
    
    def __init__(self, session: Session):
        self.session = session
        
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
        # Extract time period
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        
        # Extract category if mentioned
        category = self._extract_category(query)
        if category:
            transactions = [t for t in transactions if t.category.lower() == category.lower()]
        
        total_spent = sum(t.amount for t in transactions if t.type == 'expense')
        
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
        # Extract budget amount if mentioned
        budget_amount = self._extract_amount(query)
        time_period = self._extract_time_period(query)
        
        transactions = self._get_transactions(user_id, time_period)
        total_spent = sum(t.amount for t in transactions if t.type == 'expense')
        
        if budget_amount:
            overspend = total_spent - budget_amount
            status = "over" if overspend > 0 else "under"
        else:
            # Use historical average as baseline
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
        expense_values = [t.amount for t in transactions if t.type == 'expense']
        
        if len(expense_values) < 4:
            return {
                "type": "prediction",
                "query": query,
                "error": "Insufficient data for prediction. Need at least 4 transactions.",
                "forecast": []
            }
        
        # Get forecast for next 4 periods
        forecast_values = forecast(expense_values, periods=4)
        
        # Extract specific budget if mentioned
        budget_limit = self._extract_amount(query)
        will_exceed = False
        if budget_limit:
            will_exceed = any(f > budget_limit for f in forecast_values)
        
        response = {
            "type": "prediction",
            "query": query,
            "forecast": forecast_values,
            "average_predicted": sum(forecast_values) / len(forecast_values),
            "budget_limit": budget_limit,
            "will_exceed_budget": will_exceed,
            "recommendations": self._generate_prediction_recommendations(forecast_values, budget_limit)
        }
        
        return response
    
    def _handle_anomaly_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle anomaly detection queries"""
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        expense_values = [t.amount for t in transactions if t.type == 'expense']
        
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
        # Extract goal amount and timeframe
        goal_amount = self._extract_amount(query)
        timeframe = self._extract_timeframe(query)
        
        if not goal_amount or not timeframe:
            return {
                "type": "goal_setting",
                "query": query,
                "error": "Could not extract goal amount or timeframe from query",
                "suggestions": self._generate_goal_suggestions(user_id)
            }
        
        # Calculate current savings rate
        transactions = self._get_transactions(user_id, "all")
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        current_savings = total_income - total_expenses
        
        # Calculate required monthly savings
        months = self._timeframe_to_months(timeframe)
        required_monthly = goal_amount / months if months > 0 else 0
        
        response = {
            "type": "goal_setting",
            "query": query,
            "goal_amount": goal_amount,
            "timeframe": timeframe,
            "required_monthly_savings": required_monthly,
            "current_savings": current_savings,
            "feasible": required_monthly <= (total_income * 0.3),  # Assume max 30% savings rate
            "recommendations": self._generate_goal_recommendations(goal_amount, required_monthly, current_savings)
        }
        
        return response
    
    def _handle_summary_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle summary/overview queries"""
        time_period = self._extract_time_period(query)
        transactions = self._get_transactions(user_id, time_period)
        
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        balance = total_income - total_expenses
        
        # Category breakdown
        categories = {}
        for t in transactions:
            if t.type == 'expense':
                categories[t.category] = categories.get(t.category, 0) + t.amount
        
        response = {
            "type": "summary",
            "query": query,
            "period": time_period,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "categories": categories,
            "transaction_count": len(transactions),
            "insights": self._generate_summary_insights(transactions, balance)
        }
        
        return response
    
    def _handle_general_query(self, user_id: str, query: str) -> Dict[str, Any]:
        """Handle general queries"""
        return {
            "type": "general",
            "query": query,
            "response": "I can help you with spending analysis, budget tracking, predictions, anomaly detection, and goal setting. Try asking about your expenses, budget, or financial goals!",
            "suggestions": [
                "How much did I spend last month?",
                "Am I overspending on food?",
                "Predict my spending for next month",
                "Check for unusual transactions",
                "Help me save ₹50,000 in 6 months"
            ]
        }
    
    def _extract_time_period(self, query: str) -> str:
        """Extract time period from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['last week', 'past week']):
            return "last_week"
        elif any(word in query_lower for word in ['last month', 'past month']):
            return "last_month"
        elif any(word in query_lower for word in ['last 3 months', 'past 3 months']):
            return "last_3_months"
        elif any(word in query_lower for word in ['last year', 'past year']):
            return "last_year"
        elif any(word in query_lower for word in ['this week']):
            return "this_week"
        elif any(word in query_lower for word in ['this month']):
            return "this_month"
        else:
            return "all"
    
    def _extract_category(self, query: str) -> Optional[str]:
        """Extract category from query"""
        category_mapping = {
            'food': ['food', 'restaurant', 'dining', 'lunch', 'dinner', 'breakfast'],
            'transport': ['transport', 'uber', 'ola', 'taxi', 'bus', 'metro', 'petrol'],
            'shopping': ['shopping', 'amazon', 'flipkart', 'clothes', 'online'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'wifi'],
            'entertainment': ['movie', 'netflix', 'spotify', 'game', 'entertainment'],
            'healthcare': ['doctor', 'medicine', 'hospital', 'medical', 'pharmacy']
        }
        
        query_lower = query.lower()
        for category, keywords in category_mapping.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return None
    
    def _extract_amount(self, query: str) -> Optional[float]:
        """Extract amount from query"""
        # Look for patterns like "₹50,000", "50000", "50k", etc.
        patterns = [
            r'₹?(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rupees?|rs\.?)',
            r'(\d+)\s*k\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                amount_str = match.group(1)
                if 'k' in amount_str.lower():
                    return float(amount_str.replace('k', '').replace('K', '')) * 1000
                else:
                    return float(amount_str.replace(',', ''))
        
        return None
    
    def _extract_timeframe(self, query: str) -> Optional[str]:
        """Extract timeframe from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['next month', '1 month']):
            return "1_month"
        elif any(word in query_lower for word in ['next 3 months', '3 months']):
            return "3_months"
        elif any(word in query_lower for word in ['next 6 months', '6 months']):
            return "6_months"
        elif any(word in query_lower for word in ['next year', '1 year']):
            return "1_year"
        
        return None
    
    def _get_transactions(self, user_id: str, period: str) -> List[Transaction]:
        """Get transactions for specified period"""
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        
        if period != "all":
            end_date = datetime.now().date()
            
            if period == "last_week":
                start_date = end_date - timedelta(days=7)
            elif period == "last_month":
                start_date = end_date - timedelta(days=30)
            elif period == "last_3_months":
                start_date = end_date - timedelta(days=90)
            elif period == "last_year":
                start_date = end_date - timedelta(days=365)
            elif period == "this_week":
                start_date = end_date - timedelta(days=end_date.weekday())
            elif period == "this_month":
                start_date = end_date.replace(day=1)
            else:
                start_date = None
            
            if start_date:
                stmt = stmt.where(Transaction.date >= start_date)
        
        return self.session.exec(stmt).all()
    
    def _get_historical_average(self, user_id: str, period: str) -> float:
        """Get historical average spending for comparison"""
        transactions = self._get_transactions(user_id, period)
        expenses = [t.amount for t in transactions if t.type == 'expense']
        return sum(expenses) / len(expenses) if expenses else 0
    
    def _timeframe_to_months(self, timeframe: str) -> int:
        """Convert timeframe string to months"""
        mapping = {
            "1_month": 1,
            "3_months": 3,
            "6_months": 6,
            "1_year": 12
        }
        return mapping.get(timeframe, 1)
    
    def _generate_spending_insights(self, transactions: List[Transaction], total_spent: float) -> List[str]:
        """Generate spending insights"""
        insights = []
        
        if total_spent > 0:
            insights.append(f"You spent ₹{total_spent:,.2f} in the selected period")
            
            # Top category
            categories = {}
            for t in transactions:
                if t.type == 'expense':
                    categories[t.category] = categories.get(t.category, 0) + t.amount
            
            if categories:
                top_category = max(categories, key=categories.get)
                insights.append(f"Your highest spending category was {top_category} (₹{categories[top_category]:,.2f})")
        
        return insights
    
    def _generate_budget_recommendations(self, total_spent: float, budget: float, status: str) -> List[str]:
        """Generate budget recommendations"""
        recommendations = []
        
        if status == "over":
            overspend = total_spent - budget
            recommendations.append(f"You overspent by ₹{overspend:,.2f}")
            recommendations.append("Consider reducing discretionary expenses")
            recommendations.append("Review your spending categories to identify areas for cuts")
        else:
            savings = budget - total_spent
            recommendations.append(f"Great! You saved ₹{savings:,.2f}")
            recommendations.append("Consider investing the surplus amount")
        
        return recommendations
    
    def _generate_prediction_recommendations(self, forecast: List[float], budget_limit: Optional[float]) -> List[str]:
        """Generate prediction recommendations"""
        recommendations = []
        avg_predicted = sum(forecast) / len(forecast)
        
        recommendations.append(f"Your average predicted spending is ₹{avg_predicted:,.2f}")
        
        if budget_limit:
            if avg_predicted > budget_limit:
                recommendations.append("⚠️ You may exceed your budget based on current trends")
                recommendations.append("Consider reducing expenses or increasing your budget")
            else:
                recommendations.append("✅ Your spending is within budget limits")
        
        return recommendations
    
    def _generate_anomaly_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """Generate anomaly recommendations"""
        recommendations = []
        
        if anomalies:
            recommendations.append(f"Found {len(anomalies)} unusual transactions")
            recommendations.append("Review these transactions to ensure they're legitimate")
            recommendations.append("Consider setting up alerts for large transactions")
        else:
            recommendations.append("No unusual spending patterns detected")
            recommendations.append("Your spending appears consistent with your usual patterns")
        
        return recommendations
    
    def _generate_goal_recommendations(self, goal_amount: float, required_monthly: float, current_savings: float) -> List[str]:
        """Generate goal recommendations"""
        recommendations = []
        
        recommendations.append(f"To reach ₹{goal_amount:,.2f}, you need to save ₹{required_monthly:,.2f} monthly")
        
        if required_monthly > current_savings:
            shortfall = required_monthly - current_savings
            recommendations.append(f"You need to increase savings by ₹{shortfall:,.2f} monthly")
            recommendations.append("Consider reducing expenses or increasing income")
        else:
            recommendations.append("Your current savings rate is sufficient for this goal")
        
        return recommendations
    
    def _generate_summary_insights(self, transactions: List[Transaction], balance: float) -> List[str]:
        """Generate summary insights"""
        insights = []
        
        if balance > 0:
            insights.append(f"Your current balance is ₹{balance:,.2f}")
        else:
            insights.append(f"Your current balance is negative: ₹{balance:,.2f}")
        
        if transactions:
            insights.append(f"You have {len(transactions)} transactions in the selected period")
        
        return insights
    
    def _generate_goal_suggestions(self, user_id: str) -> List[str]:
        """Generate goal suggestions based on user's financial situation"""
        transactions = self._get_transactions(user_id, "all")
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        
        suggestions = [
            "Set up an emergency fund (3-6 months of expenses)",
            "Start a retirement savings plan",
            "Save for a major purchase or vacation",
            "Build an investment portfolio"
        ]
        
        if total_income > 0:
            monthly_income = total_income / 12  # Rough estimate
            suggestions.append(f"Consider saving 20% of your monthly income (₹{monthly_income * 0.2:,.2f})")
        
        return suggestions


class CategorizationAgent:
    """Enhanced expense categorization using DistilBERT"""
    
    def __init__(self):
        self.category_mapping = {
            'food': ['restaurant', 'dining', 'lunch', 'dinner', 'breakfast', 'meal', 'pizza', 'burger', 'cafe'],
            'groceries': ['grocery', 'supermarket', 'vegetables', 'fruits', 'market', 'food shopping'],
            'transport': ['uber', 'ola', 'taxi', 'bus', 'metro', 'train', 'petrol', 'fuel', 'auto', 'rickshaw'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'clothes', 'shopping', 'online', 'purchase', 'retail'],
            'utilities': ['electricity', 'water', 'gas', 'internet', 'wifi', 'phone', 'mobile', 'recharge'],
            'entertainment': ['movie', 'netflix', 'spotify', 'game', 'entertainment', 'fun', 'party', 'cinema'],
            'healthcare': ['doctor', 'medicine', 'hospital', 'medical', 'pharmacy', 'health', 'clinic'],
            'rent': ['rent', 'house rent', 'apartment', 'accommodation'],
            'salary': ['salary', 'pay', 'paycheck', 'wage', 'income'],
            'freelance': ['freelance', 'client', 'project', 'work', 'consulting']
        }
    
    def classify_transaction(self, description: str) -> str:
        """Classify transaction based on description"""
        description_lower = description.lower()
        
        # Use the existing ML function as fallback
        categories = categorize_descriptions([description])
        base_category = categories[0] if categories else "Other"
        
        # Enhanced classification using keyword matching
        for category, keywords in self.category_mapping.items():
            if any(keyword in description_lower for keyword in keywords):
                return category.title()
        
        return base_category
    
    def batch_classify(self, descriptions: List[str]) -> List[str]:
        """Classify multiple transactions"""
        return [self.classify_transaction(desc) for desc in descriptions]
    
    def correct_classification(self, transaction_id: int, new_category: str) -> Dict[str, Any]:
        """Handle classification corrections"""
        return {
            "transaction_id": transaction_id,
            "old_category": "Unknown",
            "new_category": new_category,
            "correction_applied": True,
            "message": f"Transaction reclassified to {new_category}"
        }


class PredictionAgent:
    """Spending prediction using LSTM models"""
    
    def __init__(self):
        self.model_loaded = False
    
    def predict_spending(self, user_id: str, historical_data: List[float], periods: int = 4) -> Dict[str, Any]:
        """Predict future spending patterns"""
        if len(historical_data) < 4:
            return {
                "error": "Insufficient data for prediction",
                "forecast": [],
                "confidence": 0
            }
        
        # Use existing forecast function
        forecast_values = forecast(historical_data, periods)
        
        # Calculate confidence based on data quality
        confidence = min(0.9, len(historical_data) / 20)  # More data = higher confidence
        
        return {
            "forecast": forecast_values,
            "confidence": confidence,
            "periods": periods,
            "average_predicted": sum(forecast_values) / len(forecast_values),
            "trend": self._calculate_trend(forecast_values)
        }
    
    def _calculate_trend(self, forecast: List[float]) -> str:
        """Calculate spending trend"""
        if len(forecast) < 2:
            return "stable"
        
        first_half = sum(forecast[:len(forecast)//2]) / (len(forecast)//2)
        second_half = sum(forecast[len(forecast)//2:]) / (len(forecast) - len(forecast)//2)
        
        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "stable"


class AnomalyAgent:
    """Anomaly detection using Isolation Forest"""
    
    def __init__(self):
        self.threshold = 0.1  # Sensitivity threshold
    
    def detect_anomalies(self, user_id: str, transactions: List[Transaction]) -> Dict[str, Any]:
        """Detect anomalous transactions"""
        if len(transactions) < 3:
            return {
                "anomalies": [],
                "anomaly_count": 0,
                "message": "Insufficient data for anomaly detection"
            }
        
        # Extract features for anomaly detection
        amounts = [t.amount for t in transactions]
        anomaly_indices = detect_anomalies(amounts)
        
        anomalies = []
        for idx in anomaly_indices:
            if idx < len(transactions):
                transaction = transactions[idx]
                anomalies.append({
                    "transaction": transaction,
                    "anomaly_score": self._calculate_anomaly_score(transaction, transactions),
                    "reason": self._explain_anomaly(transaction, transactions)
                })
        
        return {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "total_transactions": len(transactions),
            "anomaly_rate": len(anomalies) / len(transactions)
        }
    
    def _calculate_anomaly_score(self, transaction: Transaction, all_transactions: List[Transaction]) -> float:
        """Calculate anomaly score for a transaction"""
        amounts = [t.amount for t in all_transactions if t.type == transaction.type]
        if not amounts:
            return 0.0
        
        mean_amount = sum(amounts) / len(amounts)
        std_amount = (sum((x - mean_amount) ** 2 for x in amounts) / len(amounts)) ** 0.5
        
        if std_amount == 0:
            return 0.0
        
        z_score = abs(transaction.amount - mean_amount) / std_amount
        return min(1.0, z_score / 3.0)  # Normalize to 0-1
    
    def _explain_anomaly(self, transaction: Transaction, all_transactions: List[Transaction]) -> str:
        """Explain why a transaction is anomalous"""
        amounts = [t.amount for t in all_transactions if t.type == transaction.type]
        if not amounts:
            return "No similar transactions for comparison"
        
        mean_amount = sum(amounts) / len(amounts)
        
        if transaction.amount > mean_amount * 2:
            return f"Amount (₹{transaction.amount:,.2f}) is significantly higher than average (₹{mean_amount:,.2f})"
        elif transaction.amount < mean_amount * 0.5:
            return f"Amount (₹{transaction.amount:,.2f}) is significantly lower than average (₹{mean_amount:,.2f})"
        else:
            return "Transaction pattern differs from usual spending behavior"


class GoalSettingAgent:
    """Goal setting and recommendation agent"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_savings_goal(self, user_id: str, goal_amount: float, timeframe_months: int) -> Dict[str, Any]:
        """Create a savings goal"""
        # Get user's financial data
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = self.session.exec(stmt).all()
        
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        current_savings = total_income - total_expenses
        
        # Calculate required monthly savings
        required_monthly = goal_amount / timeframe_months if timeframe_months > 0 else 0
        
        # Assess feasibility
        monthly_income = total_income / 12 if total_income > 0 else 0
        max_feasible_savings = monthly_income * 0.3  # Assume max 30% savings rate
        feasible = required_monthly <= max_feasible_savings
        
        # Generate recommendations
        recommendations = self._generate_savings_recommendations(
            goal_amount, required_monthly, current_savings, monthly_income
        )
        
        return {
            "goal_amount": goal_amount,
            "timeframe_months": timeframe_months,
            "required_monthly_savings": required_monthly,
            "current_savings": current_savings,
            "monthly_income": monthly_income,
            "feasible": feasible,
            "recommendations": recommendations,
            "progress": 0.0  # New goal, no progress yet
        }
    
    def get_expense_reduction_suggestions(self, user_id: str, target_reduction_percent: float) -> Dict[str, Any]:
        """Get suggestions for reducing expenses"""
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = self.session.exec(stmt).all()
        
        # Analyze spending by category
        categories = {}
        for t in transactions:
            if t.type == 'expense':
                categories[t.category] = categories.get(t.category, 0) + t.amount
        
        total_expenses = sum(categories.values())
        target_reduction = total_expenses * (target_reduction_percent / 100)
        
        # Sort categories by amount
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        suggestions = []
        for category, amount in sorted_categories:
            if amount > target_reduction / len(sorted_categories):
                reduction_needed = min(amount * 0.2, target_reduction / len(sorted_categories))
                suggestions.append({
                    "category": category,
                    "current_spending": amount,
                    "suggested_reduction": reduction_needed,
                    "tips": self._get_category_tips(category)
                })
        
        return {
            "target_reduction_percent": target_reduction_percent,
            "target_reduction_amount": target_reduction,
            "current_total_expenses": total_expenses,
            "suggestions": suggestions
        }
    
    def _generate_savings_recommendations(self, goal_amount: float, required_monthly: float, 
                                        current_savings: float, monthly_income: float) -> List[str]:
        """Generate savings recommendations"""
        recommendations = []
        
        recommendations.append(f"To reach ₹{goal_amount:,.2f}, save ₹{required_monthly:,.2f} monthly")
        
        if required_monthly > monthly_income * 0.2:
            recommendations.append("Consider extending your timeline or reducing the goal amount")
        
        if current_savings < 0:
            recommendations.append("First focus on eliminating debt before saving")
        elif current_savings > 0:
            recommendations.append("Great! You already have some savings to build upon")
        
        recommendations.append("Set up automatic transfers to a separate savings account")
        recommendations.append("Review and reduce discretionary expenses")
        
        return recommendations
    
    def _get_category_tips(self, category: str) -> List[str]:
        """Get tips for reducing expenses in a specific category"""
        tips_mapping = {
            'food': [
                "Cook more meals at home",
                "Use grocery shopping lists to avoid impulse purchases",
                "Look for discounts and coupons",
                "Buy generic brands when possible"
            ],
            'transport': [
                "Use public transportation when possible",
                "Carpool for regular commutes",
                "Walk or bike for short distances",
                "Compare fuel prices before filling up"
            ],
            'entertainment': [
                "Look for free or low-cost entertainment options",
                "Share streaming subscriptions with family/friends",
                "Take advantage of student/senior discounts",
                "Set a monthly entertainment budget"
            ],
            'shopping': [
                "Wait 24 hours before making non-essential purchases",
                "Compare prices across different stores",
                "Use cashback and reward programs",
                "Buy only what you need, avoid impulse purchases"
            ]
        }
        
        return tips_mapping.get(category.lower(), [
            "Review your spending in this category",
            "Look for ways to reduce costs",
            "Consider if all expenses are necessary"
        ])


class RiskAssessmentAgent:
    """Comprehensive risk assessment agent"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def comprehensive_risk_assessment(self, user_id: str) -> Dict[str, Any]:
        """Comprehensive risk analysis across all dimensions"""
        try:
            # Get user's financial data
            stmt = select(Transaction).where(Transaction.user_id == user_id)
            transactions = self.session.exec(stmt).all()
            
            if not transactions:
                return {
                    "error": "Insufficient data for risk assessment",
                    "recommendations": ["Add more transactions to enable risk analysis"]
                }
            
            # Calculate financial metrics
            total_income = sum(t.amount for t in transactions if t.type == 'income')
            total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
            monthly_income = total_income / 12 if total_income > 0 else 0
            monthly_expenses = total_expenses / 12 if total_expenses > 0 else 0
            
            # Risk assessments
            credit_risk = self._assess_credit_risk(transactions, monthly_income, monthly_expenses)
            liquidity_risk = self._assess_liquidity_risk(transactions, monthly_income, monthly_expenses)
            market_risk = self._assess_market_risk(transactions)
            operational_risk = self._assess_operational_risk(transactions)
            
            # Overall risk score
            overall_risk = self._calculate_overall_risk(credit_risk, liquidity_risk, market_risk, operational_risk)
            
            return {
                "overall_risk_score": overall_risk,
                "risk_level": self._get_risk_level(overall_risk),
                "credit_risk": credit_risk,
                "liquidity_risk": liquidity_risk,
                "market_risk": market_risk,
                "operational_risk": operational_risk,
                "recommendations": self._generate_risk_recommendations(overall_risk, credit_risk, liquidity_risk, market_risk, operational_risk)
            }
        except Exception as e:
            return {"error": f"Risk assessment failed: {str(e)}"}
    
    def _assess_credit_risk(self, transactions: List[Transaction], monthly_income: float, monthly_expenses: float) -> Dict[str, Any]:
        """Assess credit risk and debt management"""
        # Calculate debt-to-income ratio (simplified)
        dti_ratio = monthly_expenses / monthly_income if monthly_income > 0 else 0
        
        # Analyze payment patterns
        payment_consistency = self._analyze_payment_consistency(transactions)
        
        # Estimate credit score
        credit_score = self._estimate_credit_score(dti_ratio, payment_consistency)
        
        return {
            "dti_ratio": dti_ratio,
            "payment_consistency": payment_consistency,
            "estimated_credit_score": credit_score,
            "risk_level": "high" if dti_ratio > 0.4 else "medium" if dti_ratio > 0.2 else "low"
        }
    
    def _assess_liquidity_risk(self, transactions: List[Transaction], monthly_income: float, monthly_expenses: float) -> Dict[str, Any]:
        """Assess liquidity and emergency fund adequacy"""
        # Calculate emergency fund months
        emergency_fund_months = 3  # Default assumption
        if monthly_expenses > 0:
            # Estimate emergency fund based on savings pattern
            savings_rate = (monthly_income - monthly_expenses) / monthly_income if monthly_income > 0 else 0
            emergency_fund_months = min(6, max(0, savings_rate * 12))
        
        # Analyze income stability
        income_stability = self._analyze_income_stability(transactions)
        
        return {
            "emergency_fund_months": emergency_fund_months,
            "income_stability": income_stability,
            "liquidity_ratio": monthly_income / monthly_expenses if monthly_expenses > 0 else 0,
            "risk_level": "high" if emergency_fund_months < 1 else "medium" if emergency_fund_months < 3 else "low"
        }
    
    def _assess_market_risk(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Assess market and investment risks"""
        # Analyze spending volatility
        expense_amounts = [t.amount for t in transactions if t.type == 'expense']
        spending_volatility = self._calculate_volatility(expense_amounts) if expense_amounts else 0
        
        # Diversification analysis (simplified)
        categories = [t.category for t in transactions if t.type == 'expense']
        diversification_score = len(set(categories)) / max(len(categories), 1)
        
        return {
            "spending_volatility": spending_volatility,
            "diversification_score": diversification_score,
            "market_exposure": "low",  # Simplified
            "risk_level": "high" if spending_volatility > 0.5 else "medium" if spending_volatility > 0.2 else "low"
        }
    
    def _assess_operational_risk(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Assess operational and behavioral risks"""
        # Analyze spending patterns
        spending_consistency = self._analyze_spending_consistency(transactions)
        
        # Financial discipline score
        financial_discipline = self._calculate_financial_discipline(transactions)
        
        # Goal achievement rate (simplified)
        goal_achievement_rate = 0.7  # Default assumption
        
        return {
            "spending_consistency": spending_consistency,
            "financial_discipline": financial_discipline,
            "goal_achievement_rate": goal_achievement_rate,
            "risk_level": "high" if financial_discipline < 0.5 else "medium" if financial_discipline < 0.7 else "low"
        }
    
    def _analyze_payment_consistency(self, transactions: List[Transaction]) -> float:
        """Analyze payment consistency"""
        if len(transactions) < 2:
            return 0.5
        
        # Calculate variance in transaction amounts
        amounts = [t.amount for t in transactions]
        mean_amount = sum(amounts) / len(amounts)
        variance = sum((x - mean_amount) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5
        
        # Consistency score (lower std dev = higher consistency)
        consistency = max(0, 1 - (std_dev / mean_amount)) if mean_amount > 0 else 0
        return min(1, consistency)
    
    def _estimate_credit_score(self, dti_ratio: float, payment_consistency: float) -> int:
        """Estimate credit score based on financial behavior"""
        base_score = 650
        
        # Adjust based on DTI ratio
        if dti_ratio < 0.2:
            base_score += 50
        elif dti_ratio > 0.4:
            base_score -= 100
        
        # Adjust based on payment consistency
        base_score += int(payment_consistency * 100)
        
        return max(300, min(850, base_score))
    
    def _analyze_income_stability(self, transactions: List[Transaction]) -> float:
        """Analyze income stability"""
        income_transactions = [t for t in transactions if t.type == 'income']
        if len(income_transactions) < 2:
            return 0.5
        
        # Calculate income variance
        amounts = [t.amount for t in income_transactions]
        mean_income = sum(amounts) / len(amounts)
        variance = sum((x - mean_income) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5
        
        # Stability score (lower std dev = higher stability)
        stability = max(0, 1 - (std_dev / mean_income)) if mean_income > 0 else 0
        return min(1, stability)
    
    def _calculate_volatility(self, amounts: List[float]) -> float:
        """Calculate volatility of amounts"""
        if len(amounts) < 2:
            return 0
        
        mean_amount = sum(amounts) / len(amounts)
        variance = sum((x - mean_amount) ** 2 for x in amounts) / len(amounts)
        std_dev = variance ** 0.5
        
        return std_dev / mean_amount if mean_amount > 0 else 0
    
    def _analyze_spending_consistency(self, transactions: List[Transaction]) -> float:
        """Analyze spending consistency"""
        expense_transactions = [t for t in transactions if t.type == 'expense']
        if len(expense_transactions) < 2:
            return 0.5
        
        # Group by month and calculate monthly spending
        monthly_spending = {}
        for t in expense_transactions:
            month_key = t.date.strftime('%Y-%m')
            monthly_spending[month_key] = monthly_spending.get(month_key, 0) + t.amount
        
        if len(monthly_spending) < 2:
            return 0.5
        
        # Calculate consistency
        amounts = list(monthly_spending.values())
        return self._calculate_volatility(amounts)
    
    def _calculate_financial_discipline(self, transactions: List[Transaction]) -> float:
        """Calculate financial discipline score"""
        if not transactions:
            return 0.5
        
        # Factors: savings rate, spending control, goal achievement
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        
        if total_income == 0:
            return 0.5
        
        savings_rate = (total_income - total_expenses) / total_income
        spending_control = 1 - min(1, total_expenses / total_income)
        
        # Combine factors
        discipline = (savings_rate + spending_control) / 2
        return max(0, min(1, discipline))
    
    def _calculate_overall_risk(self, credit_risk: Dict, liquidity_risk: Dict, market_risk: Dict, operational_risk: Dict) -> float:
        """Calculate overall risk score"""
        risk_scores = []
        
        # Convert risk levels to scores
        risk_level_scores = {"low": 0.2, "medium": 0.5, "high": 0.8}
        
        risk_scores.append(risk_level_scores.get(credit_risk["risk_level"], 0.5))
        risk_scores.append(risk_level_scores.get(liquidity_risk["risk_level"], 0.5))
        risk_scores.append(risk_level_scores.get(market_risk["risk_level"], 0.5))
        risk_scores.append(risk_level_scores.get(operational_risk["risk_level"], 0.5))
        
        return sum(risk_scores) / len(risk_scores)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level from score"""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.6:
            return "medium"
        else:
            return "high"
    
    def _generate_risk_recommendations(self, overall_risk: float, credit_risk: Dict, liquidity_risk: Dict, market_risk: Dict, operational_risk: Dict) -> List[str]:
        """Generate risk mitigation recommendations"""
        recommendations = []
        
        if overall_risk > 0.6:
            recommendations.append("🚨 High overall risk detected. Consider comprehensive financial review.")
        
        if credit_risk["risk_level"] == "high":
            recommendations.append("💳 High credit risk: Reduce debt-to-income ratio below 40%")
            recommendations.append("📊 Improve payment consistency to boost credit score")
        
        if liquidity_risk["risk_level"] == "high":
            recommendations.append("💰 Build emergency fund to cover 3-6 months of expenses")
            recommendations.append("📈 Increase income stability through diversification")
        
        if market_risk["risk_level"] == "high":
            recommendations.append("📊 Reduce spending volatility for better financial stability")
            recommendations.append("🎯 Diversify expense categories to reduce concentration risk")
        
        if operational_risk["risk_level"] == "high":
            recommendations.append("🎯 Improve financial discipline and goal achievement")
            recommendations.append("📝 Create and stick to a budget plan")
        
        if not recommendations:
            recommendations.append("✅ Your financial risk profile looks healthy!")
            recommendations.append("💡 Continue monitoring and maintain good financial habits")
        
        return recommendations


class PredictiveAnalyticsAgent:
    """Advanced predictive analytics agent"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def comprehensive_prediction(self, user_id: str) -> Dict[str, Any]:
        """Comprehensive predictive analysis"""
        try:
            # Get user's financial data
            stmt = select(Transaction).where(Transaction.user_id == user_id)
            transactions = self.session.exec(stmt).all()
            
            if len(transactions) < 4:
                return {
                    "error": "Insufficient data for predictions. Need at least 4 transactions.",
                    "recommendations": ["Add more transactions to enable predictive analytics"]
                }
            
            # Predictions
            life_events = self._predict_life_events(transactions)
            financial_trajectory = self._predict_financial_trajectory(transactions)
            market_impact = self._predict_market_impact(transactions)
            scenario_analysis = self._run_scenario_analysis(transactions)
            
            return {
                "life_events": life_events,
                "financial_trajectory": financial_trajectory,
                "market_impact": market_impact,
                "scenario_analysis": scenario_analysis,
                "recommendations": self._generate_prediction_recommendations(life_events, financial_trajectory)
            }
        except Exception as e:
            return {"error": f"Prediction analysis failed: {str(e)}"}
    
    def _predict_life_events(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Predict major life events"""
        # Analyze spending patterns for life event indicators
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        
        # Marriage prediction (simplified)
        marriage_probability = 0.3  # Default
        if total_income > 50000:  # Higher income = higher marriage probability
            marriage_probability += 0.2
        
        # Children prediction
        children_probability = 0.2  # Default
        if total_income > 40000:  # Financial stability indicator
            children_probability += 0.1
        
        # Home purchase prediction
        home_purchase_probability = 0.25  # Default
        savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
        if savings_rate > 0.2:  # Good savings rate
            home_purchase_probability += 0.2
        
        return {
            "marriage": {
                "probability": min(1, marriage_probability),
                "timeline": "2-5 years",
                "financial_impact": total_income * 0.3,  # 30% of income
                "preparation_needed": "Wedding fund, joint account planning"
            },
            "children": {
                "probability": min(1, children_probability),
                "timeline": "3-7 years",
                "financial_impact": total_income * 0.4,  # 40% of income
                "preparation_needed": "Childcare fund, education savings"
            },
            "home_purchase": {
                "probability": min(1, home_purchase_probability),
                "timeline": "1-4 years",
                "financial_impact": total_income * 2,  # 2x annual income
                "preparation_needed": "Down payment, mortgage pre-approval"
            }
        }
    
    def _predict_financial_trajectory(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Predict financial trajectory"""
        # Calculate trends
        income_trend = self._calculate_trend([t.amount for t in transactions if t.type == 'income'])
        expense_trend = self._calculate_trend([t.amount for t in transactions if t.type == 'expense'])
        
        # Predict next 12 months
        current_income = sum(t.amount for t in transactions if t.type == 'income') / 12
        current_expenses = sum(t.amount for t in transactions if t.type == 'expense') / 12
        
        monthly_projections = []
        for month in range(1, 13):
            projected_income = current_income * (1 + income_trend * month)
            projected_expenses = current_expenses * (1 + expense_trend * month)
            monthly_projections.append({
                "month": month,
                "projected_income": projected_income,
                "projected_expenses": projected_expenses,
                "projected_savings": projected_income - projected_expenses
            })
        
        return {
            "income_trend": income_trend,
            "expense_trend": expense_trend,
            "monthly_projections": monthly_projections,
            "annual_projection": {
                "total_income": sum(p["projected_income"] for p in monthly_projections),
                "total_expenses": sum(p["projected_expenses"] for p in monthly_projections),
                "total_savings": sum(p["projected_savings"] for p in monthly_projections)
            }
        }
    
    def _predict_market_impact(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Predict market impact on finances"""
        # Simplified market impact analysis
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        
        return {
            "inflation_impact": {
                "current_rate": 0.05,  # 5% inflation
                "annual_impact": total_income * 0.05,
                "recommendation": "Invest in inflation-protected assets"
            },
            "interest_rate_impact": {
                "current_rate": 0.06,  # 6% interest
                "savings_opportunity": total_income * 0.1 * 0.06,  # 10% savings at 6%
                "recommendation": "Consider high-yield savings accounts"
            },
            "market_volatility": {
                "risk_level": "medium",
                "recommendation": "Diversify investments across asset classes"
            }
        }
    
    def _run_scenario_analysis(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Run scenario analysis"""
        base_income = sum(t.amount for t in transactions if t.type == 'income') / 12
        base_expenses = sum(t.amount for t in transactions if t.type == 'expense') / 12
        
        scenarios = {
            "optimistic": {
                "income_change": 0.15,  # 15% increase
                "expense_change": 0.05,  # 5% increase
                "description": "Best case scenario with income growth"
            },
            "realistic": {
                "income_change": 0.05,  # 5% increase
                "expense_change": 0.03,  # 3% increase
                "description": "Most likely scenario"
            },
            "pessimistic": {
                "income_change": -0.05,  # 5% decrease
                "expense_change": 0.08,  # 8% increase
                "description": "Worst case scenario"
            }
        }
        
        scenario_results = {}
        for scenario_name, scenario in scenarios.items():
            new_income = base_income * (1 + scenario["income_change"])
            new_expenses = base_expenses * (1 + scenario["expense_change"])
            scenario_results[scenario_name] = {
                "monthly_income": new_income,
                "monthly_expenses": new_expenses,
                "monthly_savings": new_income - new_expenses,
                "description": scenario["description"]
            }
        
        return scenario_results
    
    def _calculate_trend(self, amounts: List[float]) -> float:
        """Calculate trend in amounts"""
        if len(amounts) < 2:
            return 0
        
        # Simple linear trend calculation
        n = len(amounts)
        x = list(range(n))
        y = amounts
        
        # Calculate slope
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Normalize by average
        avg_y = sum_y / n
        return slope / avg_y if avg_y > 0 else 0
    
    def _generate_prediction_recommendations(self, life_events: Dict, financial_trajectory: Dict) -> List[str]:
        """Generate prediction-based recommendations"""
        recommendations = []
        
        # Life event recommendations
        for event, data in life_events.items():
            if data["probability"] > 0.5:
                recommendations.append(f"🎯 High probability of {event}: {data['preparation_needed']}")
        
        # Financial trajectory recommendations
        if financial_trajectory["income_trend"] > 0.1:
            recommendations.append("📈 Strong income growth predicted - consider investment opportunities")
        elif financial_trajectory["income_trend"] < -0.05:
            recommendations.append("📉 Income decline predicted - focus on expense reduction")
        
        if financial_trajectory["expense_trend"] > 0.1:
            recommendations.append("💰 Expense growth high - review and optimize spending")
        
        # Savings recommendations
        annual_savings = financial_trajectory["annual_projection"]["total_savings"]
        if annual_savings > 0:
            recommendations.append(f"💎 Projected annual savings: ₹{annual_savings:,.2f} - consider investment options")
        else:
            recommendations.append("⚠️ Negative savings projected - urgent expense review needed")
        
        return recommendations


class NotificationAgent:
    """Proactive notification and alert agent"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def check_spending_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Check for spending alerts and notifications"""
        alerts = []
        
        # Get recent transactions
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = self.session.exec(stmt).all()
        
        if not transactions:
            return alerts
        
        # Check for unusual spending patterns
        recent_transactions = [t for t in transactions if t.date >= datetime.now().date() - timedelta(days=7)]
        
        if recent_transactions:
            # Compare with previous week
            previous_week = [t for t in transactions 
                           if datetime.now().date() - timedelta(days=14) <= t.date < datetime.now().date() - timedelta(days=7)]
            
            if previous_week:
                current_week_spending = sum(t.amount for t in recent_transactions if t.type == 'expense')
                previous_week_spending = sum(t.amount for t in previous_week if t.type == 'expense')
                
                if current_week_spending > previous_week_spending * 1.5:
                    alerts.append({
                        "type": "spending_increase",
                        "message": f"You spent ₹{current_week_spending:,.2f} this week, compared to ₹{previous_week_spending:,.2f} last week",
                        "severity": "medium",
                        "suggestion": "Review your recent expenses to identify areas for reduction"
                    })
        
        # Check for high-value transactions
        high_value_threshold = 10000  # ₹10,000
        high_value_transactions = [t for t in recent_transactions 
                                 if t.type == 'expense' and t.amount > high_value_threshold]
        
        for transaction in high_value_transactions:
            alerts.append({
                "type": "high_value_transaction",
                "message": f"Large expense detected: ₹{transaction.amount:,.2f} for {transaction.category}",
                "severity": "high",
                "transaction": transaction,
                "suggestion": "Verify this transaction and consider if it was necessary"
            })
        
        # Check for negative balance
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        balance = total_income - total_expenses
        
        if balance < 0:
            alerts.append({
                "type": "negative_balance",
                "message": f"Your balance is negative: ₹{balance:,.2f}",
                "severity": "high",
                "suggestion": "Consider reducing expenses or increasing income immediately"
            })
        
        return alerts
    
    def generate_weekly_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate weekly insights and recommendations"""
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = self.session.exec(stmt).all()
        
        # Get this week's transactions
        this_week = [t for t in transactions 
                    if t.date >= datetime.now().date() - timedelta(days=7)]
        
        if not this_week:
            return {
                "message": "No transactions this week",
                "insights": [],
                "recommendations": []
            }
        
        # Calculate spending by category
        categories = {}
        for t in this_week:
            if t.type == 'expense':
                categories[t.category] = categories.get(t.category, 0) + t.amount
        
        total_spending = sum(categories.values())
        
        # Generate insights
        insights = []
        if categories:
            top_category = max(categories, key=categories.get)
            insights.append(f"Your top spending category this week was {top_category} (₹{categories[top_category]:,.2f})")
        
        insights.append(f"Total spending this week: ₹{total_spending:,.2f}")
        
        # Generate recommendations
        recommendations = []
        if total_spending > 0:
            recommendations.append("Review your spending categories to identify areas for improvement")
            recommendations.append("Consider setting weekly spending limits for discretionary categories")
        
        return {
            "week_start": (datetime.now().date() - timedelta(days=7)).isoformat(),
            "week_end": datetime.now().date().isoformat(),
            "total_spending": total_spending,
            "category_breakdown": categories,
            "insights": insights,
            "recommendations": recommendations
        }
    
    def send_notification(self, user_id: str, notification: Dict[str, Any]) -> bool:
        """Send notification to user (placeholder for actual implementation)"""
        # In a real implementation, this would integrate with:
        # - Email services
        # - SMS services  
        # - Push notifications
        # - WebSocket connections
        
        print(f"Notification for {user_id}: {notification}")
        return True
