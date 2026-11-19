"""
Real-Time Farmer Water Usage & Practical Irrigation Scheduling Engine

Translates theoretical FAO-56 atmospheric evapotranspiration (ETc) into
actual farmer-executable irrigation schedules and operational water metrics:
1. Soil Available Water Capacity (AWC) & Root Zone Reservoir (TAW / RAW)
2. Realistic Irrigation Event Volume (applied per watering event, NOT daily)
3. Irrigation Interval (days between water applications)
4. Pump Running Hours (e.g. 5 HP, 3 HP, 7.5 HP electric/diesel pump sets)
5. Crop Archetype & Stage-specific Agricultural Guidelines (e.g. Utera/Paira
   relay pulses, AWD rice, staged wheat, and drip horticulture)
6. Criticality and over-irrigation warning alerts
"""

from typing import Dict, Any, Optional
import math


# ============================================================
# 1. SOIL AVAILABLE WATER CAPACITY (mm of water per meter soil depth)
# ============================================================

SOIL_AWC_MM_PER_M = {
    "clay": 180.0,        # Heavy black cotton soils (high retention)
    "loamy": 140.0,       # Medium loams / alluvial (standard default)
    "silty": 150.0,       # Silt loam
    "sandy loam": 100.0,  # Red chalka / sandy loams
    "sandy": 65.0         # Light sandy soils (fast drainage)
}


# ============================================================
# 2. STANDARD AGRICULTURAL PUMP DISCHARGE CAPACITIES
# ============================================================

PUMP_DISCHARGE_LPH = {
    3.0: 25000.0,   # ~6.9 L/sec
    5.0: 45000.0,   # ~12.5 L/sec (standard Indian farm pump)
    7.5: 65000.0,   # ~18.1 L/sec
    10.0: 85000.0   # ~23.6 L/sec
}


# ============================================================
# 3. CROP ARCHETYPES & REAL-WORLD FARMER PRACTICES
# ============================================================

CROP_ARCHETYPES = {
    "pulse_hardy_residual": {
        "crops": [
            "khesari", "moth", "horse-gram", "guar seed", "gram", "masoor",
            "urad", "moong(green gram)", "other rabi pulses", "other kharif pulses",
            "other summer pulses", "cowpea(lobia)", "arhar/tur", "peas & beans (pulses)"
        ],
        "category_title": "Drought-Hardy Pulse / Residual Moisture",
        "seasonal_irrigations": "0 - 2 Irrigations Total (often 100% rainfed)",
        "roots_by_stage": {
            "sowing": (0.25, 0.50),
            "vegetative": (0.50, 0.55),
            "flowering": (0.80, 0.60),
            "harvest": (0.90, 0.65)
        },
        "default_event_gross_mm": {
            "sprinkler": 45.0,
            "surface": 50.0,
            "drip": 6.0
        },
        "min_interval_days": 12,
        "max_interval_days": 18,
        "danger_daily_watering": True,
        "advice_templates": {
            "sowing": "Sown into residual moisture after paddy harvest (Paira/Utera). Only provide a light pre-sowing soaking if topsoil is completely dry.",
            "vegetative": "Deep taproot explores residual soil moisture. Avoid standing water; excessive vegetative irrigation increases foliage at the cost of grain yield.",
            "flowering": "CRITICAL STAGE: Pulses are sensitive to severe drought at flowering. If topsoil is dry, provide ONLY 1 single light irrigation (35–45 mm). DO NOT IRRIGATE DAILY! Daily watering causes severe flower drop, collar rot, and root asphyxiation.",
            "harvest": "Withhold all irrigation 20 days prior to harvest to promote uniform pod drying and prevent late fungal infection."
        }
    },
    "cereal_staged": {
        "crops": [
            "wheat", "barley", "maize", "bajra", "jowar", "ragi",
            "small millets", "other cereals"
        ],
        "category_title": "Staged Cereal Field Crop",
        "seasonal_irrigations": "4 - 6 Irrigations (Wheat) / 3 - 4 (Maize/Millets)",
        "roots_by_stage": {
            "sowing": (0.25, 0.50),
            "vegetative": (0.55, 0.50),
            "flowering": (0.90, 0.50),
            "harvest": (1.00, 0.55)
        },
        "default_event_gross_mm": {
            "sprinkler": 50.0,
            "surface": 65.0,
            "drip": 7.0
        },
        "min_interval_days": 10,
        "max_interval_days": 15,
        "danger_daily_watering": False,
        "advice_templates": {
            "sowing": "Provide 1 initial irrigation at sowing/CRI stage (21 days after sowing for wheat) to establish crown roots.",
            "vegetative": "Maintain active root growth. Irrigate every 12–15 days based on soil moisture depletion.",
            "flowering": "CRITICAL FLOWERING / HEADING STAGE: Moisture stress now reduces grain count per ear head. Apply 1 scheduled irrigation event this cycle.",
            "harvest": "Stop irrigation at physiological dough stage (10–14 days before harvesting) to allow grain hardening."
        }
    },
    "rice_awd": {
        "crops": ["rice"],
        "category_title": "Semi-Aquatic Cereal (Alternate Wetting & Drying)",
        "seasonal_irrigations": "15 - 20 Intermittent Cycles",
        "roots_by_stage": {
            "sowing": (0.15, 0.20),
            "vegetative": (0.30, 0.20),
            "flowering": (0.40, 0.20),
            "harvest": (0.40, 0.20)
        },
        "default_event_gross_mm": {
            "sprinkler": 40.0,
            "surface": 60.0,
            "drip": 8.0
        },
        "min_interval_days": 3,
        "max_interval_days": 5,
        "danger_daily_watering": False,
        "advice_templates": {
            "sowing": "Maintain shallow water layer (2 cm) during initial nursery / seedling transplanting.",
            "vegetative": "Follow Alternate Wetting & Drying (AWD): Allow water to drop 2–5 cm below soil surface before re-irrigating.",
            "flowering": "CRITICAL PANICLE / FLOWERING STAGE: Maintain 3–5 cm standing water to prevent pollen sterility.",
            "harvest": "Drain field completely 10–12 days prior to harvest to facilitate harvesting operations."
        }
    },
    "oilseed_standard": {
        "crops": [
            "rapeseed &mustard", "linseed", "safflower", "niger seed", "sesamum",
            "castor seed", "sunflower", "soyabean", "groundnut", "other oilseeds", "oilseeds total"
        ],
        "category_title": "Oilseed Crop",
        "seasonal_irrigations": "2 - 4 Irrigations Total",
        "roots_by_stage": {
            "sowing": (0.25, 0.50),
            "vegetative": (0.50, 0.50),
            "flowering": (0.80, 0.50),
            "harvest": (0.90, 0.55)
        },
        "default_event_gross_mm": {
            "sprinkler": 40.0,
            "surface": 55.0,
            "drip": 6.0
        },
        "min_interval_days": 10,
        "max_interval_days": 15,
        "danger_daily_watering": True,
        "advice_templates": {
            "sowing": "Pre-sowing irrigation ensures uniform germination. Avoid deep standing water.",
            "vegetative": "Encourage branching and root deepening with spaced irrigations every 12–14 days.",
            "flowering": "CRITICAL FLOWERING & PEGGING/CAPSULE STAGE: Provide 1 scheduled irrigation to maximize oil content and pod filling.",
            "harvest": "Withhold water when lower leaves turn yellow and capsules/pods begin browning."
        }
    },
    "commercial_cash": {
        "crops": ["cotton(lint)", "sugarcane", "banana"],
        "category_title": "High-Value Commercial Cash Crop",
        "seasonal_irrigations": "4 - 6 (Cotton) / 18 - 25 (Sugarcane/Banana)",
        "roots_by_stage": {
            "sowing": (0.30, 0.50),
            "vegetative": (0.70, 0.55),
            "flowering": (1.10, 0.55),
            "harvest": (1.20, 0.60)
        },
        "default_event_gross_mm": {
            "sprinkler": 50.0,
            "surface": 70.0,
            "drip": 8.0
        },
        "min_interval_days": 10,
        "max_interval_days": 15,
        "danger_daily_watering": False,
        "advice_templates": {
            "sowing": "Ensure adequate soil profile moisture for early root tap development.",
            "vegetative": "Support rapid biomass growth. Irrigate every 10–12 days for surface or daily via drip.",
            "flowering": "CRITICAL SQUARING / BOLL / FLOWERING STAGE: Moisture stress causes square and boll dropping in cotton. Maintain steady moisture.",
            "harvest": "Terminate irrigation 2–3 weeks before boll opening/harvest to prevent boll rot and encourage fiber maturity."
        }
    },
    "vegetable_frequent": {
        "crops": [
            "potato", "onion", "garlic", "dry chillies", "tomato",
            "ginger", "turmeric", "coriander"
        ],
        "category_title": "Shallow-Rooted Vegetable & Spice",
        "seasonal_irrigations": "8 - 14 Irrigations (Surface) / Daily-Alternate Drip",
        "roots_by_stage": {
            "sowing": (0.20, 0.40),
            "vegetative": (0.35, 0.40),
            "flowering": (0.50, 0.40),
            "harvest": (0.50, 0.45)
        },
        "default_event_gross_mm": {
            "sprinkler": 30.0,
            "surface": 45.0,
            "drip": 5.0
        },
        "min_interval_days": 4,
        "max_interval_days": 7,
        "danger_daily_watering": False,
        "advice_templates": {
            "sowing": "Keep seedbed / ridge moist for smooth emergence and tuber sprout.",
            "vegetative": "Shallow roots require light, frequent watering every 4–6 days to prevent moisture fluctuation.",
            "flowering": "CRITICAL BULB / TUBER / FLOWERING STAGE: Water stress causes bulb cracking and blossom drop. Maintain steady moisture.",
            "harvest": "Stop irrigation 7–10 days before harvest to allow skins to cure and extend shelf life."
        }
    },
    "plantation_trees": {
        "crops": [
            "arecanut", "coconut", "cashewnut", "black pepper", "cardamom",
            "tobacco", "jute", "mesta", "sannhamp", "tapioca", "sweet potato"
        ],
        "category_title": "Plantation / Perennial Crop",
        "seasonal_irrigations": "Regular Scheduled Basin / Drip",
        "roots_by_stage": {
            "sowing": (0.40, 0.50),
            "vegetative": (0.80, 0.50),
            "flowering": (1.20, 0.50),
            "harvest": (1.20, 0.50)
        },
        "default_event_gross_mm": {
            "sprinkler": 40.0,
            "surface": 60.0,
            "drip": 8.0
        },
        "min_interval_days": 8,
        "max_interval_days": 14,
        "danger_daily_watering": False,
        "advice_templates": {
            "sowing": "Provide basin watering to settle roots and establish tree root systems.",
            "vegetative": "Apply water in circular basins or via drip ring around canopy drip line.",
            "flowering": "Support flowering and nut setting. Irrigate basins every 8–12 days in dry periods.",
            "harvest": "Maintain moderate moisture to sustain next seasonal flush."
        }
    }
}


# ============================================================
# 4. RESOLVE CROP ARCHETYPE
# ============================================================

def get_crop_archetype(crop_name: str) -> Dict[str, Any]:
    """Identify the matching agricultural profile for any crop."""
    c = str(crop_name).strip().lower()

    for arch_key, arch in CROP_ARCHETYPES.items():
        for candidate in arch["crops"]:
            if candidate in c or c in candidate:
                return arch

    # Fallback to general cereal/field crop archetype
    return CROP_ARCHETYPES["cereal_staged"]


# ============================================================
# 5. MAIN FARMER WATER USAGE CALCULATION
# ============================================================

def calculate_farmer_water_plan(
    crop: str,
    growth_stage: str,
    field_area_hectare: float,
    daily_net_etc_mm: float,
    daily_gross_mm: float,
    irrigation_method: str = "Sprinkler",
    irrigation_efficiency: float = 0.75,
    soil_type: str = "Loamy",
    pump_hp: float = 5.0
) -> Dict[str, Any]:
    """
    Calculate practical, real-world farmer water usage metrics.

    Returns:
    --------
    dict containing:
        - event_volume_litres: Actual litres to apply per irrigation event
        - event_gross_depth_mm: Gross application depth per event (mm)
        - irrigation_interval_days: Recommended days between irrigations
        - irrigation_interval_display: Human-readable interval text
        - pump_hours_per_event: Hours to run pump (5 HP default)
        - pump_hp: Pump rating used for calculation
        - seasonal_irrigations_summary: Typical total irrigations in crop cycle
        - stage_criticality: Sensitivity of current stage
        - farmer_practical_guideline: Clear agronomic guidance
        - danger_warning: Over-irrigation alert if daily watering is harmful
        - daily_consumption_clarification: Explanation of ETc vs pumping target
    """
    method_clean = str(irrigation_method or "Sprinkler").strip().lower()
    stage_clean = str(growth_stage or "Flowering").strip().lower()
    soil_clean = str(soil_type or "Loamy").strip().lower()

    # Determine soil AWC (mm/m)
    soil_awc = SOIL_AWC_MM_PER_M.get(soil_clean, 140.0)

    # Determine archetype & root dynamics
    archetype = get_crop_archetype(crop)

    # Normalize stage key
    stage_key = "flowering"
    if any(k in stage_clean for k in ["sow", "init"]):
        stage_key = "sowing"
    elif any(k in stage_clean for k in ["veg", "dev"]):
        stage_key = "vegetative"
    elif any(k in stage_clean for k in ["harv", "late"]):
        stage_key = "harvest"

    root_depth_m, depletion_p = archetype["roots_by_stage"].get(
        stage_key, (0.75, 0.50)
    )

    # Root zone water holding capacity
    taw_mm = soil_awc * root_depth_m
    raw_mm = depletion_p * taw_mm

    # Effective daily net evapotranspiration
    etc = max(0.2, float(daily_net_etc_mm))
    eff = max(0.1, min(1.0, float(irrigation_efficiency or 0.75)))
    area = max(0.01, float(field_area_hectare))
    hp = float(pump_hp) if pump_hp in PUMP_DISCHARGE_LPH else 5.0
    pump_rate = PUMP_DISCHARGE_LPH.get(hp, 45000.0)

    # Calculate irrigation event depth and interval based on method
    if "drip" in method_clean:
        # Drip is applied in micro-doses daily or every 2 days
        interval_days = 1 if etc >= 3.5 else 2
        event_net_depth_mm = round(etc * interval_days, 2)
        event_gross_depth_mm = round(event_net_depth_mm / eff, 2)
        interval_display = "Daily" if interval_days == 1 else "Every 2 Days"
        seasonal_summary = "Daily / Alternate-Day Micro-Dosing (60-80 cycles across season)"
    else:
        # Sprinkler or Surface: Applied in full soil-replenishing cycles
        is_sprinkler = "sprinkler" in method_clean
        seasonal_summary = archetype["seasonal_irrigations"]
        
        # In farmer practice, equipment limits single application depth:
        # Sprinkler sets typically apply 35 - 45 mm gross to avoid ponding/runoff
        # Surface border/furrow applies 50 - 65 mm gross
        if is_sprinkler:
            target_net = min(max(raw_mm * 0.6, 28.0), 38.0)
            event_net_depth_mm = round(target_net, 1)
            event_gross_depth_mm = round(event_net_depth_mm / eff, 1)
        else:
            target_net = min(max(raw_mm * 0.7, 35.0), 50.0)
            event_net_depth_mm = round(target_net, 1)
            event_gross_depth_mm = round(event_net_depth_mm / eff, 1)

        # Calculate interval in days based on ETc consumption rate
        calculated_interval = max(3, round(event_net_depth_mm / etc))
        min_i = archetype["min_interval_days"]
        max_i = archetype["max_interval_days"]
        interval_days = max(min_i, min(max_i, calculated_interval))

        interval_display = f"Every {interval_days} - {interval_days + 2} Days"

    # Volume per irrigation event in litres
    event_volume_litres = round(event_gross_depth_mm * area * 10000)

    # Pump runtime per event and practical shift breakdown
    pump_hours = round(event_volume_litres / pump_rate, 1)
    if pump_hours <= 8.0:
        pump_shift_display = f"~{pump_hours} Hours"
        shift_guidance = f"Can be applied in 1 shift of ~{pump_hours} hours."
    else:
        num_shifts = math.ceil(pump_hours / 7.0)
        shift_hrs = round(pump_hours / num_shifts, 1)
        pump_shift_display = f"~{pump_hours}h ({num_shifts} shifts × ~{shift_hrs}h)"
        shift_guidance = (
            f"Do not run continuously! Subdivide the {area} ha (~{round(area * 2.47, 1)} acres) "
            f"into {num_shifts} border strips/kiaris and irrigate 1 plot per day (~{shift_hrs} hrs/shift) "
            f"over {num_shifts} days matching agricultural power availability."
        )

    # Stage Criticality
    if stage_key == "flowering":
        criticality = "CRITICAL (Flowering Stage - High Water Sensitivity)"
    elif stage_key == "vegetative":
        criticality = "MODERATE (Vegetative Stage)"
    elif stage_key == "sowing":
        criticality = "IMPORTANT (Establishment Stage)"
    else:
        criticality = "LOW / WITHHOLD (Maturity Stage - Stop Irrigation)"

    # Agronomic guideline text
    farmer_guideline = archetype["advice_templates"].get(
        stage_key, "Irrigate based on soil moisture depletion."
    )

    # Advisory / Warning based on method and crop archetype
    if "drip" in method_clean:
        warning_alert = (
            f"💧 Drip Micro-Irrigation Mode Active: Drip systems apply water in short daily runtimes (~{pump_hours} hrs) "
            f"directly to the root zone to match daily evaporative loss. If you use standard Flood/Surface or Sprinkler "
            f"irrigation instead, switch the 'Irrigation Method' dropdown above to view the 10–12 day scheduled interval."
        )
    elif archetype["danger_daily_watering"]:
        warning_alert = (
            f"⚠️ DO NOT IRRIGATE DAILY! {crop} is highly drought-tolerant. "
            f"Applying water daily causes collar rot, flower drop, and root decay. "
            f"The daily figure of {round(daily_gross_mm * area * 10000):,} L/day represents "
            f"crop evapotranspiration drawn from the soil reservoir, NOT a daily pumping target."
        )
    else:
        warning_alert = (
            f"Note: Water should be applied in scheduled cycles ({interval_display}), "
            f"not continuously. The daily figure represents field moisture depletion."
        )

    return {
        "irrigation_regime": archetype["category_title"],
        "event_gross_depth_mm": event_gross_depth_mm,
        "event_net_depth_mm": event_net_depth_mm,
        "event_volume_litres": event_volume_litres,
        "irrigation_interval_days": interval_days,
        "irrigation_interval_display": interval_display,
        "pump_hp": hp,
        "pump_hours_per_event": pump_hours,
        "pump_shift_display": pump_shift_display,
        "shift_guidance": shift_guidance,
        "seasonal_irrigations_summary": seasonal_summary,
        "stage_criticality": criticality,
        "soil_type": soil_clean.title(),
        "available_water_capacity_mm_m": soil_awc,
        "root_depth_meters": root_depth_m,
        "farmer_practical_guideline": farmer_guideline,
        "danger_warning": warning_alert,
        "daily_consumption_clarification": (
            f"Daily field moisture loss is {round(daily_gross_mm * area * 10000):,} Litres/day. "
            f"Real farmers replenish this in scheduled cycles of {event_volume_litres:,} Litres "
            f"({interval_display})."
        )
    }
