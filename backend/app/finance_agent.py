"""
Savion Finance Assistant — Optimized Gemini + Interactive Goal Support
"""
import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai
from sqlmodel import select, Session
from .models import Transaction

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class FinanceAgent:
    """Smart AI-based financial assistant with Gemini"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.pending_goal_inputs: Dict[str, Dict[str, Any]] = {}
        self.conversation_contexts: Dict[str, List[Dict[str, str]]] = {}

        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            print("✅ Gemini model initialized successfully (gemini-2.0-flash).")
        except Exception as e:
            print(f"⚠️ Gemini initialization failed: {e}")
            self.model = None

    # ---------- Transaction Analysis ----------
    async def analyze_transactions(self, transactions: List[Transaction]) -> Dict[str, Any]:
        if not transactions:
            return {"message": "No transactions available"}

        df = pd.DataFrame([t.dict() for t in transactions])
        if "amount" not in df.columns or df.empty:
            return {"message": "Invalid transaction data"}

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])

        total_spent = df["amount"].sum()
        avg_transaction = df["amount"].mean()

        # Category-wise summary
        cat_summary = (
            df.groupby("category")["amount"]
            .agg(["sum", "count"])
            .reset_index()
            .to_dict(orient="records")
        )

        # Daily summary (convert Timestamp → str)
        daily = (
            df.groupby(df["date"].dt.date)["amount"]
            .sum()
            .reset_index()
            .rename(columns={"date": "day", "amount": "total"})
        )
        daily["day"] = daily["day"].astype(str)

        return {
            "total_spent": float(total_spent),
            "avg_transaction": float(avg_transaction),
            "category_summary": cat_summary,
            "daily_spending": daily.to_dict(orient="records"),
        }

    # ---------- Intent Detection ----------
    def detect_intent(self, query: str) -> str:
        query = query.lower()
        if "analy" in query:
            return "analyze_data"
        if "spending summary" in query or "summary" in query:
            return "spending_summary"
        if "overspend" in query:
            return "budget_check"
        if "predict" in query:
            return "predict_spending"
        if "unusual" in query or "suspicious" in query:
            return "find_anomalies"
        if "goal" in query or "save" in query:
            return "set_goal"
        if "invest" in query or "investment" in query:
            return "investment_advice"
        return "general"

    # ---------- Query Processing ----------
    async def process_query(self, user_id: str, query: str, session: Session) -> Dict[str, Any]:
        try:
            stmt = select(Transaction).where(Transaction.user_id == user_id)
            transactions = session.exec(stmt).all()
            analysis = await self.analyze_transactions(transactions)
            intent = self.detect_intent(query)

            # Handle continued goal setup
            if user_id in self.pending_goal_inputs:
                return self._continue_goal_setup(user_id, query)

            # Handle intents
            if intent == "analyze_data":
                return self._analyze_data_response(analysis)

            elif intent == "spending_summary":
                return self._spending_summary(analysis)

            elif intent == "budget_check":
                return self._budget_check(analysis)

            elif intent == "predict_spending":
                return self._predict_spending(analysis)

            elif intent == "find_anomalies":
                return self._find_anomalies(analysis)

            elif intent == "set_goal":
                return self._handle_goal_setup(user_id, query)

            elif intent == "investment_advice":
                return self._investment_advice(analysis)

            else:
                return {"type": "ai_response", "response": "Please specify what you'd like to do 📊"}

        except Exception as e:
            print(f"❌ Error processing query: {e}")
            return {"type": "error", "response": f"Error processing your request: {e}"}

    # ---------- Intent Handlers ----------
    def _analyze_data_response(self, analysis):
        total = analysis.get("total_spent", 0)
        avg = analysis.get("avg_transaction", 0)
        cats = analysis.get("category_summary", [])
        top_cats = sorted(cats, key=lambda x: x["sum"], reverse=True)[:2]
        top_str = ", ".join([f"{c['category']} (₹{c['sum']:.0f})" for c in top_cats])
        return {
            "type": "ai_response",
            "response": f"📊 Data Analysis\n• Total: ₹{total:.0f}\n• Avg: ₹{avg:.0f}\n• Top: {top_str}",
        }

    def _spending_summary(self, analysis):
        now = datetime.now()
        df = pd.DataFrame(analysis.get("daily_spending", []))
        if df.empty:
            return {"type": "ai_response", "response": "No spending data for this month."}
        df["day"] = pd.to_datetime(df["day"])
        monthly = df[df["day"].dt.month == now.month]["total"].sum()
        return {
            "type": "ai_response",
            "response": f"💰 Spending Summary\n• This month: ₹{monthly:.0f}",
        }

    def _budget_check(self, analysis):
        total = analysis.get("total_spent", 0)
        avg = analysis.get("avg_transaction", 0)
        return {
            "type": "ai_response",
            "response": f"🎯 Budget Check\n• Total spent: ₹{total:.0f}\n• Avg: ₹{avg:.0f}\nYou're spending steadily.",
        }

    def _predict_spending(self, analysis):
        avg = analysis.get("avg_transaction", 0)
        total = analysis.get("total_spent", 0)
        est = total / 12 if total else 0
        return {
            "type": "ai_response",
            "response": f"🔮 Predict Spending\nNext month estimated: ₹{est:.0f} (based on averages).",
        }

    def _find_anomalies(self, analysis):
        df = pd.DataFrame(analysis.get("daily_spending", []))
        if df.empty:
            return {"type": "ai_response", "response": "No transactions found."}
        df["day"] = pd.to_datetime(df["day"])
        threshold = df["total"].mean() + 2 * df["total"].std()
        anomalies = df[df["total"] > threshold]
        if anomalies.empty:
            return {"type": "ai_response", "response": "🚨 No unusual transactions found."}
        tops = ", ".join([f"{row['day'].strftime('%Y-%m-%d')} (₹{row['total']:.0f})" for _, row in anomalies.iterrows()])
        return {"type": "ai_response", "response": f"🚨 Unusual days: {tops}"}

    def _handle_goal_setup(self, user_id: str, query: str):
        goal_match = re.search(r"₹?(\d+(?:,\d{3})*)", query)
        months_match = re.search(r"(\d+)\s*month", query)

        if not goal_match and not months_match:
            self.pending_goal_inputs[user_id] = {}
            return {"type": "ai_response", "response": "💎 How much would you like to save, and in how many months?"}

        if goal_match and not months_match:
            goal_amount = float(goal_match.group(1).replace(",", ""))
            self.pending_goal_inputs[user_id] = {"goal_amount": goal_amount}
            return {"type": "ai_response", "response": f"Got it! You want to save ₹{goal_amount:,.0f}. For how many months?"}

        if months_match and not goal_match:
            months = int(months_match.group(1))
            self.pending_goal_inputs[user_id] = {"months": months}
            return {"type": "ai_response", "response": f"Cool! For {months} months — how much do you want to save?"}

        # Both provided
        goal_amount = float(goal_match.group(1).replace(",", ""))
        months = int(months_match.group(1))
        return self._generate_goal_plan(user_id, goal_amount, months)

    def _continue_goal_setup(self, user_id: str, query: str):
        stored = self.pending_goal_inputs[user_id]
        goal_match = re.search(r"₹?(\d+(?:,\d{3})*)", query)
        months_match = re.search(r"(\d+)\s*month", query)
        goal_amount = float(goal_match.group(1).replace(",", "")) if goal_match else stored.get("goal_amount")
        months = int(months_match.group(1)) if months_match else stored.get("months")

        if goal_amount and months:
            return self._generate_goal_plan(user_id, goal_amount, months)
        else:
            return {"type": "ai_response", "response": "Please specify both the amount and duration (e.g., ₹50,000 in 6 months)."}

    def _generate_goal_plan(self, user_id: str, goal_amount: float, months: int):
        monthly_target = round(goal_amount / months, 2)
        weekly_target = round(goal_amount / (months * 4), 2)
        self.pending_goal_inputs.pop(user_id, None)
        return {
            "type": "ai_response",
            "response": (
                f"💎 Savings Plan\n"
                f"• Goal: ₹{goal_amount:,.0f} in {months} months\n"
                f"• Save ₹{monthly_target:,.0f}/month (₹{weekly_target:,.0f}/week)\n"
                f"• Tip: Reduce non-essential spending by 10%."
            ),
        }

    def _investment_advice(self, analysis):
        cats = analysis.get("category_summary", [])
        if not cats:
            return {"type": "ai_response", "response": "📈 No spending data to analyze investments."}
        top_expense = sorted(cats, key=lambda x: x["sum"], reverse=True)[0]
        return {
            "type": "ai_response",
            "response": (
                f"📈 Investment Advice\n"
                f"Your major expense is {top_expense['category']} (₹{top_expense['sum']:.0f}). "
                f"Try allocating 20% of your monthly surplus into SIPs or fixed deposits."
            ),
        }

    # ---------- Clear Chat ----------
    def clear_conversation_history(self, user_id: str):
        self.conversation_contexts.pop(user_id, None)
        self.pending_goal_inputs.pop(user_id, None)
        print(f"🧹 Cleared context for {user_id}")


# Singleton
_finance_agent = None


def get_finance_agent() -> FinanceAgent:
    global _finance_agent
    if _finance_agent is None:
        _finance_agent = FinanceAgent()
    return _finance_agent
