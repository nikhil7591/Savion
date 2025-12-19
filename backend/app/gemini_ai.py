import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from sqlmodel import select, Session
from .models import Transaction
from .db import get_session


class GeminiAIAssistant:
    """Gemini AI-powered financial assistant for real-time data analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        import os
        from pathlib import Path
        
        # Get the API key with your key as default
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.is_configured = False
        
        # Conversation context storage
        self.conversation_contexts = {}
        
        # Configure Gemini AI
        try:
            self._configure_gemini()
            print(f"✅ Gemini AI initialized with key: {self.api_key[:10]}...")
        except Exception as e:
            print(f"Error configuring Gemini AI: {e}")
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.is_configured = False
    
    def _configure_gemini(self):
        """Configure Gemini AI with API key"""
        if not self.api_key:
            raise ValueError("Gemini API key is required")
        
        try:
            # Reset the configuration
            genai.reset()
            
            # Configure Gemini AI with the new key
            genai.configure(api_key=self.api_key)
            
            # Initialize the chat model
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Verify the configuration with a test message
            try:
                response = self.model.generate_content("Test connection")
                if response and response.text:
                    self.is_configured = True
                    print(f"✅ Gemini AI configured successfully with key: {self.api_key[:10]}...")
                else:
                    raise ValueError("No response from model")
            except Exception as e:
                print(f"❌ Model test failed: {str(e)}")
                self.is_configured = False
                raise
        except Exception as e:
            print(f"❌ Failed to configure Gemini AI: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Gemini AI is available and configured"""
        return self.is_configured and self.model is not None
    
    def _get_user_context(self, user_id: str, session: Session) -> Dict[str, Any]:
        """Get comprehensive user financial context"""
        try:
            # Get all transactions
            stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.date)
            transactions = session.exec(stmt).all()
            
            if not transactions:
                return {
                    "user_id": user_id,
                    "transaction_count": 0,
                    "transactions": [],
                    "summary": "No transaction data available"
                }
            
            # Calculate financial summary
            total_income = sum(t.amount for t in transactions if t.type == 'income')
            total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
            balance = total_income - total_expenses
            
            # Category breakdown
            categories = {}
            for t in transactions:
                if t.type == 'expense':
                    categories[t.category] = categories.get(t.category, 0) + t.amount
            
            # Recent transactions (last 30 days)
            recent_date = datetime.now().date() - timedelta(days=30)
            recent_transactions = [
                {
                    "date": t.date.isoformat(),
                    "type": t.type,
                    "category": t.category,
                    "amount": t.amount,
                    "description": f"{t.type.title()} of ₹{t.amount} for {t.category}"
                }
                for t in transactions if t.date >= recent_date
            ]
            
            # Monthly trends (last 6 months)
            monthly_data = {}
            for t in transactions:
                month_key = t.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'income': 0, 'expenses': 0}
                monthly_data[month_key][t.type] += t.amount
            
            return {
                "user_id": user_id,
                "transaction_count": len(transactions),
                "total_income": total_income,
                "total_expenses": total_expenses,
                "balance": balance,
                "categories": categories,
                "recent_transactions": recent_transactions[-10:],  # Last 10 transactions
                "monthly_trends": monthly_data,
                "data_period": {
                    "earliest": min(t.date for t in transactions).isoformat() if transactions else None,
                    "latest": max(t.date for t in transactions).isoformat() if transactions else None
                }
            }
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {
                "user_id": user_id,
                "error": f"Failed to load user data: {str(e)}",
                "transaction_count": 0
            }
    
    def _create_context_prompt(self, user_context: Dict[str, Any], query: str) -> str:
        """Create a comprehensive prompt with user's financial context"""
        
        prompt = f"""You are a Smart Personal Finance Assistant powered by Gemini AI. You have access to the user's financial data and can provide intelligent, personalized advice.

USER'S FINANCIAL CONTEXT:
{json.dumps(user_context, indent=2)}

USER'S QUERY: {query}

INSTRUCTIONS:
1. Analyze the user's financial data to provide relevant, personalized responses
2. Use specific numbers, amounts, and trends from their actual data
3. Provide actionable insights and recommendations
4. Be conversational but professional
5. If the user asks about data that isn't available, explain what information you have and suggest alternatives
6. For spending analysis, highlight patterns and anomalies
7. For budget advice, consider their actual spending patterns
8. For predictions, use their historical data trends
9. Always provide specific, actionable next steps

RESPONSE FORMAT:
- Start with a direct answer to their question
- Provide specific insights from their data
- Give actionable recommendations
- End with follow-up questions or suggestions

Remember: You're analyzing real financial data, so be accurate and helpful with the specific numbers and patterns you find."""

        return prompt
    
    def _get_conversation_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get conversation history for context"""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = []
        
        # Keep only last 10 messages for context
        return self.conversation_contexts[user_id][-10:]
    
    def _update_conversation_history(self, user_id: str, user_query: str, ai_response: str):
        """Update conversation history"""
        if user_id not in self.conversation_contexts:
            self.conversation_contexts[user_id] = []
        
        self.conversation_contexts[user_id].append({
            "user": user_query,
            "assistant": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 messages to manage memory
        if len(self.conversation_contexts[user_id]) > 20:
            self.conversation_contexts[user_id] = self.conversation_contexts[user_id][-20:]
    
    async def process_query(self, user_id: str, query: str, session: Session) -> Dict[str, Any]:
        """Process user query with Gemini AI using their financial data"""
        try:
            # Check if Gemini AI is available
            if not self.is_available():
                return self._fallback_response(user_id, query, session)
            
            # Get user's financial context
            user_context = self._get_user_context(user_id, session)
            
            # Get conversation history
            conversation_history = self._get_conversation_history(user_id)
            
            # Create comprehensive prompt
            base_prompt = self._create_context_prompt(user_context, query)
            
            # Add conversation history if available
            if conversation_history:
                history_text = "\n\nCONVERSATION HISTORY:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages
                    history_text += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
                base_prompt += history_text
            
            # Generate response using Gemini AI
            response = await self._generate_response(base_prompt)
            
            # Update conversation history
            self._update_conversation_history(user_id, query, response)
            
            # Parse response for additional insights
            insights = self._extract_insights(response, user_context)
            
            return {
                "type": "gemini_response",
                "query": query,
                "response": response,
                "insights": insights,
                "user_context_summary": {
                    "transaction_count": user_context.get("transaction_count", 0),
                    "balance": user_context.get("balance", 0),
                    "data_available": user_context.get("transaction_count", 0) > 0
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing query with Gemini AI: {e}")
            return self._fallback_response(user_id, query, session)
    
    def _fallback_response(self, user_id: str, query: str, session: Session) -> Dict[str, Any]:
        """Provide fallback response when Gemini AI is not available"""
        user_context = self._get_user_context(user_id, session)
        
        # Simple rule-based responses based on query keywords
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['spend', 'spent', 'expense']):
            total_expenses = user_context.get("total_expenses", 0)
            response = f"I can see you've spent ₹{total_expenses:,.2f} total. To get detailed AI-powered insights, please configure your Gemini API key."
        elif any(word in query_lower for word in ['income', 'earn', 'salary']):
            total_income = user_context.get("total_income", 0)
            response = f"Your total income is ₹{total_income:,.2f}. For personalized AI analysis, please set up your Gemini API key."
        elif any(word in query_lower for word in ['balance', 'savings']):
            balance = user_context.get("balance", 0)
            response = f"Your current balance is ₹{balance:,.2f}. For advanced financial insights, please configure Gemini AI."
        else:
            response = "I can help you with basic financial analysis. For AI-powered insights and personalized recommendations, please configure your Gemini API key by setting the GEMINI_API_KEY environment variable."
        
        return {
            "type": "fallback_response",
            "query": query,
            "response": response,
            "insights": ["Gemini AI not configured - using basic mode"],
            "user_context_summary": {
                "transaction_count": user_context.get("transaction_count", 0),
                "balance": user_context.get("balance", 0),
                "data_available": user_context.get("transaction_count", 0) > 0,
                "ai_available": False
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemini AI"""
        try:
            # Use asyncio to run the synchronous Gemini call
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(prompt)
            )
            
            return response.text
        except Exception as e:
            print(f"Error generating Gemini response: {e}")
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"
    
    def _extract_insights(self, response: str, user_context: Dict[str, Any]) -> List[str]:
        """Extract key insights from the AI response"""
        insights = []
        
        # Simple insight extraction based on response content
        if "spend" in response.lower() and user_context.get("total_expenses"):
            insights.append(f"Total expenses analyzed: ₹{user_context['total_expenses']:,.2f}")
        
        if "income" in response.lower() and user_context.get("total_income"):
            insights.append(f"Total income analyzed: ₹{user_context['total_income']:,.2f}")
        
        if "balance" in response.lower() and user_context.get("balance"):
            balance = user_context['balance']
            if balance > 0:
                insights.append(f"Positive balance: ₹{balance:,.2f}")
            else:
                insights.append(f"Negative balance: ₹{balance:,.2f}")
        
        if "category" in response.lower() and user_context.get("categories"):
            top_category = max(user_context['categories'].items(), key=lambda x: x[1])
            insights.append(f"Top spending category: {top_category[0]} (₹{top_category[1]:,.2f})")
        
        return insights
    
    def analyze_data_patterns(self, user_id: str, session: Session) -> Dict[str, Any]:
        """Analyze user's data patterns for insights"""
        try:
            user_context = self._get_user_context(user_id, session)
            
            if user_context.get("transaction_count", 0) == 0:
                return {"error": "No transaction data available for analysis"}
            
            patterns = {
                "spending_trends": self._analyze_spending_trends(user_context),
                "category_analysis": self._analyze_categories(user_context),
                "financial_health": self._assess_financial_health(user_context),
                "recommendations": self._generate_recommendations(user_context)
            }
            
            return patterns
            
        except Exception as e:
            return {"error": f"Failed to analyze patterns: {str(e)}"}
    
    def _analyze_spending_trends(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze spending trends"""
        monthly_data = user_context.get("monthly_trends", {})
        
        if not monthly_data:
            return {"trend": "stable", "analysis": "Insufficient data for trend analysis"}
        
        # Calculate trend
        months = sorted(monthly_data.keys())
        if len(months) < 2:
            return {"trend": "stable", "analysis": "Need more data for trend analysis"}
        
        recent_expenses = [monthly_data[m]['expenses'] for m in months[-3:]]
        avg_recent = sum(recent_expenses) / len(recent_expenses)
        
        older_expenses = [monthly_data[m]['expenses'] for m in months[:-3]] if len(months) > 3 else recent_expenses
        avg_older = sum(older_expenses) / len(older_expenses)
        
        if avg_recent > avg_older * 1.1:
            trend = "increasing"
        elif avg_recent < avg_older * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "recent_average": avg_recent,
            "analysis": f"Spending trend is {trend} with recent average of ₹{avg_recent:,.2f}"
        }
    
    def _analyze_categories(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze spending by categories"""
        categories = user_context.get("categories", {})
        
        if not categories:
            return {"analysis": "No expense categories found"}
        
        total_expenses = sum(categories.values())
        category_percentages = {cat: (amt/total_expenses)*100 for cat, amt in categories.items()}
        
        top_categories = sorted(category_percentages.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "top_categories": top_categories,
            "total_categories": len(categories),
            "analysis": f"Spending across {len(categories)} categories, top category: {top_categories[0][0]} ({top_categories[0][1]:.1f}%)"
        }
    
    def _assess_financial_health(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall financial health"""
        total_income = user_context.get("total_income", 0)
        total_expenses = user_context.get("total_expenses", 0)
        balance = user_context.get("balance", 0)
        
        if total_income == 0:
            return {"score": 0, "assessment": "No income data available"}
        
        savings_rate = (balance / total_income) * 100 if total_income > 0 else 0
        
        if savings_rate > 20:
            score = 90
            assessment = "Excellent financial health"
        elif savings_rate > 10:
            score = 70
            assessment = "Good financial health"
        elif savings_rate > 0:
            score = 50
            assessment = "Fair financial health"
        else:
            score = 20
            assessment = "Needs improvement"
        
        return {
            "score": score,
            "assessment": assessment,
            "savings_rate": savings_rate,
            "balance": balance
        }
    
    def _generate_recommendations(self, user_context: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        balance = user_context.get("balance", 0)
        total_income = user_context.get("total_income", 0)
        
        if balance < 0:
            recommendations.append("🚨 Your balance is negative. Focus on reducing expenses or increasing income.")
        
        if total_income > 0:
            savings_rate = (balance / total_income) * 100
            if savings_rate < 10:
                recommendations.append("💰 Consider increasing your savings rate to at least 10% of income.")
            
            if savings_rate > 20:
                recommendations.append("🎯 Great savings rate! Consider investing surplus funds.")
        
        categories = user_context.get("categories", {})
        if categories:
            top_category = max(categories.items(), key=lambda x: x[1])
            if top_category[1] > total_income * 0.3:
                recommendations.append(f"📊 High spending in {top_category[0]}. Review if this is necessary.")
        
        if len(categories) < 3:
            recommendations.append("📈 Diversify your expense tracking across more categories for better insights.")
        
        return recommendations
    
    def clear_conversation_history(self, user_id: str):
        """Clear conversation history for a user"""
        if user_id in self.conversation_contexts:
            del self.conversation_contexts[user_id]
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of conversation history"""
        history = self._get_conversation_history(user_id)
        return {
            "message_count": len(history),
            "last_conversation": history[-1] if history else None,
            "conversation_topics": self._extract_conversation_topics(history)
        }
    
    def _extract_conversation_topics(self, history: List[Dict[str, str]]) -> List[str]:
        """Extract main topics from conversation history"""
        topics = []
        for msg in history:
            query = msg.get("user", "").lower()
            if any(word in query for word in ["spend", "expense", "cost"]):
                topics.append("spending_analysis")
            elif any(word in query for word in ["budget", "save", "goal"]):
                topics.append("budget_planning")
            elif any(word in query for word in ["predict", "forecast", "future"]):
                topics.append("predictions")
            elif any(word in query for word in ["invest", "investment", "money"]):
                topics.append("investment_advice")
        
        return list(set(topics))


# Global instance
_gemini_assistant = None

def get_gemini_assistant() -> GeminiAIAssistant:
    """Get or create global Gemini AI assistant instance"""
    global _gemini_assistant
    if _gemini_assistant is None:
        _gemini_assistant = GeminiAIAssistant()
    return _gemini_assistant
