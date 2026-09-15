import os

import numpy as np
import psycopg2
import xarray as xr
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


# ============================================================
# B2 / MODEL CONFIGURATION
# ============================================================

# Account 1 — GLORYS model storage
B2_1_KEY_ID = os.getenv("B2_1_KEY_ID")
B2_1_APPLICATION_KEY = os.getenv("B2_1_APPLICATION_KEY")
B2_1_BUCKET_NAME = os.getenv("B2_1_BUCKET_NAME")
B2_1_ENDPOINT = os.getenv("B2_1_ENDPOINT")

# Argo comparison model
B2_1_MODEL_PATH = os.getenv("B2_1_MODEL_PATH")

# Glider comparison model
B2_1_GLIDER_MODEL_PATH = os.getenv(
    "B2_1_GLIDER_MODEL_PATH"
)


# ============================================================
# B2 ACCOUNT 1 STORAGE OPTIONS
# ============================================================

def get_b2_1_storage_options():

    return {
        "key": B2_1_KEY_ID,
        "secret": B2_1_APPLICATION_KEY,
        "client_kwargs": {
            "endpoint_url": B2_1_ENDPOINT
        }
    }


# ============================================================
# OPEN GLORYS MODEL FROM BACKBLAZE B2
# Used by Argo comparison
# ============================================================

def open_model():

    model_url = (
        f"s3://{B2_1_BUCKET_NAME}/{B2_1_MODEL_PATH}"
    )

    return xr.open_dataset(
        model_url,
        engine="h5netcdf",
        backend_kwargs={
            "storage_options": get_b2_1_storage_options()
        }
    )


# ============================================================
# ARGO OBSERVATIONS
# ============================================================

def get_argo_observations():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            platform_id,
            cycle_number,
            observation_time,
            latitude,
            longitude,
            depth,
            temperature,
            salinity
        FROM argo_observations
        ORDER BY observation_time;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    observations = []

    for row in rows:

        observations.append({
            "platform_id": row[0],
            "cycle_number": row[1],
            "observation_time": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4]),
            "depth": float(row[5]),
            "temperature": (
                float(row[6])
                if row[6] is not None
                else None
            ),
            "salinity": (
                float(row[7])
                if row[7] is not None
                else None
            ),
        })

    return observations


# ============================================================
# ARGO ↔ GLORYS COMPARISON
# ============================================================

def compare_argo_with_model(observations=None):

    if observations is None:
        observations = get_argo_observations()

    ds = open_model()

    results = []

    for obs in observations:

        try:

            model_point = ds.interp(
                time=xr.DataArray(
                    np.datetime64(
                        obs["observation_time"].replace(
                            tzinfo=None
                        )
                    )
                ),
                latitude=obs["latitude"],
                longitude=obs["longitude"],
                depth=obs["depth"],
                method="linear"
            )

            model_temperature = (
                model_point["thetao"].item()
            )

            model_salinity = (
                model_point["so"].item()
            )

        except Exception:
            continue

        if (
            model_temperature is None
            or np.isnan(model_temperature)
        ):
            continue

        if (
            model_salinity is not None
            and np.isnan(model_salinity)
        ):
            model_salinity = None

        temperature_difference = None

        if obs["temperature"] is not None:

            temperature_difference = (
                model_temperature
                - obs["temperature"]
            )

        salinity_difference = None

        if (
            obs["salinity"] is not None
            and model_salinity is not None
        ):

            salinity_difference = (
                model_salinity
                - obs["salinity"]
            )

        results.append({
            "platform_id": obs["platform_id"],
            "cycle_number": obs["cycle_number"],
            "observation_time": obs["observation_time"],
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "depth": obs["depth"],
            "argo_temperature": obs["temperature"],
            "model_temperature": (
                float(model_temperature)
                if model_temperature is not None
                else None
            ),
            "temperature_difference": (
                temperature_difference
            ),
            "argo_salinity": obs["salinity"],
            "model_salinity": (
                float(model_salinity)
                if model_salinity is not None
                else None
            ),
            "salinity_difference": (
                salinity_difference
            ),
        })

    ds.close()

    return results


# ============================================================
# SAVE ARGO COMPARISONS
# ============================================================

def save_comparisons_to_database(comparisons):

    if not comparisons:
        print("No Argo comparisons to save.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM argo_model_comparisons;"
    )

    conn.commit()

    insert_sql = """
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
        VALUES %s
    """

    values = [
        (
            result["platform_id"],
            result["cycle_number"],
            result["observation_time"],
            result["latitude"],
            result["longitude"],
            result["depth"],
            result["argo_temperature"],
            result["model_temperature"],
            result["temperature_difference"],
            result["argo_salinity"],
            result["model_salinity"],
            result["salinity_difference"],
        )
        for result in comparisons
    ]

    execute_values(
        cur,
        insert_sql,
        values,
        page_size=10000
    )

    conn.commit()

    cur.close()
    conn.close()

    print(
        f"Saved {len(comparisons)} "
        f"Argo comparisons to database."
    )


# ============================================================
# GET NEW ARGO OBSERVATIONS
# ============================================================

def get_new_argo_observations():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            platform_id,
            cycle_number,
            observation_time,
            latitude,
            longitude,
            depth,
            temperature,
            salinity
        FROM argo_observations
        WHERE observation_time NOT IN (
            SELECT observation_time
            FROM argo_model_comparisons
        )
        ORDER BY observation_time;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    observations = []

    for row in rows:

        observations.append({
            "platform_id": row[0],
            "cycle_number": row[1],
            "observation_time": row[2],
            "latitude": float(row[3]),
            "longitude": float(row[4]),
            "depth": float(row[5]),
            "temperature": (
                float(row[6])
                if row[6] is not None
                else None
            ),
            "salinity": (
                float(row[7])
                if row[7] is not None
                else None
            ),
        })

    return observations


# ============================================================
# OPEN GLORYS MODEL FROM BACKBLAZE B2
# Used by Glider comparison
# ============================================================

def open_glider_model():

    model_url = (
        f"s3://{B2_1_BUCKET_NAME}/"
        f"{B2_1_GLIDER_MODEL_PATH}"
    )

    return xr.open_dataset(
        model_url,
        engine="h5netcdf",
        backend_kwargs={
            "storage_options": get_b2_1_storage_options()
        }
    )


# ============================================================
# GET GLIDER OBSERVATIONS IN BATCHES
# ============================================================

def get_glider_observations_batch(
    offset=0,
    batch_size=10000
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            glider_id,
            observation_time,
            latitude,
            longitude,
            depth,
            temperature,
            salinity
        FROM glider_observations
        ORDER BY observation_time, glider_id
        LIMIT %s OFFSET %s;
    """, (
        batch_size,
        offset
    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    observations = []

    for row in rows:

        observations.append({
            "glider_id": row[0],
            "observation_time": row[1],
            "latitude": float(row[2]),
            "longitude": float(row[3]),
            "depth": float(row[4]),
            "temperature": (
                float(row[5])
                if row[5] is not None
                else None
            ),
            "salinity": (
                float(row[6])
                if row[6] is not None
                else None
            ),
        })

    return observations


# ============================================================
# COUNT GLIDER OBSERVATIONS
# ============================================================

def get_glider_observation_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM glider_observations;
    """)

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return count


# ============================================================
# GLIDER ↔ GLORYS COMPARISON FOR ONE BATCH
# ============================================================

def compare_glider_batch(
    observations,
    ds
):

    if not observations:
        return []

    # --------------------------------------------------------
    # Model domain
    # --------------------------------------------------------

    min_lat = float(ds.latitude.min())
    max_lat = float(ds.latitude.max())

    min_lon = float(ds.longitude.min())
    max_lon = float(ds.longitude.max())

    min_depth = float(ds.depth.min())
    max_depth = float(ds.depth.max())

    # --------------------------------------------------------
    # Keep observations inside model domain
    # --------------------------------------------------------

    valid_observations = []

    for obs in observations:

        if not (
            min_lat <= obs["latitude"] <= max_lat
            and
            min_lon <= obs["longitude"] <= max_lon
            and
            min_depth <= obs["depth"] <= max_depth
        ):
            continue

        valid_observations.append(obs)

    if not valid_observations:
        return []

    # --------------------------------------------------------
    # Convert observation values to arrays
    # --------------------------------------------------------

    times = np.array([
        np.datetime64(
            obs["observation_time"].replace(
                tzinfo=None
            )
        )
        for obs in valid_observations
    ])

    latitudes = np.array([
        obs["latitude"]
        for obs in valid_observations
    ])

    longitudes = np.array([
        obs["longitude"]
        for obs in valid_observations
    ])

    depths = np.array([
        obs["depth"]
        for obs in valid_observations
    ])

    # --------------------------------------------------------
    # Vectorized 4D interpolation
    #
    # time + latitude + longitude + depth
    # --------------------------------------------------------

    model_points = ds.interp(
        time=xr.DataArray(
            times,
            dims="obs"
        ),
        latitude=xr.DataArray(
            latitudes,
            dims="obs"
        ),
        longitude=xr.DataArray(
            longitudes,
            dims="obs"
        ),
        depth=xr.DataArray(
            depths,
            dims="obs"
        ),
        method="linear"
    )

    model_temperatures = (
        model_points["thetao"].values
    )

    model_salinities = (
        model_points["so"].values
    )

    results = []

    # --------------------------------------------------------
    # Create comparison records
    # --------------------------------------------------------

    for i, obs in enumerate(
        valid_observations
    ):

        model_temperature = (
            float(model_temperatures[i])
            if not np.isnan(
                model_temperatures[i]
            )
            else None
        )

        model_salinity = (
            float(model_salinities[i])
            if not np.isnan(
                model_salinities[i]
            )
            else None
        )

        # Skip if model temperature unavailable
        if model_temperature is None:
            continue

        # ----------------------------------------------------
        # Temperature difference
        #
        # model - glider
        # ----------------------------------------------------

        temperature_difference = None

        if obs["temperature"] is not None:

            temperature_difference = (
                model_temperature
                - obs["temperature"]
            )

        # ----------------------------------------------------
        # Salinity difference
        #
        # model - glider
        # ----------------------------------------------------

        salinity_difference = None

        if (
            obs["salinity"] is not None
            and
            model_salinity is not None
        ):

            salinity_difference = (
                model_salinity
                - obs["salinity"]
            )

        results.append({
            "glider_id": obs["glider_id"],
            "observation_time": (
                obs["observation_time"]
            ),
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "depth": obs["depth"],
            "glider_temperature": (
                obs["temperature"]
            ),
            "model_temperature": (
                model_temperature
            ),
            "temperature_difference": (
                temperature_difference
            ),
            "glider_salinity": (
                obs["salinity"]
            ),
            "model_salinity": (
                model_salinity
            ),
            "salinity_difference": (
                salinity_difference
            ),
        })

    return results


# ============================================================
# SAVE ONE GLIDER COMPARISON BATCH
# ============================================================

def save_glider_comparison_batch(
    comparisons
):

    if not comparisons:
        return 0

    conn = get_connection()
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO glider_model_comparisons (
            glider_id,
            observation_time,
            latitude,
            longitude,
            depth,
            glider_temperature,
            model_temperature,
            temperature_difference,
            glider_salinity,
            model_salinity,
            salinity_difference
        )
        VALUES %s
    """

    values = [
        (
            result["glider_id"],
            result["observation_time"],
            result["latitude"],
            result["longitude"],
            result["depth"],
            result["glider_temperature"],
            result["model_temperature"],
            result["temperature_difference"],
            result["glider_salinity"],
            result["model_salinity"],
            result["salinity_difference"],
        )
        for result in comparisons
    ]

    execute_values(
        cur,
        insert_sql,
        values,
        page_size=10000
    )

    conn.commit()

    cur.close()
    conn.close()

    return len(comparisons)