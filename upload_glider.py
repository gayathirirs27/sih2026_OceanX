import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# File
# --------------------------------------------------

CSV_FILE = (
    "data/processed/glider/"
    "glider_bob_20160701_20160714_clean.csv"
)


# --------------------------------------------------
# Load cleaned Glider data
# --------------------------------------------------

print("Loading cleaned Glider data...")

df = pd.read_csv(
    CSV_FILE,
    low_memory=False
)

print(f"Loaded {len(df):,} Glider observations.")


# --------------------------------------------------
# Prepare data
# --------------------------------------------------

df["time"] = pd.to_datetime(
    df["time"],
    errors="coerce",
    utc=True
)

numeric_columns = [
    "latitude",
    "longitude",
    "PRES",
    "TEMP",
    "PSAL"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# --------------------------------------------------
# Connect to Supabase PostgreSQL
# --------------------------------------------------

print("Connecting to Supabase...")

conn = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

cur = conn.cursor()


# --------------------------------------------------
# 1. Clear existing Glider data
# --------------------------------------------------

print("Clearing existing Glider data...")

cur.execute("DELETE FROM glider_observations;")
cur.execute("DELETE FROM glider_platforms;")

print("Existing Glider data cleared.")


# --------------------------------------------------
# 2. Insert Glider platforms
# --------------------------------------------------

print("\nPreparing Glider platforms...")

platforms = (
    df.groupby("platform_deployment")
    .agg(
        latitude=("latitude", "last"),
        longitude=("longitude", "last"),
        last_seen=("time", "max")
    )
    .reset_index()
)


platform_values = []

for _, row in platforms.iterrows():

    glider_id = str(row["platform_deployment"])

    platform_values.append(
        (
            glider_id,
            glider_id,
            row["latitude"],
            row["longitude"],
            row["last_seen"]
        )
    )


execute_values(
    cur,
    """
    INSERT INTO glider_platforms
    (
        glider_id,
        glider_name,
        latitude,
        longitude,
        last_seen
    )
    VALUES %s
    """,
    platform_values
)

print(
    f"Uploaded {len(platform_values)} Glider platforms."
)


# --------------------------------------------------
# 3. Prepare observations
# --------------------------------------------------

print("\nPreparing Glider observations...")

observation_values = []

for row in df.itertuples(index=False):

    salinity = row.PSAL

    if pd.isna(salinity):
        salinity = None

    observation_values.append(
        (
            str(row.platform_deployment),
            row.time,
            row.latitude,
            row.longitude,
            row.PRES,
            row.TEMP,
            salinity
        )
    )


# --------------------------------------------------
# 4. Insert observations in batches
# --------------------------------------------------

print(
    f"Inserting {len(observation_values):,} "
    "Glider observations..."
)

BATCH_SIZE = 10000

for start in range(
    0,
    len(observation_values),
    BATCH_SIZE
):

    batch = observation_values[
        start:start + BATCH_SIZE
    ]

    execute_values(
        cur,
        """
        INSERT INTO glider_observations
        (
            glider_id,
            observation_time,
            latitude,
            longitude,
            depth,
            temperature,
            salinity
        )
        VALUES %s
        """,
        batch
    )

    inserted = min(
        start + BATCH_SIZE,
        len(observation_values)
    )

    print(
        f"Inserted {inserted:,} / "
        f"{len(observation_values):,}"
    )


# --------------------------------------------------
# 5. Commit
# --------------------------------------------------

conn.commit()

print("\nDatabase commit successful.")


# --------------------------------------------------
# 6. Verify database
# --------------------------------------------------

cur.execute(
    "SELECT COUNT(*) FROM glider_platforms;"
)

platform_count = cur.fetchone()[0]


cur.execute(
    "SELECT COUNT(*) FROM glider_observations;"
)

observation_count = cur.fetchone()[0]


cur.execute(
    """
    SELECT
        MIN(observation_time),
        MAX(observation_time)
    FROM glider_observations;
    """
)

first_time, last_time = cur.fetchone()


cur.execute(
    """
    SELECT
        glider_id,
        COUNT(*)
    FROM glider_observations
    GROUP BY glider_id
    ORDER BY glider_id;
    """
)

counts = cur.fetchall()


# --------------------------------------------------
# 7. Close connection
# --------------------------------------------------

cur.close()
conn.close()


# --------------------------------------------------
# Final report
# --------------------------------------------------

print("\n" + "=" * 70)
print("GLIDER DATABASE UPDATE COMPLETE")
print("=" * 70)

print(
    f"\nGlider platforms in database: "
    f"{platform_count}"
)

print(
    f"Glider observations in database: "
    f"{observation_count:,}"
)

print("\nObservation time range:")
print("First:", first_time)
print("Last :", last_time)

print("\nObservations per Glider:")

for glider_id, count in counts:
    print(
        f"  {glider_id}: {count:,}"
    )

print("\nExpected platforms:")
print("  Bellatrix_368")
print("  Denebola_382")
print("  Humpback_504")
print("  Marlin_505")
print("  Melonhead_506")

print("\nDone.")