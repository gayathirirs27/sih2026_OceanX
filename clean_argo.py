import pandas as pd

input_file = "data/raw/argo/argo_bob_20250101_20250630.csv"
output_file = "data/processed/argo/argo_bob_20250101_20250630_clean.csv"
# Read the raw Argo CSV
df = pd.read_csv(input_file, skiprows=[1])

print("Raw rows:", len(df))

# Convert numeric columns
numeric_columns = [
    "PLATFORM_NUMBER",
    "CYCLE_NUMBER",
    "latitude",
    "longitude",
    "PRES",
    "TEMP",
    "PSAL",
    "TEMP_QC",
    "PSAL_QC"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove rows missing essential information
df = df.dropna(
    subset=[
        "PLATFORM_NUMBER",
        "time",
        "latitude",
        "longitude",
        "PRES",
        "TEMP",
        "PSAL"
    ]
)

# Keep good-quality temperature and salinity observations
df = df[
    (df["TEMP_QC"] == 1) &
    (df["PSAL_QC"] == 1)
]

# Convert time to standard datetime
df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)

# Remove rows where time conversion failed
df = df.dropna(subset=["time"])

# Save cleaned data
df.to_csv(output_file, index=False)

print("Clean rows:", len(df))
print("Unique floats:", df["PLATFORM_NUMBER"].nunique())
print("Saved to:", output_file)