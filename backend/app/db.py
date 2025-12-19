import os
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "finance"

client: Optional[MongoClient] = None
db = None

def init_db():
    """Initialize MongoDB connection and create necessary indices"""
    global client, db
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create collections if they don't exist
        if "users" not in db.list_collection_names():
            db.create_collection("users")
        
        if "transactions" not in db.list_collection_names():
            db.create_collection("transactions")
        
        # Create indices for better performance
        db.users.create_index("email", unique=True, sparse=True)
        db.transactions.create_index([("user_id", 1), ("date", -1)])
        db.transactions.create_index([("user_id", 1), ("category", 1)])
        
        # Test the connection
        client.admin.command('ping')
        print("✅ MongoDB connected successfully")
        return db
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise

def get_db():
    """Get database instance"""
    global db
    if db is None:
        init_db()
    return db

def close_db():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")

# User collection functions
def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user"""
    db = get_db()
    user_data["created_at"] = datetime.utcnow()
    user_data["updated_at"] = datetime.utcnow()
    result = db.users.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    return user_data

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    db = get_db()
    return db.users.find_one({"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id})

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID (alias for get_user)"""
    return get_user(user_id)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    db = get_db()
    return db.users.find_one({"email": email})

def update_user(user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update user information"""
    db = get_db()
    update_data["updated_at"] = datetime.utcnow()
    result = db.users.find_one_and_update(
        {"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id},
        {"$set": update_data},
        return_document=True
    )
    return result

def delete_user(user_id: str) -> bool:
    """Delete a user"""
    db = get_db()
    result = db.users.delete_one({"_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id})
    return result.deleted_count > 0

# Transaction collection functions
def create_transaction(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new transaction"""
    db = get_db()
    transaction_data["created_at"] = datetime.utcnow()
    result = db.transactions.insert_one(transaction_data)
    transaction_data["_id"] = result.inserted_id
    return transaction_data

def get_transactions(user_id: str, limit: int = 1000, skip: int = 0) -> List[Dict[str, Any]]:
    """Get all transactions for a user"""
    db = get_db()
    return list(db.transactions.find(
        {"user_id": user_id}
    ).sort("date", -1).skip(skip).limit(limit))

def get_transaction(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific transaction"""
    db = get_db()
    return db.transactions.find_one({"_id": ObjectId(transaction_id)})

def update_transaction(transaction_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a transaction"""
    db = get_db()
    update_data["updated_at"] = datetime.utcnow()
    result = db.transactions.find_one_and_update(
        {"_id": ObjectId(transaction_id)},
        {"$set": update_data},
        return_document=True
    )
    return result

def delete_transaction(transaction_id: str) -> bool:
    """Delete a transaction"""
    db = get_db()
    result = db.transactions.delete_one({"_id": ObjectId(transaction_id)})
    return result.deleted_count > 0

def get_transactions_by_category(user_id: str, category: str) -> List[Dict[str, Any]]:
    """Get transactions by category"""
    db = get_db()
    return list(db.transactions.find(
        {"user_id": user_id, "category": category}
    ).sort("date", -1))

def get_transactions_by_type(user_id: str, tx_type: str) -> List[Dict[str, Any]]:
    """Get transactions by type (income/expense)"""
    db = get_db()
    return list(db.transactions.find(
        {"user_id": user_id, "type": tx_type}
    ).sort("date", -1))

def get_transactions_by_date_range(user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """Get transactions within a date range"""
    db = get_db()
    return list(db.transactions.find(
        {
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }
    ).sort("date", -1))