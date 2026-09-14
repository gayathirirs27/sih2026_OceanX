import pandas as pd
from pathlib import Path


# --------------------------------------------------
# Paths
# --------------------------------------------------

INPUT_FILE = Path("data/raw/glider/glider raw.csv")

OUTPUT_DIR = Path("data/processed/glider")
OUTPUT_FILE = OUTPUT_DIR / "glider_bob_20160701_20160714_clean.csv"


# --------------------------------------------------
# Working time window
# July 1, 2016 through July 14, 2016 inclusive
# --------------------------------------------------

START_TIME = pd.Timestamp("2016-07-01 00:00:00", tz="UTC")
END_TIME = pd.Timestamp("2016-07-15 00:00:00", tz="UTC")


# --------------------------------------------------
# Load raw CSV
# --------------------------------------------------

print("Loading raw glider data...")

df = pd.read_csv(
    INPUT_FILE,
    skiprows=[1],       # Skip the units row
    low_memory=False
)

print(f"Raw rows loaded: {len(df):,}")


# --------------------------------------------------
# Standardize column names
# --------------------------------------------------

df.columns = [col.strip() for col in df.columns]

print("\nColumns found:")
print(df.columns.tolist())


# --------------------------------------------------
# Convert numeric columns
# --------------------------------------------------

numeric_columns = [
    "latitude",
    "longitude",
    "PSAL",
    "TEMP",
    "PRES",
    "JULD"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")


# --------------------------------------------------
# Parse observation time
# --------------------------------------------------

df["time"] = pd.to_datetime(
    df["time"],
    errors="coerce",
    utc=True
)


# --------------------------------------------------
# Remove rows missing essential fields
# --------------------------------------------------

before = len(df)

df = df.dropna(
    subset=[
        "platform_deployment",
        "time",
        "latitude",
        "longitude",
        "PRES",
        "TEMP"
    ]
)

print(
    f"Removed rows missing essential fields: "
    f"{before - len(df):,}"
)


# --------------------------------------------------
# Filter geographic validity
# --------------------------------------------------

before = len(df)

df = df[
    (df["latitude"] >= -90) &
    (df["latitude"] <= 90) &
    (df["longitude"] >= -180) &
    (df["longitude"] <= 180)
]

print(
    f"Removed invalid latitude/longitude rows: "
    f"{before - len(df):,}"
)


# --------------------------------------------------
# Remove invalid pressure/depth values
# --------------------------------------------------

before = len(df)

df = df[df["PRES"] >= 0]

print(
    f"Removed negative pressure rows: "
    f"{before - len(df):,}"
)


# --------------------------------------------------
# Filter requested time period
# --------------------------------------------------

before = len(df)

df = df[
    (df["time"] >= START_TIME) &
    (df["time"] < END_TIME)
]

print(
    f"Removed rows outside July 1-14, 2016: "
    f"{before - len(df):,}"
)


# --------------------------------------------------
# Sort observations
# --------------------------------------------------

df = df.sort_values(
    by=["platform_deployment", "time"]
).reset_index(drop=True)


# --------------------------------------------------
# Save cleaned dataset
# --------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# --------------------------------------------------
# Verification
# --------------------------------------------------

print("\n" + "=" * 60)
print("GLIDER DATA CLEANING COMPLETE")
print("=" * 60)

print(f"\nOutput file:")
print(OUTPUT_FILE)

print(f"\nClean rows: {len(df):,}")

print("\nPlatforms:")
print(
    df["platform_deployment"]
    .value_counts()
    .sort_index()
)

print("\nDate range:")
print("First:", df["time"].min())
print("Last: ", df["time"].max())

print("\nGeographic bounds:")
print("Latitude :", df["latitude"].min(), "to", df["latitude"].max())
print("Longitude:", df["longitude"].min(), "to", df["longitude"].max())

print("\nPressure/depth range:")
print("PRES:", df["PRES"].min(), "to", df["PRES"].max())

print("\nMissing values:")
print(
    df[
        ["latitude", "longitude", "PRES", "TEMP", "PSAL"]
    ].isna().sum()
)

print("\nSalinity availability by platform:")

for platform, group in df.groupby("platform_deployment"):
    print(
        f"{platform}: "
        f"{group['PSAL'].notna().sum():,} salinity values / "
        f"{len(group):,} rows"
    )