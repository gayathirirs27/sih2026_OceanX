import os
import psycopg2
from dotenv import load_dotenv
from services.comparison_service import compare_argo_with_model
from services.comparison_service import (
    compare_argo_with_model,
    get_argo_observations,
    get_new_argo_observations
)

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("Checking Argo data status...\n")

# Get current Argo data status
cur.execute("""
    SELECT COUNT(*), MAX(observation_time)
    FROM argo_observations;
""")

current_count, current_latest = cur.fetchone()

# Get previously compared status
cur.execute("""
    SELECT observation_count, latest_observation_time
    FROM comparison_status
    WHERE data_source = 'argo';
""")

previous = cur.fetchone()

if previous:
    previous_count, previous_latest = previous
else:
    previous_count, previous_latest = 0, None

print(f"Current Argo records:      {current_count}")
print(f"Previously compared:      {previous_count}")
print(f"Current latest time:       {current_latest}")
print(f"Previously compared time:  {previous_latest}\n")

# Check whether anything changed
if current_count == previous_count and current_latest == previous_latest:
    print("✅ Argo data has not changed.")
    print("No comparison is required.")

    cur.close()
    conn.close()
    exit()

print("🆕 New Argo data detected.")
print("Running comparison...\n")

if previous_latest is None:
    new_observations = get_argo_observations()
else:
    new_observations = get_new_argo_observations(previous_latest)

print(f"New observations to compare: {len(new_observations)}\n")

if not new_observations:
    print("No new observations found.")
    cur.close()
    conn.close()
    exit()

results = compare_argo_with_model(new_observations)

inserted = 0

for r in results:

    temperature_difference = None
    salinity_difference = None

    if (
        r["observed_temperature"] is not None
        and r["model_temperature"] is not None
    ):
        temperature_difference = (
            r["model_temperature"] - r["observed_temperature"]
        )

    if (
        r["observed_salinity"] is not None
        and r["model_salinity"] is not None
    ):
        salinity_difference = (
            r["model_salinity"] - r["observed_salinity"]
        )

    cur.execute(
        """
        INSERT INTO argo_model_comparisons (
            platform_id,
            cycle_number,
            observation_time,
            latitude,
            longitude,
            depth,
            argo_temperature,
            model_temperature,
            temperature_difference,
            argo_salinity,
            model_salinity,
            salinity_difference
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (
            platform_id,
            cycle_number,
            observation_time,
            depth
        )
        DO NOTHING;
        """,
        (
            r["platform_id"],
            r["cycle_number"],
            r["observation_time"],
            r["latitude"],
            r["longitude"],
            r["depth"],
            r["observed_temperature"],
            r["model_temperature"],
            temperature_difference,
            r["observed_salinity"],
            r["model_salinity"],
            salinity_difference,
        )
    )

    if cur.rowcount == 1:
        inserted += 1

# Update status after successful comparison
cur.execute(
    """
    UPDATE comparison_status
    SET observation_count = %s,
        latest_observation_time = %s,
        last_compared_at = NOW()
    WHERE data_source = 'argo';
    """,
    (current_count, current_latest)
)

conn.commit()

cur.close()
conn.close()

print("========================================")
print(f"Comparison results checked: {len(results)}")
print(f"New records inserted:       {inserted}")
print("✅ Comparison database updated.")
print("========================================")