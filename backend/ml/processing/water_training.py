import pandas as pd

FILE = "backend/datasets/processed/water_training.csv"

df = pd.read_csv(FILE)

print("\n====================================")
print("WATER TRAINING DATASET CHECK")
print("====================================")

print("Shape:", df.shape)

print("\nColumns:")
for column in df.columns:
    print(column)

print("\nMissing values:")
print(df.isnull().sum())

print("\nWater requirement in mm:")
print(df["reference_water_requirement_mm"].describe())

print("\nWater requirement in litres:")
print(df["water_requirement_liters"].describe())

print("\nCrop distribution:")
print(df["Crop_Type"].value_counts())

print("\nIrrigation type distribution:")
print(df["Irrigation_Type"].value_counts())

print("\nSample records:")
print(df.head(10).to_string(index=False))

print("\n====================================")
print("CHECK COMPLETE")
print("====================================")