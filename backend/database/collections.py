"""
Collections references with safe fallback.
"""

from backend.database.db_manager import _mongo_db as db

if db is not None:
    users_collection = db["users"]
    predictions_collection = db["predictions"]
    weather_records_collection = db["weather_records"]
    model_metrics_collection = db["model_metrics"]
else:
    users_collection = None
    predictions_collection = None
    weather_records_collection = None
    model_metrics_collection = None
