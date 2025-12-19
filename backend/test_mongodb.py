#!/usr/bin/env python3
"""
Test script to verify MongoDB connection and basic operations
"""
import sys
from app import db
from app.models import Transaction
from datetime import datetime, date

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("=" * 60)
    print("Testing MongoDB Connection")
    print("=" * 60)
    
    try:
        db.init_db()
        print("✅ MongoDB connected successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False

def test_create_transaction():
    """Test creating a transaction"""
    print("\n" + "=" * 60)
    print("Testing Transaction Creation")
    print("=" * 60)
    
    try:
        transaction_data = {
            "user_id": "test_user_001",
            "type": "expense",
            "category": "Food",
            "amount": 250.50,
            "date": datetime.now(),
        }
        
        result = db.create_transaction(transaction_data)
        print(f"✅ Transaction created successfully")
        print(f"   ID: {result.get('_id')}")
        print(f"   User: {result.get('user_id')}")
        print(f"   Category: {result.get('category')}")
        print(f"   Amount: ₹{result.get('amount')}")
        return str(result.get('_id'))
    except Exception as e:
        print(f"❌ Failed to create transaction: {e}")
        return None

def test_get_transactions(user_id: str):
    """Test retrieving transactions"""
    print("\n" + "=" * 60)
    print("Testing Transaction Retrieval")
    print("=" * 60)
    
    try:
        transactions = db.get_transactions(user_id)
        print(f"✅ Retrieved {len(transactions)} transaction(s)")
        for i, tx in enumerate(transactions, 1):
            print(f"\n   Transaction {i}:")
            print(f"   - Category: {tx.get('category')}")
            print(f"   - Amount: ₹{tx.get('amount')}")
            print(f"   - Date: {tx.get('date')}")
        return True
    except Exception as e:
        print(f"❌ Failed to retrieve transactions: {e}")
        return False

def test_update_transaction(transaction_id: str):
    """Test updating a transaction"""
    print("\n" + "=" * 60)
    print("Testing Transaction Update")
    print("=" * 60)
    
    try:
        update_data = {
            "category": "Food & Dining",
            "amount": 350.75,
        }
        
        result = db.update_transaction(transaction_id, update_data)
        print(f"✅ Transaction updated successfully")
        print(f"   New Category: {result.get('category')}")
        print(f"   New Amount: ₹{result.get('amount')}")
        return True
    except Exception as e:
        print(f"❌ Failed to update transaction: {e}")
        return False

def test_get_transactions_by_category(user_id: str, category: str):
    """Test filtering transactions by category"""
    print("\n" + "=" * 60)
    print(f"Testing Filter by Category: {category}")
    print("=" * 60)
    
    try:
        transactions = db.get_transactions_by_category(user_id, category)
        print(f"✅ Retrieved {len(transactions)} transaction(s) in '{category}'")
        for tx in transactions:
            print(f"   - Amount: ₹{tx.get('amount')}")
        return True
    except Exception as e:
        print(f"❌ Failed to filter by category: {e}")
        return False

def test_delete_transaction(transaction_id: str):
    """Test deleting a transaction"""
    print("\n" + "=" * 60)
    print("Testing Transaction Deletion")
    print("=" * 60)
    
    try:
        success = db.delete_transaction(transaction_id)
        if success:
            print(f"✅ Transaction deleted successfully")
        else:
            print(f"⚠️  Transaction not found")
        return success
    except Exception as e:
        print(f"❌ Failed to delete transaction: {e}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  SAVION - MongoDB Integration Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # Test 1: Connection
    if not test_mongodb_connection():
        print("\n❌ MongoDB connection failed. Exiting tests.")
        sys.exit(1)
    
    # Test 2: Create
    tx_id = test_create_transaction()
    if not tx_id:
        print("\n❌ Failed to create transaction. Exiting tests.")
        sys.exit(1)
    
    # Test 3: Retrieve
    if not test_get_transactions("test_user_001"):
        print("\n⚠️ Retrieval test failed")
    
    # Test 4: Update
    if not test_update_transaction(tx_id):
        print("\n⚠️ Update test failed")
    
    # Test 5: Filter by category
    if not test_get_transactions_by_category("test_user_001", "Food & Dining"):
        print("\n⚠️ Filter test failed")
    
    # Test 6: Delete
    if not test_delete_transaction(tx_id):
        print("\n⚠️ Delete test failed")
    
    # Close connection
    db.close_db()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
