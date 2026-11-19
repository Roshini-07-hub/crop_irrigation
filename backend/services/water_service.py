"""
Water Requirement Service

Connects user input with the crop water requirement engine.

This service:
1. Validates user input
2. Calculates crop water requirement
3. Calculates irrigation requirement
4. Supports irrigation-method-based efficiency
5. Uses Open-Meteo weather data for location-based prediction
6. Returns water quantity in mm and litres
"""

from backend.ml.processing.water_require import (
    calculate_water_requirement
)

from backend.services.eto_service import get_eto


# ============================================================
# REFERENCE IRRIGATION EFFICIENCIES
# ============================================================

# These are indicative FIELD APPLICATION efficiencies
# from FAO guidance.
#
# Surface irrigation = 60%
# Sprinkler irrigation = 75%
# Drip irrigation = 90%
#
# These are reference assumptions, not guaranteed farm-specific
# efficiencies.

IRRIGATION_METHOD_EFFICIENCY = {

    "Surface": 0.60,

    "Drip": 0.90,

    "Sprinkler": 0.75

}


# ============================================================
# GET EFFICIENCY FROM IRRIGATION METHOD
# ============================================================

def get_irrigation_efficiency(irrigation_method):
    """
    Return the reference field application efficiency
    for the selected irrigation method.
    """

    if not irrigation_method:
        raise ValueError(
            "Irrigation method is required."
        )

    method = str(
        irrigation_method
    ).strip()


    if method not in IRRIGATION_METHOD_EFFICIENCY:

        valid_methods = ", ".join(
            IRRIGATION_METHOD_EFFICIENCY.keys()
        )

        raise ValueError(
            f"Invalid irrigation method: {method}. "
            f"Choose one of: {valid_methods}."
        )


    return IRRIGATION_METHOD_EFFICIENCY[
        method
    ]



# ============================================================
# VALIDATION - MANUAL INPUT
# ============================================================

def validate_water_input(data):
    """
    Validate manual user input before calculation.

    Manual prediction still accepts ETo and rainfall directly.
    Irrigation efficiency can be supplied directly for
    backward compatibility.
    """

    required_fields = [
        "crop",
        "growth_stage",
        "field_area_hectare",
        "eto_mm_day"
    ]


    missing_fields = [
        field
        for field in required_fields
        if field not in data
        or data[field] in [None, ""]
    ]


    if missing_fields:

        raise ValueError(
            f"Missing required fields: {missing_fields}"
        )


    try:

        field_area = float(
            data["field_area_hectare"]
        )

        eto = float(
            data["eto_mm_day"]
        )

        rainfall = float(
            data.get(
                "rainfall_mm",
                0
            )
        )


        # ----------------------------------------
        # Irrigation method OR direct efficiency
        # ----------------------------------------

        irrigation_method = data.get(
            "irrigation_method"
        )


        if irrigation_method:

            irrigation_efficiency = (
                get_irrigation_efficiency(
                    irrigation_method
                )
            )

        else:

            irrigation_efficiency = float(
                data.get(
                    "irrigation_efficiency",
                    0.80
                )
            )


    except (TypeError, ValueError):

        raise ValueError(
            "Numeric fields contain invalid values."
        )


    if field_area <= 0:

        raise ValueError(
            "Field area must be greater than zero."
        )


    if eto < 0:

        raise ValueError(
            "ETo cannot be negative."
        )


    if rainfall < 0:

        raise ValueError(
            "Rainfall cannot be negative."
        )


    if not 0 < irrigation_efficiency <= 1:

        raise ValueError(
            "Irrigation efficiency must be between 0 and 1."
        )


    return {

        "crop":
            str(
                data["crop"]
            ).strip(),

        "growth_stage":
            str(
                data["growth_stage"]
            ).strip(),

        "field_area_hectare":
            field_area,

        "eto_mm_day":
            eto,

        "rainfall_mm":
            rainfall,

        "irrigation_efficiency":
            irrigation_efficiency,

        "irrigation_method":
            irrigation_method

    }



# ============================================================
# MANUAL WATER PREDICTION
# ============================================================

def predict_water_requirement(data):
    """
    Process manual user input and return
    calculated water requirement.
    """

    clean_data = validate_water_input(
        data
    )


    result = calculate_water_requirement(

        crop=clean_data["crop"],

        growth_stage=clean_data[
            "growth_stage"
        ],

        field_area_hectare=clean_data[
            "field_area_hectare"
        ],

        eto_mm_day=clean_data[
            "eto_mm_day"
        ],

        rainfall_mm=clean_data[
            "rainfall_mm"
        ],

        irrigation_efficiency=clean_data[
            "irrigation_efficiency"
        ]

    )


    # Add method information to response
    if clean_data["irrigation_method"]:

        result["irrigation_method"] = (
            clean_data["irrigation_method"]
        )

        result["irrigation_efficiency"] = (
            clean_data["irrigation_efficiency"]
        )

        result["efficiency_status"] = (
            "FAO indicative field application efficiency"
        )


    return result



# ============================================================
# LOCATION-BASED WATER PREDICTION
# ============================================================

def predict_water_requirement_from_location(
    crop,
    growth_stage,
    field_area_hectare,
    latitude,
    longitude,
    irrigation_method=None,
    irrigation_efficiency=None
):
    """
    Calculate crop water requirement using real weather data
    and locally calculated FAO-56 Penman-Monteith ETo.

    ETo:
        Obtained from Open-Meteo weather data and calculated
        locally using FAO-56 Penman-Monteith.

    Irrigation efficiency:
        Preferably determined from the selected irrigation
        method using the FAO indicative reference values.

    A direct efficiency can still be supplied for backward
        compatibility/testing.
    """


    # ========================================================
    # VALIDATE BASIC INPUTS
    # ========================================================

    try:

        field_area_hectare = float(
            field_area_hectare
        )

        latitude = float(
            latitude
        )

        longitude = float(
            longitude
        )

    except (TypeError, ValueError):

        raise ValueError(
            "Field area, latitude, and longitude must be numeric."
        )


    if field_area_hectare <= 0:

        raise ValueError(
            "Field area must be greater than zero."
        )


    if latitude < -90 or latitude > 90:

        raise ValueError(
            "Latitude must be between -90 and 90."
        )


    if longitude < -180 or longitude > 180:

        raise ValueError(
            "Longitude must be between -180 and 180."
        )


    # ========================================================
    # DETERMINE IRRIGATION EFFICIENCY
    # ========================================================

    if irrigation_method:

        irrigation_method = str(
            irrigation_method
        ).strip()


        irrigation_efficiency = (
            get_irrigation_efficiency(
                irrigation_method
            )
        )

    elif irrigation_efficiency is not None:

        try:

            irrigation_efficiency = float(
                irrigation_efficiency
            )

        except (TypeError, ValueError):

            raise ValueError(
                "Irrigation efficiency must be numeric."
            )

    else:

        raise ValueError(
            "Please select an irrigation method."
        )


    if not 0 < irrigation_efficiency <= 1:

        raise ValueError(
            "Irrigation efficiency must be between 0 and 1."
        )


    # ========================================================
    # GET REAL WEATHER DATA
    # ========================================================

    eto_data = get_eto(

        latitude=latitude,

        longitude=longitude

    )


    eto_mm_day = eto_data[
        "eto_mm_day"
    ]


    # Rainfall from weather source

    rainfall_mm = eto_data[
        "precipitation_mm"
    ]


    # ========================================================
    # CROP WATER CALCULATION
    # ========================================================

    result = calculate_water_requirement(

        crop=crop,

        growth_stage=growth_stage,

        field_area_hectare=field_area_hectare,

        eto_mm_day=eto_mm_day,

        rainfall_mm=rainfall_mm,

        irrigation_efficiency=irrigation_efficiency

    )


    # ========================================================
    # ADD IRRIGATION METHOD INFORMATION
    # ========================================================

    result["irrigation_method"] = (
        irrigation_method
    )


    result["irrigation_efficiency"] = (
        irrigation_efficiency
    )


    result["efficiency_status"] = (
        "FAO indicative field application efficiency"
    )


    # ========================================================
    # RETURN COMPLETE RESULT
    # ========================================================

    return {

        "water_prediction":
            result,


        "weather": {

            "date":
                eto_data["date"],

            "latitude":
                eto_data["latitude"],

            "longitude":
                eto_data["longitude"],

            "temperature_mean_c":
                eto_data["tmean_c"],

            "temperature_max_c":
                eto_data["tmax_c"],

            "temperature_min_c":
                eto_data["tmin_c"],

            "humidity_percent":
                eto_data[
                    "relative_humidity_mean_pct"
                ],

            "wind_speed_10m_ms":
                eto_data[
                    "wind_speed_10m_ms"
                ],

            "rainfall_mm":
                rainfall_mm,

            "solar_radiation_mj_m2_day":
                eto_data[
                    "shortwave_radiation_mj_m2_day"
                ],

            "surface_pressure_kpa":
                eto_data[
                    "surface_pressure_kpa"
                ],

            "elevation_m":
                eto_data[
                    "elevation_m"
                ]

        },


        "eto": {

            "eto_mm_day":
                eto_data[
                    "eto_mm_day"
                ],

            "method":
                eto_data[
                    "method"
                ],

            "open_meteo_eto_mm_day":
                eto_data[
                    "open_meteo_eto_mm_day"
                ],

            "eto_difference_mm_day":
                eto_data[
                    "eto_difference_mm_day"
                ]

        }

    }



# ============================================================
# SIMPLE TEST
# ============================================================

if __name__ == "__main__":

    manual_input = {

        "crop":
            "Maize",

        "growth_stage":
            "Vegetative",

        "field_area_hectare":
            2,

        "eto_mm_day":
            5,

        "rainfall_mm":
            0,

        "irrigation_method":
            "Drip"

    }


    result = predict_water_requirement(
        manual_input
    )


    print("\n" + "=" * 60)

    print(
        "MANUAL USER WATER REQUIREMENT TEST"
    )

    print("=" * 60)


    for key, value in result.items():

        print(
            f"{key}: {value}"
        )


    print("=" * 60)