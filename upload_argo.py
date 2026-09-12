import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CSV_FILE = "data/processed/argo/argo_bob_20250101_20250107_clean.csv"

df = pd.read_csv(CSV_FILE)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

for _, row in df.iterrows():
    cur.execute("""
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
    """, (
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
    ))

conn.commit()

print(f"✅ Uploaded {len(df)} Argo observations.")

cur.close()
conn.close()