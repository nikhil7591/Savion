import os
from functools import lru_cache
from pymongo import MongoClient


@lru_cache
def get_client():
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI not set in environment")
    return MongoClient(uri)


def get_db():
    client = get_client()
    db_name = os.getenv("MONGO_DB_NAME", "savion")
    return client[db_name]
