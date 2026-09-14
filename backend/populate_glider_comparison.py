from services.comparison_service import (
    get_glider_observation_count,
    get_glider_observations_batch,
    open_glider_model,
    compare_glider_batch,
    save_glider_comparison_batch,
)

# ============================================================
# SETTINGS
# ============================================================

BATCH_SIZE = 10000


# ============================================================
# START
# ============================================================

print("========================================")
print("OceanX Glider ↔ GLORYS Comparison")
print("========================================\n")

total = get_glider_observation_count()

print(f"Total Glider observations: {total}")
print(f"Batch size:                {BATCH_SIZE}\n")


# ============================================================
# CLEAR OLD RESULTS
# ============================================================

print("Clearing previous Glider comparison results...")

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    os.getenv("DATABASE_URL")
)

cur = conn.cursor()

cur.execute(
    "DELETE FROM glider_model_comparisons;"
)

conn.commit()

cur.close()
conn.close()

print("Previous results cleared.\n")


# ============================================================
# OPEN MODEL ONCE
# ============================================================

print("Opening GLORYS Glider model...")

ds = open_glider_model()

print("GLORYS model opened successfully.\n")


# ============================================================
# PROCESS BATCHES
# ============================================================

offset = 0
total_successful = 0
total_skipped = 0

while offset < total:

    print("----------------------------------------")
    print(
        f"Reading observations "
        f"{offset + 1} - "
        f"{min(offset + BATCH_SIZE, total)}"
    )

    observations = get_glider_observations_batch(
        offset=offset,
        batch_size=BATCH_SIZE
    )

    if not observations:
        print("No more observations found.")
        break

    comparisons = compare_glider_batch(
        observations,
        ds
    )

    inserted = save_glider_comparison_batch(
        comparisons
    )

    skipped = len(observations) - inserted

    total_successful += inserted
    total_skipped += skipped

    processed = min(
        offset + len(observations),
        total
    )

    print(
        f"Processed:   {processed} / {total}"
    )

    print(
        f"Successful:  {inserted}"
    )

    print(
        f"Skipped:     {skipped}"
    )

    print(
        f"Total saved: {total_successful}"
    )

    offset += len(observations)


# ============================================================
# CLOSE MODEL
# ============================================================

ds.close()


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n========================================")
print("Glider comparison complete")
print("========================================")

print(
    f"Total observations:     {total}"
)

print(
    f"Successful comparisons: {total_successful}"
)

print(
    f"Skipped observations:   {total_skipped}"
)

print("========================================")