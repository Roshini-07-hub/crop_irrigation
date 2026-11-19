"""
MongoDB Atlas Connector

Provides safe connection helpers.
"""

from backend.database.db_manager import (
    _mongo_client as client,
    _mongo_db as db,
    _is_mongo_active,
    get_db_status
)


def test_connection():
    status = get_db_status()
    if status["mongodb_active"]:
        print("MongoDB Atlas connected successfully!")
        return True
    else:
        print("MongoDB Atlas is offline/unavailable. Local SQLite engine is active.")
        return False
