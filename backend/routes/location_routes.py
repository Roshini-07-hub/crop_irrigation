from flask import Blueprint, request, jsonify

from backend.services.geocoding_service import search_location


location_bp = Blueprint(
    "location",
    __name__,
    url_prefix="/api/location"
)


@location_bp.route("/search", methods=["GET"])
def location_search():
    try:
        query = request.args.get("q", "").strip()

        if not query:
            return jsonify({
                "success": False,
                "error": "Location search query is required."
            }), 400

        results = search_location(query)

        return jsonify({
            "success": True,
            "count": len(results),
            "locations": results
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Unable to search for location.",
            "details": str(e)
        }), 500