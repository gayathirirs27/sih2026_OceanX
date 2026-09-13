from fastapi import APIRouter, HTTPException, Query
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(
    prefix="/api/comparison",
    tags=["Comparison"]
)


@router.get("/argo")
def get_argo_comparison(
    platform_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        if platform_id:
            cur.execute(
                """
                SELECT
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
                FROM argo_model_comparisons
                WHERE platform_id = %s
                ORDER BY observation_time, depth
                LIMIT %s OFFSET %s;
                """,
                (platform_id, limit, offset)
            )
        else:
            cur.execute(
                """
                SELECT
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
                FROM argo_model_comparisons
                ORDER BY observation_time, depth
                LIMIT %s OFFSET %s;
                """,
                (limit, offset)
            )

        rows = cur.fetchall()

        comparisons = []

        for row in rows:
            comparisons.append({
                "platform_id": row[0],
                "cycle_number": row[1],
                "observation_time": row[2],
                "latitude": row[3],
                "longitude": row[4],
                "depth": row[5],

                "temperature": {
                    "argo": row[6],
                    "model": row[7],
                    "difference": row[8]
                },

                "salinity": {
                    "argo": row[9],
                    "model": row[10],
                    "difference": row[11]
                }
            })

        cur.close()
        conn.close()

        return {
            "count": len(comparisons),
            "limit": limit,
            "offset": offset,
            "comparisons": comparisons
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/argo/summary")
def get_argo_comparison_summary():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(temperature_difference),
                AVG(temperature_difference),
                AVG(ABS(temperature_difference)),
                SQRT(AVG(temperature_difference * temperature_difference)),

                COUNT(salinity_difference),
                AVG(salinity_difference),
                AVG(ABS(salinity_difference)),
                SQRT(AVG(salinity_difference * salinity_difference))

            FROM argo_model_comparisons;
        """)

        row = cur.fetchone()

        cur.close()
        conn.close()

        return {
            "dataset": "GLORYS12V1",
            "observation_source": "Argo",
            "temperature": {
                "valid_comparisons": row[0],
                "bias": row[1],
                "mae": row[2],
                "rmse": row[3]
            },
            "salinity": {
                "valid_comparisons": row[4],
                "bias": row[5],
                "mae": row[6],
                "rmse": row[7]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )   