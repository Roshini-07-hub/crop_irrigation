"""
Database Service

Provides persistence interface for predictions and history.
Backed by the unified db_manager (supporting local SQLite and MongoDB Atlas).
"""

from backend.database.db_manager import (
    save_prediction,
    get_predictions,
    delete_prediction,
    get_db_status
)

__all__ = [
    "save_prediction",
    "get_predictions",
    "delete_prediction",
    "get_db_status"
]
