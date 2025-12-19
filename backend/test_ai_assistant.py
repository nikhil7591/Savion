"""
Test the AI Assistant and Finance Agent
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

def test_finance_agent():
    """Test the FinanceAgent"""
    print("\n" + "="*60)
    print("🧪 Testing FinanceAgent Initialization")
    print("="*60)
    
    try:
        agent = get_finance_agent()
        if agent.model:
            print("✅ FinanceAgent initialized successfully")
            print(f"   - Model: {agent.model}")
            print(f"   - API Key configured: {bool(agent.api_key)}")
        else:
            print("⚠️ FinanceAgent initialized but model is None")
        return agent
    except Exception as e:
        print(f"❌ Failed to initialize FinanceAgent: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_finance_agent_query():
    """Test the query processing"""
    print("\n" + "="*60)
    print("🧪 Testing Query Processing")
    print("="*60)
    
    agent = get_finance_agent()
    if not agent:
        print("❌ Agent not available")
        return
    
    test_queries = [
        "What's my spending summary?",
        "Analyze my data",
        "I want to save ₹50,000 in 6 months",
        "Show me budget check",
        "Predict my spending",
    ]
    
    user_id = "test_user_12345"
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            result = await agent.process_query(user_id, query)
            if result:
                print(f"✅ Response type: {result.get('type')}")
                response = result.get('response', '')
                # Print first 200 chars of response
                print(f"📄 Response preview:\n{response[:200]}...")
            else:
                print("❌ No response received")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def test_database_connection():
    """Test MongoDB connection"""
    print("\n" + "="*60)
    print("🧪 Testing Database Connection")
    print("="*60)
    
    try:
        db.init_db()
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🤖 Savion AI Assistant Test Suite")
    print("="*60)
    
    # Test database
    test_database_connection()
    
    # Test agent initialization
    agent = test_finance_agent()
    
    if agent:
        # Test query processing
        await test_finance_agent_query()
    
    print("\n" + "="*60)
    print("✅ Test Suite Complete")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
