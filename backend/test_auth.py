#!/usr/bin/env python
"""Test authentication endpoints"""
import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_signup():
    """Test user signup"""
    print("\n=== Testing Signup ===")
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": "test@example.com",
            "password": "Test@1234",
            "name": "Test User"
        }
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get("access_token") if response.status_code == 200 else None

def test_signin():
    """Test user signin"""
    print("\n=== Testing Signin ===")
    response = requests.post(
        f"{BASE_URL}/auth/signin",
        json={
            "email": "test@example.com",
            "password": "Test@1234"
        }
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    return data.get("access_token") if response.status_code == 200 else None

def test_verify(token):
    """Test token verification"""
    print("\n=== Testing Verify ===")
    response = requests.get(
        f"{BASE_URL}/auth/verify?token={token}"
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    print("Testing Authentication Endpoints")
    
    # Test signup
    token = test_signup()
    
    # Test signin
    token = test_signin()
    
    # Test verify
    if token:
        test_verify(token)
