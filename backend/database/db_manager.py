"""
Unified Database Manager for Sustainable AI Crop Irrigation

Provides seamless persistence with automatic dual-mode operation:
1. Local SQLite Storage (high-speed, always reliable, zero external dependencies)
2. MongoDB Atlas (remote cloud database when configured and reachable)

Ensures 100% uptime with graceful fallback so the application NEVER crashes
due to network issues or Atlas IP whitelist restrictions.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Path configuration
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
SQLITE_DB_PATH = BASE_DIR / "database" / "crop_water_local.db"

load_dotenv(ENV_FILE)

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "sustainable_ai_irrigation")

_mongo_client = None
_mongo_db = None
_is_mongo_active = False


def _init_sqlite():
    """Initialize local SQLite tables."""
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id TEXT PRIMARY KEY,
                prediction_type TEXT,
                input_json TEXT,
                result_json TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_records (
                id TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                weather_json TEXT,
                created_at TEXT
            )
        """)
        conn.commit()


# Initialize SQLite on import
_init_sqlite()


def _get_sqlite_conn():
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _try_init_mongodb():
    """Attempt a non-blocking MongoDB connection check with short timeout."""
    global _mongo_client, _mongo_db, _is_mongo_active

    if not MONGO_URI:
        _is_mongo_active = False
        return

    try:
        from pymongo import MongoClient

        # Use 2-second timeout so app never hangs
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000
        )
        # Fast ping check
        client.admin.command("ping")
        _mongo_client = client
        _mongo_db = client[DB_NAME]
        _is_mongo_active = True
        print("[Database] MongoDB Atlas connected successfully.")
    except Exception as e:
        _is_mongo_active = False
        print(f"[Database] MongoDB Atlas not reachable ({e}). Using local SQLite database.")


# Attempt MongoDB connection once on load
_try_init_mongodb()


def get_db_status():
    """Return database operational status."""
    return {
        "engine": "MongoDB Atlas" if _is_mongo_active else "Local SQLite Engine",
        "mongodb_active": _is_mongo_active,
        "sqlite_active": True,
        "sqlite_path": str(SQLITE_DB_PATH)
    }


# ============================================================
# PREDICTIONS PERSISTENCE
# ============================================================

def save_prediction(prediction_type, input_data, result_data):
    """
    Save a prediction record into the active database.
    Always persists to local SQLite and mirrors to MongoDB when connected.
    """
    rec_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    # 1. Save to local SQLite
    try:
        with _get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO predictions (id, prediction_type, input_json, result_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    str(prediction_type),
                    json.dumps(input_data, default=str),
                    json.dumps(result_data, default=str),
                    now_iso
                )
            )
            conn.commit()
    except Exception as e:
        print(f"[Database Warning] Failed to write to SQLite: {e}")

    # 2. Mirror to MongoDB if active
    if _is_mongo_active and _mongo_db is not None:
        try:
            doc = {
                "_id": rec_id,
                "prediction_type": prediction_type,
                "input": input_data,
                "result": result_data,
                "created_at": now_dt
            }
            _mongo_db["predictions"].insert_one(doc)
        except Exception as e:
            print(f"[Database Warning] MongoDB mirror failed: {e}")

    return rec_id


def get_predictions(prediction_type=None, limit=50):
    """Retrieve predictions sorted by creation date descending."""
    limit = max(1, min(int(limit), 100))

    # Try MongoDB first if active
    if _is_mongo_active and _mongo_db is not None:
        try:
            query = {}
            if prediction_type:
                query["prediction_type"] = prediction_type
            records = list(
                _mongo_db["predictions"]
                .find(query)
                .sort("created_at", -1)
                .limit(limit)
            )
            output = []
            for rec in records:
                created = rec.get("created_at")
                if isinstance(created, datetime):
                    created_str = created.isoformat()
                else:
                    created_str = str(created) if created else None

                output.append({
                    "id": str(rec.get("_id")),
                    "prediction_type": rec.get("prediction_type"),
                    "input": rec.get("input", {}),
                    "result": rec.get("result", {}),
                    "created_at": created_str
                })
            return output
        except Exception as e:
            print(f"[Database Warning] MongoDB read failed ({e}), reading from SQLite.")

    # Read from SQLite
    try:
        with _get_sqlite_conn() as conn:
            cursor = conn.cursor()
            if prediction_type:
                cursor.execute(
                    """
                    SELECT id, prediction_type, input_json, result_json, created_at
                    FROM predictions
                    WHERE prediction_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (prediction_type, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, prediction_type, input_json, result_json, created_at
                    FROM predictions
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
            rows = cursor.fetchall()
            output = []
            for r in rows:
                try:
                    inp = json.loads(r["input_json"]) if r["input_json"] else {}
                except Exception:
                    inp = {}
                try:
                    res = json.loads(r["result_json"]) if r["result_json"] else {}
                except Exception:
                    res = {}

                output.append({
                    "id": r["id"],
                    "prediction_type": r["prediction_type"],
                    "input": inp,
                    "result": res,
                    "created_at": r["created_at"]
                })
            return output
    except Exception as e:
        print(f"[Database Error] SQLite read failed: {e}")
        return []


def delete_prediction(prediction_id):
    """Delete a prediction by its ID."""
    deleted = False

    # 1. Delete from SQLite
    try:
        with _get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM predictions WHERE id = ?", (str(prediction_id),))
            conn.commit()
            if cursor.rowcount > 0:
                deleted = True
    except Exception as e:
        print(f"[Database Warning] SQLite delete error: {e}")

    # 2. Delete from MongoDB if active
    if _is_mongo_active and _mongo_db is not None:
        try:
            from bson import ObjectId
            try:
                oid = ObjectId(prediction_id)
                res = _mongo_db["predictions"].delete_one({"_id": oid})
            except Exception:
                res = _mongo_db["predictions"].delete_one({"_id": str(prediction_id)})
            if res.deleted_count > 0:
                deleted = True
        except Exception as e:
            print(f"[Database Warning] MongoDB delete error: {e}")

    return deleted


# ============================================================
# WEATHER RECORDS PERSISTENCE
# ============================================================

def save_weather_record(weather_data, latitude, longitude):
    """Save a weather observation record."""
    rec_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    # 1. Save to SQLite
    try:
        with _get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO weather_records (id, latitude, longitude, weather_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    float(latitude),
                    float(longitude),
                    json.dumps(weather_data, default=str),
                    now_iso
                )
            )
            conn.commit()
    except Exception as e:
        print(f"[Database Warning] Failed to save weather to SQLite: {e}")

    # 2. Mirror to MongoDB if active
    if _is_mongo_active and _mongo_db is not None:
        try:
            doc = {
                "_id": rec_id,
                "latitude": latitude,
                "longitude": longitude,
                "weather": weather_data,
                "created_at": now_dt
            }
            _mongo_db["weather_records"].insert_one(doc)
        except Exception as e:
            print(f"[Database Warning] MongoDB weather save failed: {e}")

    return rec_id


def get_weather_records(limit=50):
    """Retrieve weather records sorted by date descending."""
    limit = max(1, min(int(limit), 100))

    if _is_mongo_active and _mongo_db is not None:
        try:
            records = list(
                _mongo_db["weather_records"]
                .find()
                .sort("created_at", -1)
                .limit(limit)
            )
            output = []
            for rec in records:
                created = rec.get("created_at")
                if isinstance(created, datetime):
                    created_str = created.isoformat()
                else:
                    created_str = str(created) if created else None
                rec["_id"] = str(rec.get("_id"))
                rec["created_at"] = created_str
                output.append(rec)
            return output
        except Exception as e:
            print(f"[Database Warning] MongoDB weather read failed: {e}")

    try:
        with _get_sqlite_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, latitude, longitude, weather_json, created_at
                FROM weather_records
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            output = []
            for r in rows:
                try:
                    w = json.loads(r["weather_json"]) if r["weather_json"] else {}
                except Exception:
                    w = {}
                output.append({
                    "_id": r["id"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "weather": w,
                    "created_at": r["created_at"]
                })
            return output
    except Exception as e:
        print(f"[Database Error] SQLite weather read failed: {e}")
        return []
