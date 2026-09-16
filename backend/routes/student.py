from fastapi import APIRouter, HTTPException, Query
import math

from backend.services.comparison_service import open_model

router = APIRouter(
    prefix="/api/stakeholder",
    tags=["Stakeholder - Student"],
)


@router.get("/student")
def student(
    latitude: float = Query(..., ge=5, le=25),
    longitude: float = Query(..., ge=80, le=100),
    depth: float = Query(0, ge=0),
):
    ds = None

    try:
        ds = open_model()

        available_depths = ds.depth.values

        depth_index = int(
            abs(available_depths - depth).argmin()
        )

        actual_depth = float(
            available_depths[depth_index]
        )

        point = ds.thetao.isel(
            time=0,
            depth=depth_index,
        ).interp(
            latitude=latitude,
            longitude=longitude,
        )

        temperature = float(point.values)

        if math.isnan(temperature):
            temperature = None

        if actual_depth <= 50:
            zone = "Sunlight"
        elif actual_depth <= 200:
            zone = "Twilight"
        else:
            zone = "Deep"

        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "model": "GLORYS12V1 / Copernicus Marine",
            "time": str(ds.time.values[0]),
            "requested_depth": depth,
            "actual_depth": actual_depth,
            "temperature_c": temperature,
            "depth_zone": zone,
            "explanation": {
                "Sunlight": "Upper ocean where sunlight is strongest.",
                "Twilight": "Lower-light transition zone.",
                "Deep": "Deeper ocean below the main light-penetrated layer.",
            }[zone],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load student data: {str(e)}"
        )

    finally:
        if ds:
            ds.close()