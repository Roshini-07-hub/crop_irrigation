from flask import Blueprint, request, jsonify

from backend.services.weather_service import get_weather


weather_bp = Blueprint("weather", __name__, url_prefix="/api/weather")


@weather_bp.route("/", methods=["GET"])
def weather():
    try:
        latitude = request.args.get("latitude", type=float)
        longitude = request.args.get("longitude", type=float)

        if latitude is None or longitude is None:
            return jsonify({
                "success": False,
                "error": "latitude and longitude are required"
            }), 400

        if not (-90 <= latitude <= 90):
            return jsonify({
                "success": False,
                "error": "latitude must be between -90 and 90"
            }), 400

        if not (-180 <= longitude <= 180):
            return jsonify({
                "success": False,
                "error": "longitude must be between -180 and 180"
            }), 400

        weather_data = get_weather(latitude, longitude)

        return jsonify({
            "success": True,
            "weather": weather_data
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500