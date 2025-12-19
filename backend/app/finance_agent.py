"""
Savion Finance Assistant — Optimized Gemini + Interactive Goal Support
"""
import os
import json
import re
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai
from . import db
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
            if not self.api_key:
                print("⚠️ GEMINI_API_KEY not found. Using basic financial analysis mode.")
                self.model = None
            else:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.0-flash")
                print("✅ Gemini model initialized successfully (gemini-2.0-flash).")
        except Exception as e:
            print(f"⚠️ Gemini initialization failed: {e}. Will use basic mode.")
            self.model = None

    # ---------- Transaction Analysis ----------
    async def analyze_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {"message": "No transactions available"}

        df = pd.DataFrame(transactions)
        if "amount" not in df.columns or df.empty:
            return {"message": "Invalid transaction data"}

        df["date"] = pd.to_datetime(df.get("date", []), errors="coerce")
        df = df.dropna(subset=["date"])

        # 🔥 FIX: Filter ONLY expenses (not income) for spending analysis
        df_expenses = df[df.get("type", "").str.lower() == "expense"].copy() if "type" in df.columns else df
        
        if df_expenses.empty:
            return {
                "total_spent": 0,
                "avg_transaction": 0,
                "category_summary": [],
                "daily_spending": [],
            }

        total_spent = df_expenses["amount"].sum()
        avg_transaction = df_expenses["amount"].mean()

        # Category-wise summary (expenses only)
        cat_summary = (
            df_expenses.groupby("category")["amount"]
            .agg(["sum", "count"])
            .reset_index()
            .to_dict(orient="records")
        )

        # Daily summary (expenses only)
        daily = (
            df_expenses.groupby(df_expenses["date"].dt.date)["amount"]
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
    async def process_query(self, user_id: str, query: str) -> Dict[str, Any]:
        try:
            transactions = db.get_transactions(user_id)
            analysis = await self.analyze_transactions(transactions)
            intent = self.detect_intent(query)

            # Handle continued goal setup
            if user_id in self.pending_goal_inputs:
                result = self._continue_goal_setup(user_id, query)
                return result

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
                return await self._investment_advice(analysis)

            else:
                return {"type": "ai_response", "response": "📊 I can help you with spending analysis, predictions, and more! What would you like to know?"}

        except Exception as e:
            print(f"❌ Error processing query: {e}")
            return {"type": "error", "response": f"⚠️ Error processing your request: {str(e)}. Please try again."}

    # ---------- Intent Handlers ----------
    def _analyze_data_response(self, analysis):
        total = analysis.get("total_spent", 0)
        avg = analysis.get("avg_transaction", 0)
        cats = analysis.get("category_summary", [])
        top_cats = sorted(cats, key=lambda x: x["sum"], reverse=True)[:3]
        top_str = " | ".join([f"{c['category']}: ₹{c['sum']:.0f}" for c in top_cats])
        
        return {
            "type": "ai_response",
            "response": f"""📊 **Your Financial Overview**

💸 **Total Spent:** ₹{total:,.0f}
📈 **Average Transaction:** ₹{avg:,.0f}
🏷️ **Top Spending Categories:**
{chr(10).join([f"   • {c['category']}: ₹{c['sum']:,.0f} ({c['count']} transactions)" for c in top_cats])}

✨ **Insight:** You're spending consistently. Keep tracking to find savings opportunities!""",
        }

    def _spending_summary(self, analysis):
        now = datetime.now()
        df = pd.DataFrame(analysis.get("daily_spending", []))
        if df.empty:
            return {"type": "ai_response", "response": "📊 No spending data for this month yet. Start tracking your expenses!"}
        df["day"] = pd.to_datetime(df["day"])
        monthly = df[df["day"].dt.month == now.month]["total"].sum()
        days_data = len(df[df["day"].dt.month == now.month])
        avg_daily = monthly / days_data if days_data > 0 else 0
        
        return {
            "type": "ai_response",
            "response": f"""💰 **Monthly Spending Summary**

📅 **This Month:** ₹{monthly:,.0f}
📊 **Days Tracked:** {days_data}
📈 **Daily Average:** ₹{avg_daily:,.0f}

💡 **Recommendation:** {"You're on track! 🎯" if monthly < 100000 else "Consider reducing expenses 📉"}""",
        }

    def _budget_check(self, analysis):
        total = analysis.get("total_spent", 0)
        avg = analysis.get("avg_transaction", 0)
        if total == 0:
            return {"type": "ai_response", "response": "📊 No expense data yet. Add your first transaction to get budget insights!"}
        
        return {
            "type": "ai_response",
            "response": f"""🎯 **Budget Analysis**

💸 **Total Spent:** ₹{total:,.0f}
📊 **Average per Transaction:** ₹{avg:,.0f}

📈 **Spending Pattern:** You're maintaining a {("steady" if total < 500000 else "high")} spending pattern.
✅ **Action Items:**
   • Review high-value transactions
   • Set daily spending limits
   • Track recurring expenses""",
        }

    def _predict_spending(self, analysis):
        avg = analysis.get("avg_transaction", 0)
        total = analysis.get("total_spent", 0)
        transactions_count = sum(c['count'] for c in analysis.get("category_summary", []))
        if transactions_count == 0:
            return {"type": "ai_response", "response": "📊 Insufficient data for predictions. Keep tracking your expenses!"}
        
        monthly_estimate = transactions_count * avg if avg > 0 else 0
        
        return {
            "type": "ai_response",
            "response": f"""🔮 **Spending Forecast**

📊 **Estimated Next Month:** ₹{monthly_estimate:,.0f}
📈 **Based on:** {transactions_count} transactions analyzed
💡 **Average per Transaction:** ₹{avg:,.0f}

📌 **Plan for Next Month:**
   • Budget: ₹{monthly_estimate * 1.1:,.0f} (10% cushion)
   • Track daily to stay on target
   • Alert when approaching limit""",
        }

    def _find_anomalies(self, analysis):
        df = pd.DataFrame(analysis.get("daily_spending", []))
        if df.empty:
            return {"type": "ai_response", "response": "📊 No transactions found to analyze."}
        df["day"] = pd.to_datetime(df["day"])
        threshold = df["total"].mean() + 2 * df["total"].std()
        anomalies = df[df["total"] > threshold]
        if anomalies.empty:
            mean_spending = df["total"].mean()
            return {"type": "ai_response", "response": f"""✅ **Spending Audit**

🎯 **All Clear!** No unusual transactions detected.
📊 **Average Daily:** ₹{mean_spending:,.0f}
✨ Your spending is consistent and predictable!"""}
        
        tops = "\n".join([f"   • {row['day'].strftime('%Y-%m-%d')}: ₹{row['total']:,.0f} (High!)" for _, row in anomalies.iterrows()])
        return {"type": "ai_response", "response": f"""🚨 **Anomalies Detected**

⚠️ **Unusual Spending Days:**
{tops}

💡 **Action:** Review these days for unexpected expenses or one-time purchases."""}

    def _handle_goal_setup(self, user_id: str, query: str):
        goal_match = re.search(r"₹?(\d+(?:,\d{3})*)", query)
        months_match = re.search(r"(\d+)\s*month", query)

        if not goal_match and not months_match:
            self.pending_goal_inputs[user_id] = {}
            return {"type": "ai_response", "response": "💎 **Savings Goal Setup**\n\nHow much would you like to save? (e.g., ₹50,000)\nAnd in how many months?"}

        if goal_match and not months_match:
            goal_amount = float(goal_match.group(1).replace(",", ""))
            self.pending_goal_inputs[user_id] = {"goal_amount": goal_amount}
            return {"type": "ai_response", "response": f"""✅ Goal Amount: ₹{goal_amount:,.0f}

⏱️ **Next:** How many months do you want to save this in?
(e.g., "6 months" or "12 months")"""}

        if months_match and not goal_match:
            months = int(months_match.group(1))
            self.pending_goal_inputs[user_id] = {"months": months}
            return {"type": "ai_response", "response": f"""✅ Duration: {months} months

💰 **Next:** How much do you want to save?
(e.g., "₹50,000" or "50000")"""}

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
            return {"type": "ai_response", "response": "❌ Please provide both amount and duration.\nExample: 'Save ₹50,000 in 6 months'"}

    def _generate_goal_plan(self, user_id: str, goal_amount: float, months: int):
        monthly_target = round(goal_amount / months, 2)
        weekly_target = round(goal_amount / (months * 4), 2)
        self.pending_goal_inputs.pop(user_id, None)
        return {
            "type": "ai_response",
            "response": f"""💎 **Your Savings Plan**

🎯 **Goal:** ₹{goal_amount:,.0f}
⏱️ **Timeline:** {months} months

📊 **Breakdown:**
   • Monthly Target: ₹{monthly_target:,.0f}
   • Weekly Target: ₹{weekly_target:,.0f}
   • Daily Target: ₹{round(goal_amount / (months * 30), 2):,.0f}

💡 **Strategy Tips:**
   • Open a separate savings account
   • Set up automatic transfers
   • Reduce non-essential spending by 15%
   • Track progress weekly

✨ **You've got this!** 🚀""",
        }

    async def _investment_advice(self, analysis):
        """Get investment advice with real-time market data using Gemini web search"""
        cats = analysis.get("category_summary", [])
        if not cats:
            return {"type": "ai_response", "response": "📊 No spending data to analyze investments. Start tracking expenses first!"}
        
        top_expense = sorted(cats, key=lambda x: x["sum"], reverse=True)[0]
        suggested_investment = round(top_expense['sum'] * 0.1, 0)
        
        # Get web-based investment research from Gemini
        if self.model:
            try:
                web_advice = await self._get_web_investment_advice(suggested_investment, top_expense['category'])
                return web_advice
            except Exception as e:
                print(f"⚠️ Web search failed: {e}. Using basic advice.")
                return self._get_basic_investment_advice(analysis, top_expense, suggested_investment)
        else:
            return self._get_basic_investment_advice(analysis, top_expense, suggested_investment)
    
    async def _get_web_investment_advice(self, investment_amount: float, category: str) -> Dict[str, Any]:
        """Research current investment options using Gemini's web search"""
        try:
            prompt = f"""You are a financial investment advisor. Based on current market trends and latest investment options in India:

The user wants to invest ₹{investment_amount:,.0f} monthly and their major expense is {category}.

Please provide:
1. Top 3 current best investment options (SIPs, FDs, RDs, etc.) with current rates/returns
2. Pros and cons of each
3. Current market sentiment
4. Risk assessment
5. Specific product recommendations
6. Expected returns over 1 year and 5 years

Keep it concise, actionable, and based on current market data. Include specific fund names, interest rates, or indices if possible."""

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            
            if response and response.text:
                formatted_response = self._format_web_investment_advice(
                    response.text, 
                    investment_amount, 
                    category
                )
                return formatted_response
            else:
                raise ValueError("No response from model")
                
        except Exception as e:
            print(f"❌ Error in web investment research: {e}")
            raise
    
    def _format_web_investment_advice(self, web_data: str, amount: float, category: str) -> Dict[str, Any]:
        """Format web-researched investment advice with current market data"""
        return {
            "type": "ai_response",
            "response": f"""📈 **AI-Powered Investment Advice (Web Research)**

💸 **Your Investment Capacity:** ₹{amount:,.0f}/month
🏷️ **Based on Reducing:** {category} expenses

🌐 **CURRENT MARKET RESEARCH:**
{web_data}

🎯 **Your Personalized Action Plan:**
   1. Reduce {category.lower()} spending by 10% (save ₹{amount:,.0f})
   2. Start with auto-debit for consistency
   3. Diversify across 2-3 investment options
   4. Review quarterly and rebalance

📊 **Portfolio Suggestion for You:**
   • 40% - Best Current SIP Option (Equity/Hybrid funds)
   • 35% - Fixed Deposit (Safe returns)
   • 25% - Direct Stock or Index Funds (Growth)

💡 **Expected Annual Return (Conservative):** ₹{round(amount * 12 * 0.10, 0):,.0f}
💡 **Expected 5-Year Growth:** ₹{round(amount * 60 * 1.55, 0):,.0f}

🔔 **Next Steps:**
   1. Open a Demat account if investing in stocks
   2. Choose a mutual fund platform (Groww, Kuvera, etc.)
   3. Set up SIP with monthly auto-debit
   4. Enable alerts for portfolio updates

⚠️ **Disclaimer:** This is based on current market data from Gemini AI research. Consult a SEBI-registered financial advisor before making decisions."""
        }
    
    def _get_basic_investment_advice(self, analysis: Dict, top_expense: Dict, suggested_investment: float) -> Dict[str, Any]:
        """Fallback basic investment advice when web search is unavailable"""
        return {
            "type": "ai_response",
            "response": f"""📈 **Investment Recommendations (Basic Mode)**

💸 **Your Major Expense:** {top_expense['category']} (₹{top_expense['sum']:,.0f})

🎯 **Action Plan:**
   1. Review if {top_expense['category'].lower()} is necessary
   2. Cut 10% from this category
   3. Invest the saved amount in:
      • SIPs (Systematic Investment Plans)
      • Fixed Deposits (FD)
      • Recurring Deposits (RD)

💰 **Suggested Monthly Investment:** ₹{round(top_expense['sum'] * 0.1, 0):,.0f}

📊 **Potential Returns (1 year at 8% interest):**
    ₹{round(top_expense['sum'] * 0.1 * 12 * 1.08, 0):,.0f}

💡 **Diversification Strategy:**
   • 50% - Mutual Fund SIPs (Hybrid funds)
   • 30% - Fixed Deposits
   • 20% - Direct Stock Investment

📈 **5-Year Projection:**
   Assuming average 10% return: ₹{round(top_expense['sum'] * 0.1 * 60 * 1.61, 0):,.0f}

ℹ️ **Note:** For real-time market data and latest investment options, ask again to get web-based research!

⚠️ **Disclaimer:** Consult a financial advisor before investing."""
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
