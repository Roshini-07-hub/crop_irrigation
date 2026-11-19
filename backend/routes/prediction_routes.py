from flask import Blueprint, request, jsonify

from backend.services.water_service import (
    predict_water_requirement,
    predict_water_requirement_from_location
)

from backend.services.irrigation_service import (
    generate_irrigation_recommendation,
    generate_weather_based_recommendation
)

from backend.services.database_service import (
    save_prediction
)

from backend.services.weather_database_service import (
    save_weather_record
)


# ============================================================
# BLUEPRINT
# ============================================================

prediction_bp = Blueprint(
    "prediction",
    __name__,
    url_prefix="/api/predict"
)


# ============================================================
# WATER REQUIREMENT API
# ============================================================

@prediction_bp.route("/water", methods=["POST"])
def water_prediction():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "error": "Request body is required."
            }), 400


        # ----------------------------------------------------
        # CALCULATE WATER REQUIREMENT
        # ----------------------------------------------------

        result = predict_water_requirement(
            data
        )


        # ----------------------------------------------------
        # SAVE PREDICTION TO MONGODB
        # ----------------------------------------------------

        prediction_id = save_prediction(

            prediction_type="water",

            input_data=data,

            result_data=result

        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "prediction_id":
                prediction_id,

            "prediction":
                result

        }), 200


    except ValueError as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 400


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                "Internal server error.",

            "details":
                str(e)

        }), 500


# ============================================================
# COMPLETE IRRIGATION RECOMMENDATION API
# ============================================================

@prediction_bp.route("/complete", methods=["POST"])
def complete_prediction():

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "error":
                    "Request body is required."

            }), 400


        # ----------------------------------------------------
        # WATER REQUIREMENT
        # ----------------------------------------------------

        water_result = predict_water_requirement(
            data
        )


        # ----------------------------------------------------
        # IRRIGATION RECOMMENDATION
        # ----------------------------------------------------

        recommendation_result = (
            generate_irrigation_recommendation(

                crop=data["crop"],

                growth_stage=data["growth_stage"],

                soil_type=data["soil_type"],

                soil_moisture=float(
                    data["soil_moisture"]
                ),

                temperature_c=float(
                    data["temperature_c"]
                ),

                humidity=float(
                    data["humidity"]
                ),

                rainfall_mm=float(
                    data.get(
                        "rainfall_mm",
                        0
                    )
                ),

                sunlight_hours=float(
                    data["sunlight_hours"]
                ),

                wind_speed_kmh=float(
                    data["wind_speed_kmh"]
                ),

                field_area_hectare=float(
                    data["field_area_hectare"]
                ),

                current_irrigation_type=data[
                    "irrigation_type"
                ],

                irrigation_need=data.get(
                    "irrigation_need"
                )

            )
        )


        # ----------------------------------------------------
        # SAVE COMPLETE PREDICTION TO MONGODB
        # ----------------------------------------------------

        combined_result = {

            "water_requirement":
                water_result,

            "irrigation_recommendation":
                recommendation_result

        }


        prediction_id = save_prediction(

            prediction_type="complete",

            input_data=data,

            result_data=combined_result

        )


        # ----------------------------------------------------
        # COMBINED RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "prediction_id":
                prediction_id,

            "water_requirement":
                water_result,

            "irrigation_recommendation":
                recommendation_result

        }), 200


    except KeyError as e:

        return jsonify({

            "success": False,

            "error":
                f"Missing required field: {str(e)}"

        }), 400


    except ValueError as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 400


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                "Internal server error.",

            "details":
                str(e)

        }), 500


# ============================================================
# WEATHER + IRRIGATION RECOMMENDATION API
# ============================================================

@prediction_bp.route(
    "/weather/irrigation",
    methods=["POST"]
)
def weather_irrigation_prediction():

    try:

        data = request.get_json()

        if not data:

            return jsonify({

                "success": False,

                "error":
                    "Request body is required."

            }), 400


        # ----------------------------------------------------
        # REQUIRED INPUTS
        # ----------------------------------------------------

        required_fields = [

            "crop",

            "growth_stage",

            "soil_type",

            "soil_moisture",

            "latitude",

            "longitude"

        ]


        missing_fields = [

            field

            for field in required_fields

            if field not in data

        ]


        if missing_fields:

            return jsonify({

                "success": False,

                "error":
                    "Missing required fields.",

                "missing_fields":
                    missing_fields

            }), 400


        # ----------------------------------------------------
        # GET LIVE WEATHER + IRRIGATION RECOMMENDATION
        # ----------------------------------------------------

        result = generate_weather_based_recommendation(

            crop=data["crop"],

            growth_stage=data["growth_stage"],

            soil_type=data["soil_type"],

            soil_moisture=float(
                data["soil_moisture"]
            ),

            latitude=float(
                data["latitude"]
            ),

            longitude=float(
                data["longitude"]
            ),

            irrigation_need=data.get(
                "irrigation_need",
                "Medium"
            ),

            irrigation_type=data.get(
                "irrigation_type",
                "Drip"
            ),

            field_area_hectare=float(
                data.get(
                    "field_area_hectare",
                    1.0
                )
            ),

            sunlight_hours=float(
                data.get(
                    "sunlight_hours",
                    7.0
                )
            )
        )


        # ----------------------------------------------------
        # SAVE WEATHER DATA TO MONGODB
        # ----------------------------------------------------

        weather = result["weather"]


        weather_id = save_weather_record(

            weather_data=weather,

            latitude=weather["latitude"],

            longitude=weather["longitude"]

        )


        # ----------------------------------------------------
        # SAVE IRRIGATION RECOMMENDATION TO MONGODB
        # ----------------------------------------------------

        prediction_id = save_prediction(

            prediction_type="irrigation",

            input_data=data,

            result_data=result

        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "prediction_id":
                prediction_id,

            "weather_id":
                weather_id,

            "result":
                result

        }), 200


    except ValueError as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 400


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                "Internal server error.",

            "details":
                str(e)

        }), 500


# ============================================================
# WATER + WEATHER API
# ============================================================

@prediction_bp.route(
    "/water/weather",
    methods=["POST"]
)
def predict_water_from_weather():

    try:

        data = request.get_json()


        if not data:

            return jsonify({

                "success": False,

                "error":
                    "Request body is required."

            }), 400


        # ----------------------------------------------------
        # REQUIRED INPUTS
        # ----------------------------------------------------

        required_fields = [

            "crop",

            "growth_stage",

            "field_area_hectare",

            "latitude",

            "longitude",

            "irrigation_method"

        ]


        missing_fields = [

            field

            for field in required_fields

            if field not in data

            or data[field] in [None, ""]

        ]


        if missing_fields:

            return jsonify({

                "success": False,

                "error":
                    "Missing required fields.",

                "missing_fields":
                    missing_fields

            }), 400


        # ----------------------------------------------------
        # CALCULATE WATER REQUIREMENT
        # USING LOCATION + WEATHER + METHOD
        # ----------------------------------------------------

        result = (
            predict_water_requirement_from_location(

                crop=data["crop"],

                growth_stage=data[
                    "growth_stage"
                ],

                field_area_hectare=float(
                    data[
                        "field_area_hectare"
                    ]
                ),

                latitude=float(
                    data["latitude"]
                ),

                longitude=float(
                    data["longitude"]
                ),

                irrigation_method=data[
                    "irrigation_method"
                ]

            )
        )


        # ----------------------------------------------------
        # SAVE PREDICTION TO MONGODB
        # ----------------------------------------------------

        prediction_id = save_prediction(

            prediction_type="water_weather",

            input_data=data,

            result_data=result[
                "water_prediction"
            ]

        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "prediction_id":
                prediction_id,

            "prediction":
                result[
                    "water_prediction"
                ],

            "weather":
                result["weather"],

            "eto":
                result["eto"]

        }), 200


    except ValueError as e:

        return jsonify({

            "success": False,

            "error":
                str(e)

        }), 400


    except Exception as e:

        return jsonify({

            "success": False,

            "error":
                "Unable to calculate water requirement.",

            "details":
                str(e)

        }), 500


# ============================================================
# WATER API HEALTH
# ============================================================

@prediction_bp.route(
    "/water/health",
    methods=["GET"]
)
def water_health():

    return jsonify({

        "success": True,

        "service":
            "Water Requirement Prediction",

        "status":
            "running"

    }), 200


# ============================================================
# COMPLETE API HEALTH
# ============================================================

@prediction_bp.route(
    "/complete/health",
    methods=["GET"]
)
def complete_health():

    return jsonify({

        "success": True,

        "service":
            "Complete Irrigation Decision Support",

        "status":
            "running"

    }), 200