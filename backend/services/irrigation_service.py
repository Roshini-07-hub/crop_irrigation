"""
Irrigation Recommendation Service

Provides:
1. Irrigation priority
2. Recommended irrigation time
3. Recommended irrigation technique
4. Explanation/reason
5. Supporting factors

This is a transparent rule-based decision-support layer.
It is NOT an ML prediction target.
"""

from datetime import datetime


# ============================================================
# SUPPORTED VALUES
# ============================================================

VALID_GROWTH_STAGES = {
    "sowing",
    "vegetative",
    "flowering",
    "harvest"
}

VALID_IRRIGATION_NEEDS = {
    "low",
    "medium",
    "high"
}

VALID_IRRIGATION_TYPES = {
    "rainfed",
    "canal",
    "drip",
    "sprinkler",
    "surface",
    "flood"
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value):
    """Convert input to a clean lowercase string."""

    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# IRRIGATION PRIORITY
# ============================================================

def calculate_irrigation_priority(
    soil_moisture,
    temperature_c,
    humidity,
    rainfall_mm,
    sunlight_hours,
    wind_speed_kmh,
    irrigation_need=None,
    growth_stage=None
):
    """
    Determine irrigation priority using transparent rules.

    Soil moisture has a strong influence on the priority.

    Returns:
        LOW / MEDIUM / HIGH
    """

    score = 0
    reasons = []

    # --------------------------------------------------------
    # Soil moisture
    # --------------------------------------------------------

    if soil_moisture < 20:

        score += 6
        reasons.append("Very dry root-zone soil (<20%)")

    elif soil_moisture < 35:

        score += 4
        reasons.append("Dry soil condition (20-35%)")

    elif soil_moisture < 50:

        score += 1
        reasons.append("Moderately moist soil condition (35-50%)")

    elif soil_moisture < 70:

        score -= 3
        reasons.append("Adequate soil moisture (50-70%)")

    else:

        score -= 7
        reasons.append("High / saturated soil moisture (>70%)")


    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------

    if temperature_c >= 35:

        score += 3
        reasons.append("Very high temperature")

    elif temperature_c >= 30:

        score += 2
        reasons.append("High temperature")

    elif temperature_c >= 25:

        score += 1


    # --------------------------------------------------------
    # Humidity
    # --------------------------------------------------------

    if humidity < 40:

        score += 2
        reasons.append("Low humidity")

    elif humidity < 55:

        score += 1

    elif humidity > 80:

        score -= 1
        reasons.append("High humidity")


    # --------------------------------------------------------
    # Rainfall
    # --------------------------------------------------------

    if rainfall_mm <= 2:

        score += 2
        reasons.append("Very low recent rainfall")

    elif rainfall_mm <= 10:

        score += 1

    elif rainfall_mm >= 25:

        score -= 4
        reasons.append("Substantial recent rainfall")


    # --------------------------------------------------------
    # Sunlight
    # --------------------------------------------------------

    if sunlight_hours >= 9:

        score += 2
        reasons.append("High sunlight exposure")

    elif sunlight_hours >= 7:

        score += 1


    # --------------------------------------------------------
    # Wind
    # --------------------------------------------------------

    if wind_speed_kmh >= 15:

        score += 1
        reasons.append("High wind speed")


    # --------------------------------------------------------
    # Dataset irrigation need
    # --------------------------------------------------------

    need = normalize(irrigation_need)

    if need == "high":

        score += 3
        reasons.append("Dataset indicates high irrigation need")

    elif need == "medium":

        score += 1

    elif need == "low":

        score -= 2
        reasons.append("Dataset indicates low irrigation need")


    # --------------------------------------------------------
    # Growth stage
    # --------------------------------------------------------

    stage = normalize(growth_stage)

    if stage == "flowering":

        score += 2
        reasons.append(
            "Flowering stage has higher water sensitivity"
        )

    elif stage == "vegetative":

        score += 1

    elif stage == "harvest":

        score -= 1


    # --------------------------------------------------------
    # Final priority
    # --------------------------------------------------------

    # Agronomic safety bounds:
    # 1. Saturated soil (>= 75%) never requires immediate irrigation
    # 2. Critically dry root-zone (< 20%) requires immediate intervention
    if soil_moisture >= 75:
        priority = "LOW"
    elif soil_moisture < 20:
        priority = "HIGH"
    elif score >= 9:
        priority = "HIGH"
    elif score >= 4:
        priority = "MEDIUM"
    else:
        priority = "LOW"


    return priority, score, reasons


# ============================================================
# BEST IRRIGATION TIME
# ============================================================

def recommend_irrigation_time(
    priority,
    soil_moisture,
    temperature_c,
    humidity,
    sunlight_hours,
    wind_speed_kmh,
    rainfall_mm
):
    """
    Recommend a practical irrigation time window.

    Soil moisture is explicitly considered so that
    the recommendation can change with the farmer's
    selected soil condition.
    """

    # --------------------------------------------------------
    # VERY WET SOIL
    # --------------------------------------------------------

    if soil_moisture >= 70:

        return {
            "time_window":
                "Do not irrigate now; reassess after the soil dries",

            "preferred_period":
                "Reassess later",

            "reason":
                "Soil is very wet, so additional irrigation may "
                "increase waterlogging risk."
        }


    # --------------------------------------------------------
    # SUBSTANTIAL RAINFALL
    # --------------------------------------------------------

    if rainfall_mm >= 25:

        return {
            "time_window":
                "Delay irrigation and reassess after rainfall",

            "preferred_period":
                "After rainfall assessment",

            "reason":
                "Recent rainfall is substantial."
        }


    # --------------------------------------------------------
    # MOIST SOIL
    # --------------------------------------------------------

    if soil_moisture >= 60:

        return {
            "time_window":
                "Delay irrigation and reassess in the next cycle",

            "preferred_period":
                "Reassess later",

            "reason":
                "Soil moisture is already adequate, so immediate "
                "irrigation may not be necessary."
        }


    # --------------------------------------------------------
    # LOW PRIORITY
    # --------------------------------------------------------

    if priority == "LOW":

        return {
            "time_window":
                "No immediate irrigation required",

            "preferred_period":
                "Reassess during the next suitable irrigation cycle",

            "reason":
                "Current conditions indicate low irrigation priority."
        }


    # --------------------------------------------------------
    # VERY DRY SOIL
    # --------------------------------------------------------

    if soil_moisture < 20:

        return {
            "time_window":
                "Irrigate at the next suitable early-morning window: "
                "5:30 AM – 8:00 AM",

            "preferred_period":
                "Early morning",

            "reason":
                "Soil is very dry, so irrigation should not be "
                "unnecessarily delayed."
        }


    # --------------------------------------------------------
    # DRY SOIL
    # --------------------------------------------------------

    if soil_moisture < 30:

        return {
            "time_window":
                "Early morning: 5:30 AM – 8:00 AM",

            "preferred_period":
                "Early morning",

            "reason":
                "Soil is dry and early morning helps reduce "
                "water loss during daytime conditions."
        }


    # --------------------------------------------------------
    # VERY HOT CONDITIONS
    # --------------------------------------------------------

    if temperature_c >= 35:

        return {
            "time_window":
                "Early morning: 5:30 AM – 8:00 AM",

            "preferred_period":
                "Early morning",

            "reason":
                "High temperature makes early morning preferable "
                "to avoid irrigation during the hottest part of the day."
        }


    # --------------------------------------------------------
    # HIGH WIND
    # --------------------------------------------------------

    if wind_speed_kmh >= 15:

        return {
            "time_window":
                "Early morning: 5:30 AM – 8:00 AM",

            "preferred_period":
                "Early morning",

            "reason":
                "Higher wind conditions can increase water losses, "
                "so an early-morning window is preferred."
        }


    # --------------------------------------------------------
    # HIGH SUNLIGHT / LOW HUMIDITY
    # --------------------------------------------------------

    if sunlight_hours >= 9 and humidity < 50:

        return {
            "time_window":
                "Early morning: 5:30 AM – 8:00 AM",

            "preferred_period":
                "Early morning",

            "reason":
                "High sunlight and relatively low humidity favor "
                "irrigation during the cooler morning period."
        }


    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return {
        "time_window":
            "Early morning: 5:30 AM – 8:00 AM",

        "preferred_period":
            "Early morning",

        "reason":
            "Early morning is selected as the default practical "
            "irrigation window to reduce exposure to daytime heat."
    }


# ============================================================
# IRRIGATION TECHNIQUE
# ============================================================

def recommend_irrigation_technique(
    crop,
    soil_type,
    field_area_hectare,
    current_irrigation_type,
    rainfall_mm,
    soil_moisture
):
    """
    Recommend an irrigation technique.

    Soil moisture is considered before the existing
    irrigation-system preference.
    """

    crop_name = str(crop).strip()

    soil = normalize(soil_type)

    current_type = normalize(current_irrigation_type)


    # --------------------------------------------------------
    # VERY WET SOIL
    # --------------------------------------------------------

    if soil_moisture >= 70:

        return {
            "technique":
                "No irrigation currently",

            "reason":
                "Soil is very wet. Additional irrigation is "
                "not recommended until soil moisture decreases."
        }


    # --------------------------------------------------------
    # MOIST SOIL
    # --------------------------------------------------------

    if soil_moisture >= 60:

        return {
            "technique":
                "Delay irrigation",

            "reason":
                "Soil moisture is already adequate. Irrigation "
                "can be reassessed when moisture decreases."
        }


    # --------------------------------------------------------
    # VERY DRY SOIL
    # --------------------------------------------------------

    if soil_moisture < 20:

        return {
            "technique":
                "Drip irrigation",

            "reason":
                "The soil is very dry. Controlled root-zone "
                "application can provide water efficiently "
                "while reducing unnecessary field losses."
        }


    # --------------------------------------------------------
    # DRY SOIL
    # --------------------------------------------------------

    if soil_moisture < 30:

        if soil == "sandy":

            return {
                "technique":
                    "Drip irrigation",

                "reason":
                    "Dry sandy soil can lose water quickly, so "
                    "controlled root-zone application is recommended."
            }

        return {
            "technique":
                "Drip irrigation",

            "reason":
                "The soil is dry and controlled irrigation can "
                "deliver water near the crop root zone."
        }


    # --------------------------------------------------------
    # RAINFED SITUATION
    # --------------------------------------------------------

    if current_type == "rainfed":

        if soil_moisture < 40 and rainfall_mm < 10:

            return {
                "technique":
                    "Drip irrigation",

                "reason":
                    "Soil moisture is limited and recent rainfall "
                    "is low; drip irrigation can be considered "
                    "as a supplementary method where infrastructure "
                    "is available."
            }

        return {
            "technique":
                "Rainwater-supported irrigation",

            "reason":
                "The current system is rainfed and current "
                "conditions do not indicate an immediate need "
                "for intensive irrigation."
        }


    # --------------------------------------------------------
    # EXISTING DRIP SYSTEM
    # --------------------------------------------------------

    if current_type == "drip":

        return {
            "technique":
                "Drip irrigation",

            "reason":
                "Drip irrigation is already available and can "
                "provide controlled water delivery near the "
                "crop root zone."
        }


    # --------------------------------------------------------
    # EXISTING SPRINKLER SYSTEM
    # --------------------------------------------------------

    if current_type == "sprinkler":

        if rainfall_mm < 25:

            return {
                "technique":
                    "Sprinkler irrigation",

                "reason":
                    "The existing sprinkler system can be retained "
                    "when rainfall conditions do not indicate a "
                    "need to delay irrigation."
            }

        return {
            "technique":
                "Delay irrigation",

            "reason":
                "Recent rainfall suggests irrigation should be "
                "reassessed before additional application."
        }


    # --------------------------------------------------------
    # CANAL IRRIGATION
    # --------------------------------------------------------

    if current_type == "canal":

        if soil == "sandy":

            return {
                "technique":
                    "Drip irrigation",

                "reason":
                    "Sandy soil can have faster drainage, so "
                    "controlled root-zone application is recommended "
                    "where feasible."
            }


        if soil in {"loamy", "silt", "silty"}:

            return {
                "technique":
                    "Surface irrigation",

                "reason":
                    "For canal-fed fields with loamy or silt soil, "
                    "surface irrigation can be considered where "
                    "field leveling and distribution are suitable."
            }


        return {
            "technique":
                "Surface irrigation",

            "reason":
                "Canal water is available and surface irrigation "
                "is a practical option where field conditions permit."
        }


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return {
        "technique":
            "Drip irrigation",

        "reason":
            f"Drip irrigation is provided as a water-efficient "
            f"default recommendation for {crop_name}, subject to "
            f"local feasibility and infrastructure availability."
    }


# ============================================================
# COMPLETE RECOMMENDATION
# ============================================================

def generate_irrigation_recommendation(
    crop,
    growth_stage,
    soil_type,
    soil_moisture,
    temperature_c,
    humidity,
    rainfall_mm,
    sunlight_hours,
    wind_speed_kmh,
    field_area_hectare,
    current_irrigation_type,
    irrigation_need=None
):
    """
    Generate the complete irrigation recommendation.
    """

    # --------------------------------------------------------
    # Validate numerical inputs
    # --------------------------------------------------------

    numeric_values = {
        "soil_moisture": soil_moisture,
        "temperature_c": temperature_c,
        "humidity": humidity,
        "rainfall_mm": rainfall_mm,
        "sunlight_hours": sunlight_hours,
        "wind_speed_kmh": wind_speed_kmh,
        "field_area_hectare": field_area_hectare
    }

    for name, value in numeric_values.items():

        if value is None:

            raise ValueError(
                f"{name} is required."
            )

        if value < 0:

            raise ValueError(
                f"{name} cannot be negative."
            )


    if soil_moisture > 100:

        raise ValueError(
            "Soil moisture cannot exceed 100."
        )


    if field_area_hectare <= 0:

        raise ValueError(
            "Field area must be greater than zero."
        )


    # --------------------------------------------------------
    # Validate categorical values
    # --------------------------------------------------------

    stage = normalize(growth_stage)

    need = normalize(irrigation_need)

    irrigation_type = normalize(
        current_irrigation_type
    )


    if stage not in VALID_GROWTH_STAGES:

        raise ValueError(
            f"Invalid growth stage: {growth_stage}"
        )


    if need and need not in VALID_IRRIGATION_NEEDS:

        raise ValueError(
            f"Invalid irrigation need: {irrigation_need}"
        )


    if irrigation_type not in VALID_IRRIGATION_TYPES:

        raise ValueError(
            f"Invalid irrigation type: {current_irrigation_type}"
        )

    if irrigation_type in ["surface", "flood"]:
        irrigation_type = "canal"


    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    priority, score, priority_reasons = (
        calculate_irrigation_priority(

            soil_moisture=soil_moisture,

            temperature_c=temperature_c,

            humidity=humidity,

            rainfall_mm=rainfall_mm,

            sunlight_hours=sunlight_hours,

            wind_speed_kmh=wind_speed_kmh,

            irrigation_need=irrigation_need,

            growth_stage=growth_stage
        )
    )


    # --------------------------------------------------------
    # Timing
    # --------------------------------------------------------

    timing = recommend_irrigation_time(

        priority=priority,

        soil_moisture=soil_moisture,

        temperature_c=temperature_c,

        humidity=humidity,

        sunlight_hours=sunlight_hours,

        wind_speed_kmh=wind_speed_kmh,

        rainfall_mm=rainfall_mm
    )


    # --------------------------------------------------------
    # Technique
    # --------------------------------------------------------

    technique = recommend_irrigation_technique(

        crop=crop,

        soil_type=soil_type,

        field_area_hectare=field_area_hectare,

        current_irrigation_type=current_irrigation_type,

        rainfall_mm=rainfall_mm,

        soil_moisture=soil_moisture
    )


    # --------------------------------------------------------
    # Explanation
    # --------------------------------------------------------

    explanation_parts = []

    if priority_reasons:

        explanation_parts.extend(
            priority_reasons
        )


    explanation = "; ".join(
        explanation_parts
    )


    if not explanation:

        explanation = (
            "Current environmental conditions do not indicate "
            "strong irrigation stress."
        )


    # Add timing/technique explanation

    explanation = (
        f"{explanation}; "
        f"{timing['reason']}; "
        f"{technique['reason']}"
    )


    # --------------------------------------------------------
    # Real-Time Operational Water Quantity for Recommendation
    # --------------------------------------------------------
    if priority == "LOW" or soil_moisture >= 60:
        recommended_water_litres = 0
        volume_display = "0 Litres (Adequate soil moisture)"
        pump_display = "0 Hours (No pumping needed)"
        action_summary = "Soil moisture is currently sufficient. Delay irrigation to conserve water."
    else:
        try:
            from backend.ml.processing.farmer_water_usage import calculate_farmer_water_plan
            est_method = "Drip" if "drip" in technique["technique"].lower() or "drip" in str(current_irrigation_type).lower() else (
                "Sprinkler" if "sprinkler" in technique["technique"].lower() or "sprinkler" in str(current_irrigation_type).lower() else "Surface"
            )
            plan = calculate_farmer_water_plan(
                crop=crop,
                growth_stage=growth_stage,
                field_area_hectare=field_area_hectare,
                daily_net_etc_mm=max(2.5, float(temperature_c) / 8.0),
                daily_gross_mm=max(3.5, float(temperature_c) / 6.0),
                irrigation_method=est_method,
                soil_type=soil_type,
                pump_hp=5.0
            )
            recommended_water_litres = plan["event_volume_litres"]
            volume_display = f"{plan['event_volume_litres']:,} Litres"
            pump_display = plan["pump_shift_display"]
            action_summary = f"Apply {volume_display} during the recommended time window ({pump_display})."
        except Exception:
            recommended_water_litres = round(field_area_hectare * 500000)
            volume_display = f"{recommended_water_litres:,} Litres"
            pump_display = "~11 Hours (5 HP)"
            action_summary = f"Apply {volume_display} during the recommended time window."

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {

        "crop":
            crop,

        "growth_stage":
            growth_stage,

        "irrigation_priority":
            priority,

        "priority_score":
            score,

        "recommended_water_litres":
            recommended_water_litres,

        "event_volume_display":
            volume_display,

        "pump_shift_display":
            pump_display,

        "action_summary":
            action_summary,

        "recommended_time":
            timing["time_window"],

        "preferred_period":
            timing["preferred_period"],

        "time_reason":
            timing["reason"],

        "recommended_technique":
            technique["technique"],

        "technique_reason":
            technique["reason"],

        "explanation":
            explanation,

        "priority_reasons":
            priority_reasons,

        "factors":
            priority_reasons,

        "reason":
            timing["reason"],

        "inputs": {

            "soil_type":
                soil_type,

            "soil_moisture":
                soil_moisture,

            "temperature_c":
                temperature_c,

            "humidity":
                humidity,

            "rainfall_mm":
                rainfall_mm,

            "sunlight_hours":
                sunlight_hours,

            "wind_speed_kmh":
                wind_speed_kmh,

            "field_area_hectare":
                field_area_hectare,

            "current_irrigation_type":
                current_irrigation_type,

            "irrigation_need":
                irrigation_need
        },

        "generated_at":
            datetime.now().isoformat()
    }


# ============================================================
# WEATHER-BASED RECOMMENDATION
# ============================================================

def generate_weather_based_recommendation(
    crop,
    growth_stage,
    soil_type,
    soil_moisture,
    latitude,
    longitude,
    irrigation_need="Medium",
    irrigation_type="Drip",
    field_area_hectare=1.0,
    sunlight_hours=7.0
):
    """
    Generate irrigation recommendation using live weather data.
    """

    from backend.services.weather_service import get_weather


    weather = get_weather(
        latitude,
        longitude
    )


    recommendation = generate_irrigation_recommendation(

        crop=crop,

        growth_stage=growth_stage,

        soil_type=soil_type,

        soil_moisture=soil_moisture,

        temperature_c=weather["temperature_c"],

        humidity=weather["humidity"],

        rainfall_mm=weather["rainfall_mm"],

        sunlight_hours=sunlight_hours,

        wind_speed_kmh=weather["wind_speed_kmh"],

        field_area_hectare=field_area_hectare,

        current_irrigation_type=irrigation_type,

        irrigation_need=irrigation_need
    )


    return {

        "weather":
            weather,

        "irrigation_recommendation":
            recommendation
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_conditions = [

        ("Very Dry", 10),

        ("Dry", 25),

        ("Moderately Moist", 40),

        ("Moist", 60),

        ("Very Wet", 80)
    ]


    for label, moisture in test_conditions:

        result = generate_irrigation_recommendation(

            crop="Maize",

            growth_stage="Vegetative",

            soil_type="Loamy",

            soil_moisture=moisture,

            temperature_c=30,

            humidity=60,

            rainfall_mm=2,

            sunlight_hours=7,

            wind_speed_kmh=8,

            field_area_hectare=2,

            current_irrigation_type="Drip",

            irrigation_need="Medium"
        )


        print("\n" + "=" * 60)

        print(
            f"SOIL CONDITION: {label}"
        )

        print("=" * 60)

        print(
            "Priority:",
            result["irrigation_priority"]
        )

        print(
            "Priority score:",
            result["priority_score"]
        )

        print(
            "Recommended time:",
            result["recommended_time"]
        )

        print(
            "Recommended technique:",
            result["recommended_technique"]
        )

        print(
            "Explanation:",
            result["explanation"]
        )