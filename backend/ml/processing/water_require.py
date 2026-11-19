import pandas as pd
from pathlib import Path

from backend.ml.processing.farmer_water_usage import (
    calculate_farmer_water_plan
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

PARAMETER_FILE = (
    BASE_DIR / "datasets" / "processed" / "crop_water_parameters.csv"
)


# ============================================================
# LOAD CROP PARAMETERS
# ============================================================

def load_crop_parameters():
    """
    Load the 55 supported crop water parameters.
    """

    if not PARAMETER_FILE.exists():
        raise FileNotFoundError(
            f"Crop parameter file not found: {PARAMETER_FILE}"
        )

    df = pd.read_csv(PARAMETER_FILE)

    required_columns = [
        "Crop",
        "Crop_Group",
        "Kc_Initial",
        "Kc_Development",
        "Kc_Mid",
        "Kc_Late",
        "Water_Need_Min_mm",
        "Water_Need_Max_mm",
        "Reference_Source",
        "Parameter_Status"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns in crop parameter file: {missing}"
        )

    return df


# ============================================================
# CROP ALIAS NORMALIZATION
# ============================================================

CROP_ALIASES = {
    # Paddy / Rice
    "rice": "Paddy",
    "rice paddy": "Paddy",
    "paddy (rice)": "Paddy",
    "paddy": "Paddy",
    "dhan": "Paddy",

    # Mirchi / Chilli / Red Chillies
    "dry chillies": "Mirchi",
    "dry chilli": "Mirchi",
    "red chillies": "Mirchi",
    "red chilli": "Mirchi",
    "chilli": "Mirchi",
    "chillies": "Mirchi",
    "mirchi": "Mirchi",
    "pepper": "Mirchi",
    "lal mirch": "Mirchi",
    "green chilli": "Mirchi",
    "mirchi (chilli)": "Mirchi",
    "mirchi (red chilli)": "Mirchi",

    # Gram / Chana
    "gram": "Gram (Chana)",
    "chana": "Gram (Chana)",
    "chickpea": "Gram (Chana)",
    "bengal gram": "Gram (Chana)",
    "gram (chana)": "Gram (Chana)",
    "gram / chana": "Gram (Chana)",

    # Cotton
    "cotton": "Cotton",
    "cotton(lint)": "Cotton",
    "cotton (lint)": "Cotton",
    "cotton (kapas)": "Cotton",
    "kapas": "Cotton",

    # Mustard
    "mustard": "Mustard",
    "rapeseed &mustard": "Mustard",
    "rapeseed & mustard": "Mustard",
    "mustard / rapeseed": "Mustard",
    "sarson": "Mustard",
    "rai": "Mustard",

    # Pulses
    "arhar": "Arhar/Tur",
    "tur": "Arhar/Tur",
    "toor": "Arhar/Tur",
    "toor dal": "Arhar/Tur",
    "pigeon pea": "Arhar/Tur",
    "red gram": "Arhar/Tur",
    "arhar/tur": "Arhar/Tur",
    "arhar / tur": "Arhar/Tur",
    "moong": "Moong (Green Gram)",
    "green gram": "Moong (Green Gram)",
    "moong(green gram)": "Moong (Green Gram)",
    "moong (green gram)": "Moong (Green Gram)",
    "urad": "Urad",
    "black gram": "Urad",
    "lobia": "Cowpea(Lobia)",
    "cowpea": "Cowpea(Lobia)",
    "cowpea(lobia)": "Cowpea(Lobia)",
    "cowpea (lobia)": "Cowpea(Lobia)",
    "kulthi": "Horse-gram",
    "horse gram": "Horse-gram",
    "horse-gram": "Horse-gram",

    # Oilseeds
    "peanut": "Groundnut",
    "mungfali": "Groundnut",
    "groundnut": "Groundnut",
    "til": "Sesamum",
    "sesame": "Sesamum",
    "sesamum": "Sesamum",
    "soybean": "Soyabean",
    "soyabean": "Soyabean",
    "flaxseed": "Linseed",
    "alsi": "Linseed",
    "linseed": "Linseed",
    "other oilseeds": "Other Oilseeds",

    # Cereals
    "gehun": "Wheat",
    "wheat": "Wheat",
    "corn": "Maize",
    "makka": "Maize",
    "maize": "Maize",
    "jowar": "Jowar",
    "sorghum": "Jowar",
    "bajra": "Bajra",
    "pearl millet": "Bajra",
    "ragi": "Ragi",
    "finger millet": "Ragi",

    # Cash / Vegetables
    "ganna": "Sugarcane",
    "sugarcane": "Sugarcane",
    "aloo": "Potato",
    "potato": "Potato",
    "pyaz": "Onion",
    "onion": "Onion",
    "lahsun": "Garlic",
    "garlic": "Garlic",
    "adrak": "Ginger",
    "ginger": "Ginger",
    "haldi": "Turmeric",
    "turmeric": "Turmeric",
    "dhaniya": "Coriander",
    "coriander": "Coriander"
}


def normalize_crop_name(crop, parameters_df):
    """
    Resolve crop name across regional farmer aliases and canonical dataset names.
    Supports Mirchi, Red Chillies, Dry chillies, Paddy, Rice, Chana, etc.
    """
    c = str(crop).strip()
    c_lower = c.lower()
    supported = parameters_df["Crop"].tolist()

    # 1. Exact case-insensitive match in dataset
    for s in supported:
        if s.lower() == c_lower:
            return s

    # 2. Known alias dictionary lookup
    if c_lower in CROP_ALIASES:
        canonical = CROP_ALIASES[c_lower]
        for s in supported:
            if s.lower() == canonical.lower():
                return s

    # 3. Substring match
    for s in supported:
        if s.lower() in c_lower or c_lower in s.lower():
            return s

    return c


# ============================================================
# GROWTH-STAGE → Kc
# ============================================================

def get_kc(crop_row, growth_stage):
    """
    Select crop coefficient (Kc) according to growth stage.
    """

    stage = str(growth_stage).strip().lower()

    stage_mapping = {
        "sowing": "Kc_Initial",
        "initial": "Kc_Initial",

        "vegetative": "Kc_Development",
        "development": "Kc_Development",

        "flowering": "Kc_Mid",
        "mid": "Kc_Mid",

        "harvest": "Kc_Late",
        "late": "Kc_Late"
    }

    column = stage_mapping.get(stage)

    if column is None:
        raise ValueError(
            f"Unsupported growth stage: {growth_stage}"
        )

    return float(crop_row[column])


# ============================================================
# MAIN WATER REQUIREMENT CALCULATION
# ============================================================

def calculate_water_requirement(
    crop,
    growth_stage,
    field_area_hectare,
    eto_mm_day,
    rainfall_mm=0,
    irrigation_efficiency=0.80,
    irrigation_method="Sprinkler",
    soil_type="Loamy",
    pump_hp=5.0
):
    """
    Calculate crop water and irrigation requirement based on FAO-56
    and real-time farmer operational field practices.
    """

    # --------------------------------------------------------
    # Validate inputs
    # --------------------------------------------------------

    if field_area_hectare <= 0:
        raise ValueError(
            "Field area must be greater than zero."
        )

    if eto_mm_day < 0:
        raise ValueError(
            "ETo cannot be negative."
        )

    if rainfall_mm < 0:
        raise ValueError(
            "Rainfall cannot be negative."
        )

    if not 0 < irrigation_efficiency <= 1:
        raise ValueError(
            "Irrigation efficiency must be between 0 and 1."
        )

    # --------------------------------------------------------
    # Load parameters
    # --------------------------------------------------------

    parameters = load_crop_parameters()
    resolved_crop = normalize_crop_name(crop, parameters)

    crop_match = parameters[
        parameters["Crop"].str.strip().str.lower()
        == resolved_crop.strip().lower()
    ]

    if crop_match.empty:
        supported = sorted(parameters["Crop"].tolist())

        raise ValueError(
            f"Unsupported crop: {crop}. "
            f"Supported crops: {supported}"
        )

    crop_row = crop_match.iloc[0]

    # --------------------------------------------------------
    # Crop coefficient
    # --------------------------------------------------------

    kc = get_kc(
        crop_row,
        growth_stage
    )

    # --------------------------------------------------------
    # Crop evapotranspiration
    #
    # FAO relationship:
    # ETc = ETo × Kc
    # --------------------------------------------------------

    crop_water_requirement_mm = eto_mm_day * kc

    # --------------------------------------------------------
    # Effective rainfall
    #
    # Simple conservative assumption for this initial engine.
    # This can later be replaced by a proper effective-rainfall
    # calculation using the weather/CROPWAT layer.
    # --------------------------------------------------------

    effective_rainfall_mm = min(
        rainfall_mm,
        crop_water_requirement_mm
    )

    # --------------------------------------------------------
    # Net irrigation requirement
    # --------------------------------------------------------

    net_irrigation_requirement_mm = max(
        crop_water_requirement_mm
        - effective_rainfall_mm,
        0
    )

    # --------------------------------------------------------
    # Gross irrigation requirement
    #
    # Gross = Net / irrigation efficiency
    # --------------------------------------------------------

    gross_irrigation_requirement_mm = (
        net_irrigation_requirement_mm
        / irrigation_efficiency
    )

    # --------------------------------------------------------
    # Convert mm to litres
    #
    # 1 mm over 1 hectare = 10,000 litres
    # --------------------------------------------------------

    crop_water_litres = (
        crop_water_requirement_mm
        * field_area_hectare
        * 10000
    )

    net_irrigation_litres = (
        net_irrigation_requirement_mm
        * field_area_hectare
        * 10000
    )

    gross_irrigation_litres = (
        gross_irrigation_requirement_mm
        * field_area_hectare
        * 10000
    )

    # --------------------------------------------------------
    # Reference seasonal range
    # --------------------------------------------------------

    min_water = crop_row["Water_Need_Min_mm"]
    max_water = crop_row["Water_Need_Max_mm"]

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = {
        "crop": crop_row["Crop"],
        "crop_group": crop_row["Crop_Group"],
        "growth_stage": growth_stage,

        "kc": round(kc, 3),

        "eto_mm_day": round(eto_mm_day, 3),

        "crop_water_requirement_mm": round(
            crop_water_requirement_mm,
            3
        ),

        "effective_rainfall_mm": round(
            effective_rainfall_mm,
            3
        ),

        "net_irrigation_requirement_mm": round(
            net_irrigation_requirement_mm,
            3
        ),

        "gross_irrigation_requirement_mm": round(
            gross_irrigation_requirement_mm,
            3
        ),

        "field_area_hectare": round(
            field_area_hectare,
            3
        ),

        "crop_water_requirement_litres": round(
            crop_water_litres,
            2
        ),

        "net_irrigation_litres": round(
            net_irrigation_litres,
            2
        ),

        "gross_irrigation_litres": round(
            gross_irrigation_litres,
            2
        ),

        "reference_water_min_mm": (
            None if pd.isna(min_water)
            else float(min_water)
        ),

        "reference_water_max_mm": (
            None if pd.isna(max_water)
            else float(max_water)
        ),

        "parameter_status": crop_row[
            "Parameter_Status"
        ],

        "reference_source": crop_row[
            "Reference_Source"
        ]
    }

    # --------------------------------------------------------
    # Real-Time Farmer Practical Water Usage & Schedule
    # --------------------------------------------------------
    farmer_plan = calculate_farmer_water_plan(
        crop=crop_row["Crop"],
        growth_stage=growth_stage,
        field_area_hectare=field_area_hectare,
        daily_net_etc_mm=net_irrigation_requirement_mm,
        daily_gross_mm=gross_irrigation_requirement_mm,
        irrigation_method=irrigation_method,
        irrigation_efficiency=irrigation_efficiency,
        soil_type=soil_type,
        pump_hp=pump_hp
    )

    result["farmer_usage"] = farmer_plan
    result["irrigation_interval_days"] = farmer_plan["irrigation_interval_days"]
    result["irrigation_interval_display"] = farmer_plan["irrigation_interval_display"]
    result["event_volume_litres"] = farmer_plan["event_volume_litres"]
    result["event_gross_depth_mm"] = farmer_plan["event_gross_depth_mm"]
    result["pump_hours_per_event"] = farmer_plan["pump_hours_per_event"]
    result["pump_shift_display"] = farmer_plan.get("pump_shift_display", f"~{farmer_plan['pump_hours_per_event']} Hours")
    result["shift_guidance"] = farmer_plan.get("shift_guidance", "")
    result["seasonal_irrigations_summary"] = farmer_plan["seasonal_irrigations_summary"]
    result["stage_criticality"] = farmer_plan["stage_criticality"]
    result["farmer_practical_guideline"] = farmer_plan["farmer_practical_guideline"]
    result["danger_warning"] = farmer_plan["danger_warning"]
    result["daily_consumption_clarification"] = farmer_plan["daily_consumption_clarification"]

    return result


# ============================================================
# TEST ALL 55 CROPS
# ============================================================

def test_all_crops():
    """
    Verify that every crop in the parameter file
    can be processed successfully.
    """

    parameters = load_crop_parameters()

    stages = [
        "Sowing",
        "Vegetative",
        "Flowering",
        "Harvest"
    ]

    successful = 0
    failed = []

    for crop in parameters["Crop"]:

        try:

            for stage in stages:

                calculate_water_requirement(
                    crop=crop,
                    growth_stage=stage,
                    field_area_hectare=1,
                    eto_mm_day=5,
                    rainfall_mm=0,
                    irrigation_efficiency=0.80
                )

            successful += 1

        except Exception as e:

            failed.append(
                {
                    "crop": crop,
                    "error": str(e)
                }
            )

    print("\n" + "=" * 60)
    print("55-CROP WATER REQUIREMENT TEST")
    print("=" * 60)

    print(f"Total crops : {len(parameters)}")
    print(f"Successful  : {successful}")
    print(f"Failed      : {len(failed)}")

    if failed:

        print("\nFAILED CROPS:")

        for item in failed:
            print(
                f"- {item['crop']}: {item['error']}"
            )

    else:

        print("\nALL 55 CROPS PASSED.")

    print("=" * 60)

if __name__ == "__main__":

    # --------------------------------------------------------
    # Test all 55 crops
    # --------------------------------------------------------

    test_all_crops()

    # --------------------------------------------------------
    # Generate example calculations for ALL 55 crops
    # --------------------------------------------------------

    parameters = load_crop_parameters()

    all_results = []

    for crop in parameters["Crop"]:

        result = calculate_water_requirement(
            crop=crop,
            growth_stage="Vegetative",
            field_area_hectare=1,
            eto_mm_day=5,
            rainfall_mm=0,
            irrigation_efficiency=0.80
        )

        all_results.append(result)

    # --------------------------------------------------------
    # Convert results to DataFrame
    # --------------------------------------------------------

    results_df = pd.DataFrame(all_results)

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    output_file = (
        BASE_DIR
        / "datasets"
        / "processed"
        / "55_crop_water_examples.csv"
    )

    results_df.to_csv(
        output_file,
        index=False
    )

    # --------------------------------------------------------
    # Display summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("55-CROP WATER CALCULATION")
    print("=" * 60)

    print(
        f"Generated calculations for "
        f"{len(results_df)} crops."
    )

    print(f"Output file: {output_file}")

    print("=" * 60)

    print("\nSAMPLE RESULTS:")

    print(
        results_df[
            [
                "crop",
                "growth_stage",
                "kc",
                "crop_water_requirement_mm",
                "crop_water_requirement_litres"
            ]
        ].to_string(index=False)
    )