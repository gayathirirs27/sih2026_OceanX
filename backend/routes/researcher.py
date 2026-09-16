from fastapi import APIRouter, HTTPException, Query
import math
import numpy as np

from backend.services.comparison_service import open_model, get_connection

router = APIRouter(prefix="/api/stakeholder", tags=["Stakeholder - Researcher"])


@router.get("/researcher")
def researcher(
    latitude: float = Query(..., ge=5, le=25),
    longitude: float = Query(..., ge=80, le=100),
    depth: float = Query(0, ge=0),
):
    ds = None
    conn = None

    try:
        ds = open_model()

        result = {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "requested_depth": depth,
            "model": {},
        }

        # Model point values
        for variable in ["thetao", "so", "uo", "vo"]:
            if variable not in ds:
                continue

            da = ds[variable]

            available_depths = ds.depth.values
            depth_index = int(abs(available_depths - depth).argmin())
            actual_depth = float(available_depths[depth_index])

            point = da.isel(
                depth=depth_index
            ).interp(
                latitude=latitude,
                longitude=longitude,
                method="linear",
            )

            value = float(point.values)

            result["model"][variable] = {
                "value": None if not math.isfinite(value) else value,
                "actual_depth": actual_depth,
            }

        # Current speed and direction
        u = result["model"].get("uo", {}).get("value")
        v = result["model"].get("vo", {}).get("value")

        if u is not None and v is not None:
            speed = math.sqrt(u * u + v * v)
            direction = (math.degrees(math.atan2(u, v)) + 360) % 360

            result["model"]["current"] = {
                "speed_ms": speed,
                "direction_degrees": direction,
            }

        # Simple temperature/salinity profile
        profiles = {}

        for variable in ["thetao", "so"]:
            if variable not in ds:
                continue

            profile = ds[variable].interp(
                latitude=latitude,
                longitude=longitude,
                method="linear",
            ).isel(time=0)

            values = profile.values

            profiles[variable] = [
                {
                    "depth": float(d),
                    "value": None if not np.isfinite(v) else float(v),
                }
                for d, v in zip(ds.depth.values, values)
            ]

        result["profiles"] = profiles

        # Simple stratification indicator
        temp_profile = profiles.get("thetao", [])

        valid_temp = [
            p for p in temp_profile
            if p["value"] is not None
        ]

        if len(valid_temp) >= 2:
            surface = valid_temp[0]["value"]
            deepest = valid_temp[-1]["value"]

            result["derived"] = {
                "temperature_difference_surface_to_deepest": (
                    surface - deepest
                ),
                "stratification_indicator": (
                    "strong"
                    if abs(surface - deepest) >= 3
                    else "moderate"
                    if abs(surface - deepest) >= 1
                    else "weak"
                ),
            }

        # Existing Argo/model comparison statistics
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) AS matched,
                AVG(temperature_difference),
                AVG(ABS(temperature_difference)),
                SQRT(AVG(temperature_difference * temperature_difference)),
                AVG(salinity_difference),
                AVG(ABS(salinity_difference)),
                SQRT(AVG(salinity_difference * salinity_difference))
            FROM argo_model_comparisons
            WHERE temperature_difference IS NOT NULL
        """)

        row = cur.fetchone()

        result["model_validation"] = {
            "matched_observations": int(row[0] or 0),
            "temperature_bias": float(row[1]) if row[1] is not None else None,
            "temperature_mae": float(row[2]) if row[2] is not None else None,
            "temperature_rmse": float(row[3]) if row[3] is not None else None,
            "salinity_bias": float(row[4]) if row[4] is not None else None,
            "salinity_mae": float(row[5]) if row[5] is not None else None,
            "salinity_rmse": float(row[6]) if row[6] is not None else None,
        }

        cur.close()

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load researcher data: {str(e)}"
        )

    finally:
        if conn:
            conn.close()

        if ds:
            ds.close()