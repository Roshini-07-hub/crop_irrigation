"""
Weather Database Service

Provides persistence for weather records.
Backed by the unified db_manager (supporting local SQLite and MongoDB Atlas).
"""

from backend.database.db_manager import (
    save_weather_record,
    get_weather_records
)

__all__ = [
    "save_weather_record",
    "get_weather_records"
]
