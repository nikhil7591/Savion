#!/usr/bin/env python3
"""
Test script for Gemini AI integration
"""
import os
import asyncio

# Set the API key
os.environ["GEMINI_API_KEY"] = "AIzaSyCYvS0PIOo_2yyBJk73yE_xegtf37ZNxD8"

async def test_gemini():
    """Test Gemini AI functionality"""
    try:
        from app.gemini_ai import get_gemini_assistant
        
        print("🧪 Testing Gemini AI...")
        
        # Get assistant instance
        assistant = get_gemini_assistant()
        
        if not assistant.is_available():
            print("❌ Gemini AI not available")
            return False
        
        print("✅ Gemini AI is available!")
        
        # Test basic response generation
        test_prompt = "Hello, can you help me with financial analysis?"
        response = await assistant._generate_response(test_prompt)
        
        print(f"📝 Test Response: {response[:100]}...")
        print("✅ Gemini AI is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gemini AI: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Gemini AI Integration...")
    success = asyncio.run(test_gemini())
    
    if success:
        print("\n🎉 All tests passed! Gemini AI is ready to use.")
        print("\nTo start the server, run:")
        print("uvicorn app.main:app --reload --port 8000")
    else:
        print("\n❌ Tests failed. Please check the configuration.")
