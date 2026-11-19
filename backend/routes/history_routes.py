"""
History Routes Blueprint

Provides REST endpoints for retrieving and managing prediction and weather history.
Backed by the resilient database manager (SQLite local mode / MongoDB Atlas).
"""

from flask import Blueprint, jsonify, request

from backend.services.database_service import (
    get_predictions,
    delete_prediction
)
from backend.services.weather_database_service import (
    get_weather_records
)


history_bp = Blueprint(
    "history",
    __name__,
    url_prefix="/api/history"
)


# ============================================================
# GET ALL PREDICTION HISTORY
# ============================================================

@history_bp.route("/", methods=["GET"])
def get_history():
    try:
        limit = int(request.args.get("limit", 50))
        if limit <= 0:
            limit = 50
        if limit > 100:
            limit = 100

        prediction_type = request.args.get("type", None)
        if prediction_type:
            prediction_type = prediction_type.strip().lower()

        history = get_predictions(prediction_type=prediction_type, limit=limit)

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200

    except ValueError:
        return jsonify({
            "success": False,
            "error": "limit must be a valid integer."
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to retrieve prediction history.",
            "details": str(e)
        }), 500


# ============================================================
# GET WATER HISTORY
# ============================================================

@history_bp.route("/water", methods=["GET"])
def get_water_history():
    try:
        limit = int(request.args.get("limit", 50))
        history = get_predictions(prediction_type="water", limit=limit)

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to retrieve water history.",
            "details": str(e)
        }), 500


# ============================================================
# GET COMPLETE IRRIGATION HISTORY
# ============================================================

@history_bp.route("/complete", methods=["GET"])
def get_complete_history():
    try:
        limit = int(request.args.get("limit", 50))
        history = get_predictions(prediction_type="complete", limit=limit)

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to retrieve complete prediction history.",
            "details": str(e)
        }), 500


# ============================================================
# GET WEATHER HISTORY
# ============================================================

@history_bp.route("/weather", methods=["GET"])
def weather_history():
    try:
        limit = int(request.args.get("limit", 50))
        history = get_weather_records(limit=limit)

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to retrieve weather history.",
            "details": str(e)
        }), 500


# ============================================================
# DELETE ONE PREDICTION HISTORY RECORD
# ============================================================

@history_bp.route("/<prediction_id>", methods=["DELETE"])
def delete_history_record(prediction_id):
    try:
        deleted = delete_prediction(prediction_id)

        if not deleted:
            return jsonify({
                "success": False,
                "error": "History record not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "History record deleted successfully."
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to delete history record.",
            "details": str(e)
        }), 500
