#!/usr/bin/env python3
"""
Setup script for Gemini API key
"""
import os
import sys

def set_gemini_key():
    """Set Gemini API key as environment variable"""
    api_key = "AIzaSyCYvS0PIOo_2yyBJk73yE_xegtf37ZNxD8"
    
    # Set environment variable for current session
    os.environ["GEMINI_API_KEY"] = api_key
    
    print("✅ Gemini API key set successfully!")
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    
    # Test the connection
    try:
        from app.gemini_ai import get_gemini_assistant
        assistant = get_gemini_assistant()
        
        if assistant.is_available():
            print("✅ Gemini AI is configured and ready!")
            return True
        else:
            print("❌ Gemini AI configuration failed")
            return False
    except Exception as e:
        print(f"❌ Error testing Gemini AI: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Gemini AI...")
    success = set_gemini_key()
    
    if success:
        print("\n🎉 Setup complete! You can now start the server.")
        print("Run: uvicorn app.main:app --reload --port 8000")
    else:
        print("\n❌ Setup failed. Please check your API key.")
        sys.exit(1)
