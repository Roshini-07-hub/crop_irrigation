import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of where Python is invoked from
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from backend.routes.prediction_routes import prediction_bp
from backend.routes.history_routes import history_bp
from backend.routes.weather_routes import weather_bp
from backend.routes.location_routes import location_bp
from backend.routes.crops_routes import crops_bp
from backend.services.database_service import get_db_status

# ============================================================
# CREATE FLASK APP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path=""
)

# Enable CORS for all domains so frontend works from file:// or http://
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(prediction_bp)
app.register_blueprint(history_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(location_bp)
app.register_blueprint(crops_bp)


# ============================================================
# FRONTEND & ROOT ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def home():
    """
    Serve the frontend homepage if requested by a browser,
    or return API info if JSON is requested.
    """
    accept = request.headers.get("Accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return jsonify({
            "success": True,
            "message": "Sustainable AI Crop Irrigation API is operational.",
            "version": "2.0.0",
            "endpoints": [
                "/api/predict/water",
                "/api/predict/complete",
                "/api/predict/weather/irrigation",
                "/api/predict/water/weather",
                "/api/history/",
                "/api/crops/",
                "/api/weather/",
                "/api/location/search",
                "/health"
            ]
        })

    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return send_from_directory(str(FRONTEND_DIR), "index.html")
    return jsonify({
        "success": True,
        "message": "Sustainable AI Crop Irrigation API is running."
    })


@app.route("/pages/<path:filename>", methods=["GET"])
def serve_pages(filename):
    return send_from_directory(str(FRONTEND_DIR / "pages"), filename)


@app.route("/css/<path:filename>", methods=["GET"])
def serve_css(filename):
    return send_from_directory(str(FRONTEND_DIR / "css"), filename)


@app.route("/js/<path:filename>", methods=["GET"])
def serve_js(filename):
    return send_from_directory(str(FRONTEND_DIR / "js"), filename)


@app.route("/assets/<path:filename>", methods=["GET"])
def serve_assets(filename):
    return send_from_directory(str(FRONTEND_DIR / "assets"), filename)


# ============================================================
# SYSTEM HEALTH & STATUS CHECK
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    db_info = get_db_status()
    return jsonify({
        "success": True,
        "status": "operational",
        "system": "Sustainable AI Crop Irrigation System",
        "database": db_info
    })


@app.route("/api/status", methods=["GET"])
def api_status():
    db_info = get_db_status()
    return jsonify({
        "success": True,
        "status": "ready",
        "database": db_info,
        "features": {
            "fao56_penman_monteith": True,
            "supported_crops": 55,
            "open_meteo_live_weather": True,
            "geocoding_search": True,
            "dual_mode_storage": True
        }
    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("🌱 Sustainable AI Crop Irrigation System Server")
    print(f"   Port:    {port}")
    print(f"   API Doc: http://0.0.0.0:{port}/api/status")
    print("=" * 60)
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
