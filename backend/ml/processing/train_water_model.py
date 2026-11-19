import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from sklearn.impute import SimpleImputer

from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor

from xgboost import XGBRegressor

from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score


# ============================================================
# 1. FILE PATHS
# ============================================================

DATA_FILE = (
    "backend/datasets/processed/water_training.csv"
)

MODEL_DIR = "backend/ml/models"

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# 2. LOAD DATA
# ============================================================

df = pd.read_csv(DATA_FILE)

print("\n====================================")
print("WATER MODEL TRAINING")
print("====================================")

print("Dataset shape:", df.shape)


# ============================================================
# 3. DEFINE TARGET
# ============================================================

TARGET = "reference_water_requirement_mm"


# ============================================================
# 4. DEFINE FEATURES
# ============================================================

features = [
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


X = df[features]
y = df[TARGET]


# ============================================================
# 5. IDENTIFY DATA TYPES
# ============================================================

categorical_features = X.select_dtypes(
    include=["object"]
).columns.tolist()

numeric_features = X.select_dtypes(
    exclude=["object"]
).columns.tolist()


print("\nNumerical features:")
print(numeric_features)

print("\nCategorical features:")
print(categorical_features)


# ============================================================
# 6. PREPROCESSING
# ============================================================

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        )
    ]
)


categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="most_frequent")
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ]
)


preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_features
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    ]
)


# ============================================================
# 7. TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


print("\n====================================")
print("TRAIN TEST SPLIT")
print("====================================")

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# ============================================================
# 8. MODELS
# ============================================================

models = {

    "Linear Regression":
        LinearRegression(),

    "Decision Tree":
        DecisionTreeRegressor(
            random_state=42,
            max_depth=10
        ),

    "Random Forest":
        RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1
        ),

    "XGBoost":
        XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            objective="reg:squarederror",
            n_jobs=-1
        )
}


# ============================================================
# 9. TRAIN AND EVALUATE
# ============================================================

results = []

trained_models = {}


for model_name, model in models.items():

    print("\n------------------------------------")
    print("Training:", model_name)
    print("------------------------------------")

    pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor
            ),
            (
                "model",
                model
            )
        ]
    )

    pipeline.fit(
        X_train,
        y_train
    )

    predictions = pipeline.predict(
        X_test
    )

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

    print("MAE :", round(mae, 3))
    print("RMSE:", round(rmse, 3))
    print("R2  :", round(r2, 4))

    results.append(
        {
            "Model": model_name,
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2
        }
    )

    trained_models[model_name] = pipeline


# ============================================================
# 10. RESULTS TABLE
# ============================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="RMSE"
)


print("\n====================================")
print("MODEL COMPARISON")
print("====================================")

print(
    results_df.to_string(index=False)
)


# ============================================================
# 11. SELECT BEST MODEL
# ============================================================

best_model_name = results_df.iloc[0]["Model"]

best_model = trained_models[
    best_model_name
]


print("\n====================================")
print("BEST MODEL")
print("====================================")

print(
    "Best model:",
    best_model_name
)


# ============================================================
# 12. SAVE BEST MODEL
# ============================================================

model_path = (
    f"{MODEL_DIR}/water_model.pkl"
)

joblib.dump(
    best_model,
    model_path
)


# ============================================================
# 13. SAVE MODEL RESULTS
# ============================================================

results_path = (
    "backend/datasets/processed/"
    "water_model_results.csv"
)

results_df.to_csv(
    results_path,
    index=False
)


print("\n====================================")
print("FILES SAVED")
print("====================================")

print(
    "Model:",
    model_path
)

print(
    "Results:",
    results_path
)

print("\n====================================")
print("WATER MODEL TRAINING COMPLETE")
print("====================================")