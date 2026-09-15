import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL")
    )


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

def get_summary():

    conn = get_connection()
    cur = conn.cursor()

    # Total observations
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM argo_observations)
            +
            (SELECT COUNT(*) FROM glider_observations);
    """)

    total_observations = cur.fetchone()[0]

    # Argo model comparison statistics
    cur.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE temperature_difference IS NOT NULL
            ),
            AVG(
                ABS(temperature_difference)
            ),
            AVG(
                temperature_difference
            ),
            SQRT(
                AVG(
                    temperature_difference *
                    temperature_difference
                )
            )
        FROM argo_model_comparisons;
    """)

    row = cur.fetchone()

    comparison_count = row[0] or 0
    temperature_mae = float(row[1]) if row[1] is not None else None
    temperature_bias = float(row[2]) if row[2] is not None else None
    temperature_rmse = float(row[3]) if row[3] is not None else None

    cur.close()
    conn.close()

    # Simple accuracy indicator.
    # This is NOT a percentage claimed by the model.
    # It is only a normalized score based on RMSE.
    if temperature_rmse is not None:
        model_accuracy_score = max(
            0,
            100 - (temperature_rmse * 10)
        )
    else:
        model_accuracy_score = None

    return {
        "total_observations": total_observations,
        "argo_model_comparisons": comparison_count,
        "temperature_mae": temperature_mae,
        "temperature_bias": temperature_bias,
        "temperature_rmse": temperature_rmse,
        "model_accuracy_score": model_accuracy_score
    }


# ============================================================
# TEMPERATURE TREND
# ============================================================

def get_temperature_trend():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            DATE_TRUNC(
                'month',
                observation_time
            ) AS month,
            AVG(temperature) AS temperature,
            COUNT(*) AS observations
        FROM argo_observations
        WHERE temperature IS NOT NULL
        GROUP BY month
        ORDER BY month;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "month": row[0].strftime("%Y-%m"),
            "temperature": round(float(row[1]), 3),
            "observations": row[2]
        }
        for row in rows
    ]


# ============================================================
# SALINITY BY DEPTH
# ============================================================

def get_salinity_depth():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            ROUND(depth::numeric, 1) AS depth,
            AVG(salinity) AS salinity,
            COUNT(*) AS observations
        FROM argo_observations
        WHERE salinity IS NOT NULL
        GROUP BY depth
        ORDER BY depth;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "depth": float(row[0]),
            "salinity": round(float(row[1]), 3),
            "observations": row[2]
        }
        for row in rows
    ]


# ============================================================
# MODEL PERFORMANCE
# ============================================================

def get_model_performance():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            AVG(temperature_difference),
            AVG(
                ABS(temperature_difference)
            ),
            SQRT(
                AVG(
                    temperature_difference *
                    temperature_difference
                )
            ),
            AVG(salinity_difference),
            AVG(
                ABS(salinity_difference)
            ),
            SQRT(
                AVG(
                    salinity_difference *
                    salinity_difference
                )
            )
        FROM argo_model_comparisons;
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "model": "GLORYS / Copernicus",

        "temperature": {
            "bias": (
                float(row[0])
                if row[0] is not None
                else None
            ),
            "mae": (
                float(row[1])
                if row[1] is not None
                else None
            ),
            "rmse": (
                float(row[2])
                if row[2] is not None
                else None
            )
        },

        "salinity": {
            "bias": (
                float(row[3])
                if row[3] is not None
                else None
            ),
            "mae": (
                float(row[4])
                if row[4] is not None
                else None
            ),
            "rmse": (
                float(row[5])
                if row[5] is not None
                else None
            )
        }
    }


# ============================================================
# SIMPLE ANOMALY DETECTION
# ============================================================

def get_anomalies():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        WITH stats AS (
            SELECT
                AVG(temperature) AS mean_temp,
                STDDEV(temperature) AS std_temp
            FROM argo_observations
            WHERE temperature IS NOT NULL
        )

        SELECT
            a.platform_id,
            a.observation_time,
            a.latitude,
            a.longitude,
            a.depth,
            a.temperature,
            stats.mean_temp,
            stats.std_temp
        FROM argo_observations a
        CROSS JOIN stats
        WHERE
            a.temperature IS NOT NULL
            AND stats.std_temp IS NOT NULL
            AND ABS(
                a.temperature - stats.mean_temp
            ) > 2 * stats.std_temp
        ORDER BY a.observation_time DESC
        LIMIT 20;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "platform_id": row[0],
            "observation_time": row[1],
            "latitude": float(row[2]),
            "longitude": float(row[3]),
            "depth": float(row[4]),
            "temperature": float(row[5]),
            "mean_temperature": round(
                float(row[6]), 3
            ),
            "type": "Temperature anomaly"
        }
        for row in rows
    ]