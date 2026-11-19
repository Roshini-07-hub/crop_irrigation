import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


# ============================================================
# 1. FILE PATHS
# ============================================================

DATA_FILE = (
    "backend/datasets/processed/water_training.csv"
)

MODEL_FILE = (
    "backend/ml/models/water_model.pkl"
)

OUTPUT_DIR = (
    "backend/reports/model_results"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. LOAD DATA AND MODEL
# ============================================================

df = pd.read_csv(DATA_FILE)

model = joblib.load(MODEL_FILE)


# ============================================================
# 3. FEATURES AND TARGET
# ============================================================

TARGET = "reference_water_requirement_mm"

FEATURES = [
    "Soil_Type",
    "Soil_pH",
    "Soil_Moisture",
    "Organic_Carbon",
    "Electrical_Conductivity",
    "Temperature_C",
    "Humidity",
    "Rainfall_mm",
    "Sunlight_Hours",
    "Wind_Speed_kmh",
    "Crop_Type",
    "Crop_Growth_Stage",
    "Season",
    "Irrigation_Type",
    "Water_Source",
    "Field_Area_hectare",
    "Mulching_Used",
    "Previous_Irrigation_mm",
    "Region",
    "Irrigation_Need"
]


X = df[FEATURES]
y = df[TARGET]


# ============================================================
# 4. SAME 80/20 SPLIT USED DURING TRAINING
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


# ============================================================
# 5. PREDICTIONS
# ============================================================

predictions = model.predict(X_test)


# ============================================================
# 6. METRICS
# ============================================================

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5

r2 = r2_score(
    y_test,
    predictions
)


# ============================================================
# 7. PRINT RESULTS
# ============================================================

print("\n====================================")
print("WATER MODEL EVALUATION")
print("====================================")

print("Test records:", len(X_test))

print("\nEvaluation Metrics:")

print(
    "MAE :",
    round(mae, 3),
    "mm"
)

print(
    "RMSE:",
    round(rmse, 3),
    "mm"
)

print(
    "R2  :",
    round(r2, 4)
)


# ============================================================
# 8. CREATE PREDICTION TABLE
# ============================================================

evaluation_df = X_test.copy()

evaluation_df[
    "actual_water_requirement_mm"
] = y_test.values

evaluation_df[
    "predicted_water_requirement_mm"
] = predictions

evaluation_df[
    "absolute_error_mm"
] = (
    evaluation_df[
        "actual_water_requirement_mm"
    ]
    -
    evaluation_df[
        "predicted_water_requirement_mm"
    ]
).abs()


# ============================================================
# 9. CONVERT PREDICTION TO LITRES
# ============================================================

evaluation_df[
    "predicted_water_requirement_liters"
] = (
    evaluation_df[
        "predicted_water_requirement_mm"
    ]
    *
    evaluation_df[
        "Field_Area_hectare"
    ]
    *
    10000
)


# ============================================================
# 10. SAVE PREDICTIONS
# ============================================================

prediction_file = (
    f"{OUTPUT_DIR}/water_predictions.csv"
)

evaluation_df.to_csv(
    prediction_file,
    index=False
)


# ============================================================
# 11. SAVE METRICS
# ============================================================

metrics_df = pd.DataFrame(
    [
        {
            "Model": "Best Water Model",
            "MAE_mm": mae,
            "RMSE_mm": rmse,
            "R2": r2
        }
    ]
)

metrics_file = (
    f"{OUTPUT_DIR}/water_evaluation_metrics.csv"
)

metrics_df.to_csv(
    metrics_file,
    index=False
)


# ============================================================
# 12. DISPLAY SAMPLE PREDICTIONS
# ============================================================

print("\n====================================")
print("SAMPLE PREDICTIONS")
print("====================================")

print(
    evaluation_df[
        [
            "Crop_Type",
            "Irrigation_Type",
            "Field_Area_hectare",
            "actual_water_requirement_mm",
            "predicted_water_requirement_mm",
            "predicted_water_requirement_liters",
            "absolute_error_mm"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 13. FILES SAVED
# ============================================================

print("\n====================================")
print("EVALUATION FILES SAVED")
print("====================================")

print(
    "Predictions:",
    prediction_file
)

print(
    "Metrics:",
    metrics_file
)

print("\n====================================")
print("EVALUATION COMPLETE")
print("====================================")