"""
Test the Enhanced Investment Advice Feature with Web Search
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "AIzaSyB6BzoXgJ5tBJplZ3r09chKK87822Q5eCM")

from app.finance_agent import get_finance_agent
from app import db

def test_investment_advice_basic():
    """Test basic investment advice (without web search)"""
    print("\n" + "="*70)
    print("🧪 Test 1: Basic Investment Advice (Fallback Mode)")
    print("="*70)
    
    agent = get_finance_agent()
    
    # Simulate spending analysis
    analysis = {
        "total_spent": 50000,
        "avg_transaction": 1200,
        "category_summary": [
            {"category": "Food", "sum": 15000, "count": 20},
            {"category": "Transport", "sum": 10000, "count": 15},
            {"category": "Entertainment", "sum": 8000, "count": 10},
        ],
        "daily_spending": []
    }
    
    print("📊 Input Analysis:")
    print(f"   Total Spent: ₹{analysis['total_spent']:,.0f}")
    print(f"   Top Category: {analysis['category_summary'][0]['category']} (₹{analysis['category_summary'][0]['sum']:,.0f})")
    
    # Get basic advice (this tests the fallback)
    result = agent._get_basic_investment_advice(
        analysis,
        analysis['category_summary'][0],
        5000
    )
    
    print("\n✅ Response Type:", result.get("type"))
    print("\n📄 Response Preview (first 500 chars):")
    print(result.get("response", "")[:500])
    print("...")

async def test_investment_advice_web_search():
    """Test investment advice with web search"""
    print("\n" + "="*70)
    print("🧪 Test 2: Investment Advice with Web Search")
    print("="*70)
    
    agent = get_finance_agent()
    
    if not agent.model:
        print("⚠️ Gemini model not available. Skipping web search test.")
        print("Set GEMINI_API_KEY in .env to enable web search.")
        return
    
    print("🌐 Initiating web search for investment data...")
    print("   Investment Amount: ₹5,000/month")
    print("   Category: Food expenses")
    
    analysis = {
        "total_spent": 50000,
        "avg_transaction": 1200,
        "category_summary": [
            {"category": "Food", "sum": 15000, "count": 20},
            {"category": "Transport", "sum": 10000, "count": 15},
            {"category": "Entertainment", "sum": 8000, "count": 10},
        ],
        "daily_spending": []
    }
    
    try:
        result = await agent._investment_advice(analysis)
        
        print("\n✅ Web Search Completed Successfully!")
        print("📄 Response Type:", result.get("type"))
        print("\n📄 Response Preview (first 800 chars):")
        print(result.get("response", "")[:800])
        print("...")
        
        if "CURRENT MARKET RESEARCH" in result.get("response", ""):
            print("\n🌐 ✅ Web search data included in response!")
        else:
            print("\n⚠️ Web search response may not have included latest market data")
            
    except Exception as e:
        print(f"\n❌ Error during web search: {e}")
        print("ℹ️ This might indicate web search is not fully configured")
        import traceback
        traceback.print_exc()

async def test_full_investment_query():
    """Test full query processing for investment advice"""
    print("\n" + "="*70)
    print("🧪 Test 3: Full Investment Query Processing")
    print("="*70)
    
    agent = get_finance_agent()
    user_id = "test_user_investment"
    
    print("📝 Query: 'I need investment advice'")
    print("   Processing as: 'investment_advice' intent")
    
    # Create dummy analysis
    analysis = {
        "total_spent": 50000,
        "avg_transaction": 1200,
        "category_summary": [
            {"category": "Food", "sum": 15000, "count": 20},
        ]
    }
    
    try:
        result = await agent._investment_advice(analysis)
        
        print("\n✅ Query processed successfully!")
        print("📄 Response Type:", result.get("type"))
        print("📄 Response Length:", len(result.get("response", "")), "characters")
        
        response = result.get("response", "")
        
        # Check for expected components
        checks = {
            "Has investment emojis": "📈" in response or "💰" in response,
            "Has action plan": "Action Plan" in response or "Personalized" in response,
            "Has return projections": "Expected" in response or "Return" in response,
            "Has disclaimer": "Disclaimer" in response,
            "Has next steps": "Next Steps" in response,
        }
        
        print("\n✅ Response Quality Checks:")
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_investment_intent_detection():
    """Test investment intent detection"""
    print("\n" + "="*70)
    print("🧪 Test 4: Investment Intent Detection")
    print("="*70)
    
    agent = get_finance_agent()
    
    test_queries = [
        ("investment advice", "investment_advice"),
        ("suggest investments", "investment_advice"),
        ("invest in stocks", "investment_advice"),
        ("mutual funds recommendations", "investment_advice"),
        ("where should I invest", "investment_advice"),
        ("What's my spending?", "spending_summary"),
        ("analyze data", "analyze_data"),
    ]
    
    print("Testing intent detection on various queries:\n")
    
    for query, expected_intent in test_queries:
        detected_intent = agent.detect_intent(query)
        status = "✅" if detected_intent == expected_intent else "❌"
        print(f"{status} '{query}'")
        print(f"   Expected: {expected_intent}, Detected: {detected_intent}")

async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 INVESTMENT ADVICE FEATURE - TEST SUITE")
    print("="*70)
    
    print("\n📊 Test Configuration:")
    print(f"   Gemini API Key: {('✅ Set' if os.environ.get('GEMINI_API_KEY') else '❌ Not set')}")
    print(f"   Python Version: {sys.version.split()[0]}")
    
    # Run tests
    test_investment_advice_basic()
    test_investment_intent_detection()
    await test_investment_advice_web_search()
    await test_full_investment_query()
    
    print("\n" + "="*70)
    print("✅ TEST SUITE COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
