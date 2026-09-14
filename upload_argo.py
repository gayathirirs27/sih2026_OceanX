import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CSV_FILE = "data/processed/argo/argo_bob_20250101_20250630_clean.csv"

df = pd.read_csv(CSV_FILE)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# --------------------------------------------------
# 1. Clear existing Argo data
# --------------------------------------------------

cur.execute("DELETE FROM argo_observations;")
cur.execute("DELETE FROM argo_platforms;")

print("🗑️ Existing Argo data cleared.")

# --------------------------------------------------
# 2. Insert Argo platforms
# --------------------------------------------------

platforms = (
    df.groupby("PLATFORM_NUMBER")
    .agg(
        latitude=("latitude", "last"),
        longitude=("longitude", "last"),
        last_seen=("time", "max")
    )
    .reset_index()
)

for _, row in platforms.iterrows():

    cur.execute(
        """
        INSERT INTO argo_platforms
        (
            platform_id,
            platform_type,
            latitude,
            longitude,
            last_seen
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            str(int(row["PLATFORM_NUMBER"])),
            "Argo Float",
            row["latitude"],
            row["longitude"],
            row["last_seen"]
        )
    )

print(f"🌊 Uploaded {len(platforms)} Argo platforms.")

# --------------------------------------------------
# 3. Insert Argo observations
# --------------------------------------------------

for _, row in df.iterrows():

    cur.execute(
        """
        INSERT INTO argo_observations
        (
            platform_id,
            cycle_number,
            observation_time,
            latitude,
            longitude,
            depth,
            temperature,
            salinity,
            temperature_qc,
            salinity_qc
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            str(int(row["PLATFORM_NUMBER"])),
            int(row["CYCLE_NUMBER"]),
            row["time"],
            row["latitude"],
            row["longitude"],
            row["PRES"],
            row["TEMP"],
            row["PSAL"],
            str(int(row["TEMP_QC"])),
            str(int(row["PSAL_QC"]))
        )
    )

conn.commit()

print(f"✅ Uploaded {len(df)} Argo observations.")

cur.close()
conn.close()

print("🎉 Argo database update completed successfully.")