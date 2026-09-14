from fastapi import APIRouter, HTTPException, Query
import os
import psycopg2
from dotenv import load_dotenv


load_dotenv()

router = APIRouter(
    prefix="/api/argo",
    tags=["Argo"]
)


@router.get("/floats")
def get_argo_floats():

    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL")
        )

        cur = conn.cursor()

        cur.execute("""
            SELECT
                platform_id,
                platform_type,
                latitude,
                longitude,
                last_seen
            FROM argo_platforms
            ORDER BY platform_id;
        """)

        rows = cur.fetchall()

        floats = []

        for row in rows:
            floats.append({
                "platform_id": row[0],
                "platform_type": row[1],
                "latitude": row[2],
                "longitude": row[3],
                "last_seen": row[4]
            })

        cur.close()
        conn.close()

        return {
            "count": len(floats),
            "floats": floats
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/trajectory")
def get_argo_trajectory(
    platform_id: str = Query(...)
):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute("""
            SELECT DISTINCT
                platform_id,
                cycle_number,
                observation_time,
                latitude,
                longitude
            FROM argo_observations
            WHERE platform_id = %s
            ORDER BY observation_time;
        """, (platform_id,))

        rows = cur.fetchall()

        trajectory = []

        for row in rows:
            trajectory.append({
                "platform_id": row[0],
                "cycle_number": row[1],
                "observation_time": row[2],
                "latitude": row[3],
                "longitude": row[4]
            })

        cur.close()
        conn.close()

        return {
            "platform_id": platform_id,
            "count": len(trajectory),
            "trajectory": trajectory
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
def get_argo_profile(
    platform_id: str = Query(...),
    cycle_number: int | None = Query(None)
):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        if cycle_number is not None:
            cur.execute("""
                SELECT
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
                FROM argo_observations
                WHERE platform_id = %s
                  AND cycle_number = %s
                ORDER BY depth;
            """, (platform_id, cycle_number))
        else:
            cur.execute("""
                SELECT
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
                FROM argo_observations
                WHERE platform_id = %s
                ORDER BY observation_time, depth;
            """, (platform_id,))

        rows = cur.fetchall()

        profile = []

        for row in rows:
            profile.append({
                "platform_id": row[0],
                "cycle_number": row[1],
                "observation_time": row[2],
                "latitude": row[3],
                "longitude": row[4],
                "depth": row[5],
                "temperature": row[6],
                "salinity": row[7],
                "temperature_qc": row[8],
                "salinity_qc": row[9]
            })

        cur.close()
        conn.close()

        return {
            "platform_id": platform_id,
            "cycle_number": cycle_number,
            "count": len(profile),
            "profile": profile
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))