from datetime import datetime
from bson import ObjectId
from . import schemas, security
from .mongo import get_db


def get_user_by_email(email: str):
    db = get_db()
    return db.users.find_one({"email": email})


def create_user(user: schemas.UserCreate):
    db = get_db()
    hashed_password = security.get_password_hash(user.password)
    doc = {
        "name": user.name,
        "email": user.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
    }
    result = db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
