from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
import math

from backend.services.nrt_service import get_nrt_field

router = APIRouter(
    prefix="/api/stakeholder/search-rescue",
    tags=["Stakeholder - Search & Rescue"],
)


class DriftRequest(BaseModel):
    latitude: float = Field(..., ge=5, le=25)
    longitude: float = Field(..., ge=80, le=100)
    start_time: datetime
    duration_hours: int = Field(12, ge=1, le=72)


def nearest_value(data, latitude, longitude):
    lats = data["latitude"]
    lons = data["longitude"]
    values = data["values"]

    lat_index = min(
        range(len(lats)),
        key=lambda i: abs(lats[i] - latitude)
    )

    lon_index = min(
        range(len(lons)),
        key=lambda i: abs(lons[i] - longitude)
    )

    value = values[lat_index][lon_index]

    return value


@router.post("/drift")
def drift(request: DriftRequest):
    try:
        u_field = get_nrt_field("uo", 0)
        v_field = get_nrt_field("vo", 0)

        latitude = request.latitude
        longitude = request.longitude

        trajectory = []

        start = request.start_time

        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        for hour in range(request.duration_hours + 1):
            current_time = start + timedelta(hours=hour)

            trajectory.append({
                "time": current_time.isoformat(),
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
            })

            u = nearest_value(
                u_field,
                latitude,
                longitude,
            )

            v = nearest_value(
                v_field,
                latitude,
                longitude,
            )

            if u is None or v is None:
                break

            # Convert m/s → approximate degrees for one hour.
            latitude += (
                v * 3600 / 111320
            )

            cos_lat = max(
                0.1,
                math.cos(math.radians(latitude))
            )

            longitude += (
                u * 3600
                / (111320 * cos_lat)
            )

            # Stop if the trajectory leaves the model domain.
            if not (
                5 <= latitude <= 25
                and 80 <= longitude <= 100
            ):
                break

        if len(trajectory) > 1:
            lat1 = trajectory[0]["latitude"]
            lon1 = trajectory[0]["longitude"]

            lat2 = trajectory[-1]["latitude"]
            lon2 = trajectory[-1]["longitude"]

            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            mean_lat = math.radians((lat1 + lat2) / 2)

            distance_km = (
                6371
                * math.sqrt(
                    dlat ** 2
                    + (math.cos(mean_lat) * dlon) ** 2
                )
            )
        else:
            distance_km = 0

        return {
            "origin": {
                "latitude": request.latitude,
                "longitude": request.longitude,
            },
            "duration_hours": request.duration_hours,
            "trajectory": trajectory,
            "total_displacement_km": round(distance_km, 2),
            "model": "Current-driven approximation",
            "note": (
                "This is a decision-support trajectory based on the "
                "latest available surface current and is not a guaranteed "
                "prediction of object or person location."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to calculate drift: {str(e)}"
        )