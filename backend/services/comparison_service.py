import os
from pathlib import Path

import numpy as np
import psycopg2
import xarray as xr
from dotenv import load_dotenv

load_dotenv()

MODEL_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "raw"
    / "copernicus"
    / "cmems_mod_glo_phy_my_0.083deg_P1D-m_thetao-so-uo-vo_80.00E-100.00E_5.00N-25.00N_0.49-453.94m_2025-01-01-2025-03-31.nc"
)


def get_argo_observations():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
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
        WHERE temperature IS NOT NULL
           OR salinity IS NOT NULL
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
            "latitude": row[3],
            "longitude": row[4],
            "depth": row[5],
            "temperature": row[6],
            "salinity": row[7],
        })

    return observations


def compare_argo_with_model(observations=None):

    if observations is None:
        observations = get_argo_observations()


    ds = xr.open_dataset(MODEL_FILE)

    min_lat = float(ds.latitude.min())
    max_lat = float(ds.latitude.max())
    min_lon = float(ds.longitude.min())
    max_lon = float(ds.longitude.max())
    min_depth = float(ds.depth.min())
    max_depth = float(ds.depth.max())

    results = []

    for obs in observations:

        # Check whether observation is inside model spatial/depth domain
        if not (
            min_lat <= obs["latitude"] <= max_lat
            and min_lon <= obs["longitude"] <= max_lon
            and min_depth <= obs["depth"] <= max_depth
        ):
            continue

        observation_time = obs["observation_time"].replace(tzinfo=None)

        # Interpolate model to exact observation location,
        # depth and time
        model_point = ds.interp(
            time=np.datetime64(observation_time),
            latitude=obs["latitude"],
            longitude=obs["longitude"],
            depth=obs["depth"],
            method="linear"
        )

        model_temperature = model_point["thetao"].values.item()
        model_salinity = model_point["so"].values.item()

        if np.isnan(model_temperature):
            model_temperature = None

        if np.isnan(model_salinity):
            model_salinity = None

        temperature_difference = None
        salinity_difference = None

        if (
            obs["temperature"] is not None
            and model_temperature is not None
        ):
            temperature_difference = (
                model_temperature - obs["temperature"]
            )

        if (
            obs["salinity"] is not None
            and model_salinity is not None
        ):
            salinity_difference = (
                model_salinity - obs["salinity"]
            )

        results.append({
            "platform_id": obs["platform_id"],
            "cycle_number": obs["cycle_number"],
            "observation_time": str(obs["observation_time"]),
            "latitude": obs["latitude"],
            "longitude": obs["longitude"],
            "depth": obs["depth"],

            "observed_temperature": obs["temperature"],
            "model_temperature": model_temperature,
            "temperature_difference": temperature_difference,

            "observed_salinity": obs["salinity"],
            "model_salinity": model_salinity,
            "salinity_difference": salinity_difference,
        })

    ds.close()

    return results

def save_comparisons_to_database():
    results = compare_argo_with_model()

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    # Clear previous results before inserting fresh comparison data
    cur.execute("DELETE FROM argo_model_comparisons;")

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
            );
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

        inserted += 1

    conn.commit()

    cur.close()
    conn.close()

    return inserted

def get_new_argo_observations(previous_latest_time):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    cur.execute("""
        SELECT platform_id, cycle_number, observation_time,
               latitude, longitude, depth,
               temperature, salinity
        FROM argo_observations
        WHERE observation_time > %s
          AND (temperature IS NOT NULL OR salinity IS NOT NULL)
        ORDER BY observation_time;
    """, (previous_latest_time,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    observations = []

    for row in rows:
        observations.append({
            "platform_id": row[0],
            "cycle_number": row[1],
            "observation_time": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "depth": row[5],
            "temperature": row[6],
            "salinity": row[7],
        })

    return observations