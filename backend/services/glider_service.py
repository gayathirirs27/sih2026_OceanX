import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


# ---------------------------------------------------------
# GET ALL GLIDERS
# ---------------------------------------------------------

def get_gliders():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            glider_id,
            glider_name,
            latitude,
            longitude,
            last_seen
        FROM glider_platforms
        ORDER BY glider_id;
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "count": len(rows),
        "gliders": [
            {
                "glider_id": row[0],
                "glider_name": row[1],
                "latitude": row[2],
                "longitude": row[3],
                "last_seen": row[4],
            }
            for row in rows
        ],
    }


# ---------------------------------------------------------
# GET GLIDER TRAJECTORY
# ---------------------------------------------------------

def get_glider_trajectory(glider_id):
    conn = get_connection()
    cur = conn.cursor()

    # Glider observations are high-frequency.
    # All observations remain stored in Supabase.
    # The API returns approximately 500 points for
    # lightweight map visualization.

    cur.execute("""
        WITH numbered AS (
            SELECT
                glider_id,
                observation_time,
                latitude,
                longitude,
                ROW_NUMBER() OVER (
                    ORDER BY observation_time
                ) AS rn,
                COUNT(*) OVER () AS total_count
            FROM glider_observations
            WHERE glider_id = %s
        )
        SELECT
            glider_id,
            observation_time,
            latitude,
            longitude
        FROM numbered
        WHERE rn = 1
           OR MOD(
                rn,
                GREATEST(
                    1,
                    CEIL(total_count / 500.0)::INTEGER
                )
           ) = 0
        ORDER BY observation_time;
    """, (glider_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        return None

    return {
        "glider_id": glider_id,
        "count": len(rows),
        "trajectory": [
            {
                "observation_time": row[1],
                "latitude": row[2],
                "longitude": row[3],
            }
            for row in rows
        ],
    }


# ---------------------------------------------------------
# GET GLIDER PROFILE
# ---------------------------------------------------------

def get_glider_profile(glider_id, observation_time=None):
    conn = get_connection()
    cur = conn.cursor()

    if observation_time:

        # Instead of requiring an exact timestamp,
        # find the nearest observation to the requested time.
        cur.execute("""
            SELECT observation_time
            FROM glider_observations
            WHERE glider_id = %s
            ORDER BY ABS(
                EXTRACT(
                    EPOCH FROM (
                        observation_time
                        - %s::timestamptz
                    )
                )
            )
            LIMIT 1;
        """, (glider_id, observation_time))

        nearest = cur.fetchone()

        if not nearest:
            cur.close()
            conn.close()
            return None

        selected_time = nearest[0]

        # Use a ±10 minute window around the selected
        # observation to construct a useful Glider profile.
        cur.execute("""
            SELECT
                observation_time,
                depth,
                temperature,
                salinity
            FROM glider_observations
            WHERE glider_id = %s
              AND observation_time BETWEEN
                    %s - INTERVAL '10 minutes'
                    AND
                    %s + INTERVAL '10 minutes'
            ORDER BY depth;
        """, (glider_id, selected_time, selected_time))

    else:

        # No time supplied: return a limited set of
        # observations for general exploration.
        cur.execute("""
            SELECT
                observation_time,
                depth,
                temperature,
                salinity
            FROM glider_observations
            WHERE glider_id = %s
            ORDER BY observation_time, depth
            LIMIT 5000;
        """, (glider_id,))

        selected_time = None

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        return None

    return {
        "glider_id": glider_id,
        "count": len(rows),
        "selected_observation_time": selected_time,
        "profile": [
            {
                "observation_time": row[0],
                "depth": row[1],
                "temperature": row[2],
                "salinity": row[3],
            }
            for row in rows
        ],
    }