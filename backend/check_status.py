#!/usr/bin/env python3
"""
Status check script for Savion Backend
"""
import os
import sys
import requests
import time

def check_backend_status():
    """Check if backend server is running"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            return True, "Backend server is running"
        else:
            return False, f"Backend returned status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Cannot connect to backend: {e}"

def check_gemini_status():
    """Check Gemini AI status"""
    try:
        response = requests.get("http://localhost:8000/api/gemini/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("available", False), data.get("message", "Unknown status")
        else:
            return False, f"Gemini status check failed: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Cannot check Gemini status: {e}"

def check_websocket_status():
    """Check WebSocket status"""
    try:
        response = requests.get("http://localhost:8000/api/websocket/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"WebSocket active - {data.get('total_connections', 0)} connections"
        else:
            return False, f"WebSocket check failed: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"Cannot check WebSocket status: {e}"

def main():
    """Main status check"""
    print("🔍 Checking Savion Backend Status...")
    print("=" * 50)
    
    # Check backend
    backend_ok, backend_msg = check_backend_status()
    print(f"🖥️  Backend Server: {'✅' if backend_ok else '❌'} {backend_msg}")
    
    if not backend_ok:
        print("\n❌ Backend server is not running!")
        print("Please start the server with:")
        print("uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    
    # Check Gemini AI
    gemini_ok, gemini_msg = check_gemini_status()
    print(f"🧠 Gemini AI: {'✅' if gemini_ok else '❌'} {gemini_msg}")
    
    # Check WebSocket
    websocket_ok, websocket_msg = check_websocket_status()
    print(f"🔌 WebSocket: {'✅' if websocket_ok else '❌'} {websocket_msg}")
    
    print("\n" + "=" * 50)
    
    if backend_ok and gemini_ok and websocket_ok:
        print("🎉 All systems are operational!")
        print("\n📱 You can now:")
        print("• Open the frontend at http://localhost:5173")
        print("• Use the chatbot with AI-powered responses")
        print("• Upload CSV/Excel files for analysis")
        print("• Chat in real-time via WebSocket")
    else:
        print("⚠️  Some components need attention")
        if not gemini_ok:
            print("• Gemini AI needs configuration")
        if not websocket_ok:
            print("• WebSocket may have issues")

if __name__ == "__main__":
    main()
