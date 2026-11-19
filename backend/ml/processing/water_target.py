import pandas as pd
import re


# ==========================================
# FILE PATHS
# ==========================================

IRRIGATION_FILE = (
    "backend/datasets/processed/irrigation_clean.csv"
)

WATER_REFERENCE_FILE = (
    "backend/datasets/raw/india_crop_water_requirement.xlsx"
)

OUTPUT_FILE = (
    "backend/datasets/processed/water_training.csv"
)


# ==========================================
# LOAD DATA
# ==========================================

irrigation_df = pd.read_csv(IRRIGATION_FILE)

water_ref_df = pd.read_excel(WATER_REFERENCE_FILE)


# ==========================================
# CLEAN TEXT
# ==========================================

for column in irrigation_df.select_dtypes(include="object").columns:
    irrigation_df[column] = (
        irrigation_df[column]
        .astype(str)
        .str.strip()
    )

for column in water_ref_df.select_dtypes(include="object").columns:
    water_ref_df[column] = (
        water_ref_df[column]
        .astype(str)
        .str.strip()
    )


# ==========================================
# CONVERT WATER RANGE TO MIDPOINT
# ==========================================

def range_to_midpoint(value):

    value = str(value).strip()

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value
    )

    if len(numbers) >= 2:

        lower = float(numbers[0])
        upper = float(numbers[1])

        return (lower + upper) / 2

    elif len(numbers) == 1:

        return float(numbers[0])

    return None


water_ref_df[
    "Reference_Water_Requirement_mm"
] = water_ref_df[
    "Total Crop Water Requirement (mm)"
].apply(range_to_midpoint)


# ==========================================
# PREPARE CROP/METHOD MAPPING
# ==========================================

def normalize_crop(crop):

    crop = crop.lower().strip()

    if "maize" in crop:
        return "Maize"

    if "wheat" in crop:
        return "Wheat"

    if "rice" in crop:
        return "Rice"

    if "groundnut" in crop:
        return "Groundnut"

    if "mustard" in crop:
        return "Mustard"

    if "moong" in crop:
        return "Moong Bean"

    if "green pea" in crop:
        return "Green Pea"

    if "okra" in crop:
        return "Okra"

    if "cowpea" in crop:
        return "Cowpea"

    if "onion" in crop:
        return "Onion"

    if "potato" in crop:
        return "Potato"

    if "broccoli" in crop:
        return "Broccoli"

    if "red pepper" in crop:
        return "Red Pepper"

    return None


water_ref_df["Crop_Normalized"] = (
    water_ref_df["Crop"]
    .apply(normalize_crop)
)


# ==========================================
# NORMALIZE IRRIGATION METHOD
# ==========================================

def normalize_method(method):

    method = method.lower().strip()

    if "drip" in method:
        return "Drip"

    if "surface" in method:
        return "Surface"

    return None


water_ref_df["Method_Normalized"] = (
    water_ref_df["Irrigation Method"]
    .apply(normalize_method)
)


# ==========================================
# MATCH PROJECT CROPS
# ==========================================

reference_rows = water_ref_df[
    water_ref_df["Crop_Normalized"].isin(
        irrigation_df["Crop_Type"].unique()
    )
].copy()


print("\n====================================")
print("REFERENCE MATCHING")
print("====================================")

print(
    "Reference rows available:",
    len(reference_rows)
)

print(
    reference_rows[
        [
            "Crop",
            "Irrigation Method",
            "Reference_Water_Requirement_mm"
        ]
    ].to_string(index=False)
)


# ==========================================
# CROP + IRRIGATION METHOD LOOKUP
# ==========================================

reference_lookup = {}

for _, row in reference_rows.iterrows():

    crop = row["Crop_Normalized"]
    method = row["Method_Normalized"]

    if crop is None or method is None:
        continue

    reference_lookup[
        (crop, method)
    ] = row[
        "Reference_Water_Requirement_mm"
    ]


# ==========================================
# GENERATE BASE WATER TARGET
# ==========================================

def get_reference_water(row):

    crop = row["Crop_Type"]
    irrigation_type = row["Irrigation_Type"]

    # Drip has direct reference values
    if irrigation_type == "Drip":

        return reference_lookup.get(
            (crop, "Drip")
        )

    # Canal/Sprinkler/Rainfed do not always
    # have a direct matching reference.
    if irrigation_type == "Canal":

        return reference_lookup.get(
            (crop, "Surface")
        )

    if irrigation_type == "Sprinkler":

        return reference_lookup.get(
            (crop, "Surface")
        )

    return None


irrigation_df[
    "reference_water_requirement_mm"
] = irrigation_df.apply(
    get_reference_water,
    axis=1
)


# ==========================================
# CHECK MATCHING
# ==========================================

matched = (
    irrigation_df[
        "reference_water_requirement_mm"
    ].notna()
)

print("\n====================================")
print("TARGET MATCHING")
print("====================================")

print(
    "Matched records:",
    matched.sum()
)

print(
    "Unmatched records:",
    (~matched).sum()
)


# ==========================================
# KEEP MATCHED RECORDS
# ==========================================

water_training_df = irrigation_df[
    matched
].copy()


# ==========================================
# CONVERT MM TO LITRES
# ==========================================

# 1 hectare = 10,000 square metres
# 1 mm over 1 square metre = 1 litre
#
# Therefore:
#
# Litres = mm × hectares × 10,000

water_training_df[
    "water_requirement_liters"
] = (
    water_training_df[
        "reference_water_requirement_mm"
    ]
    *
    water_training_df[
        "Field_Area_hectare"
    ]
    *
    10000
)


# ==========================================
# SAVE DATASET
# ==========================================

water_training_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==========================================
# SUMMARY
# ==========================================

print("\n====================================")
print("WATER TRAINING DATASET CREATED")
print("====================================")

print(
    "Rows:",
    len(water_training_df)
)

print(
    "Columns:",
    len(water_training_df.columns)
)

print("\nWater requirement in mm:")

print(
    water_training_df[
        "reference_water_requirement_mm"
    ].describe()
)

print("\nWater requirement in litres:")

print(
    water_training_df[
        "water_requirement_liters"
    ].describe()
)

print("\nSaved to:")

print(OUTPUT_FILE)