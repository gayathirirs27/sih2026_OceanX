from fastapi import APIRouter, HTTPException
import math

from backend.services.nrt_service import get_nrt_field
from backend.services.chlorophyll_service import get_chlorophyll_field
from backend.services.analytics_service import (
    get_temperature_trend,
    get_salinity_depth,
    get_anomalies,
)

router = APIRouter(
    prefix="/api/stakeholder",
    tags=["Stakeholder - Policymaker"],
)


def field_statistics(variable):
    data = get_nrt_field(variable, 0)

    values = [
        value
        for row in data["values"]
        for value in row
        if value is not None and math.isfinite(value)
    ]

    if not values:
        return {
            "mean": None,
            "min": None,
            "max": None,
            "time": data["time"],
        }

    return {
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
        "time": data["time"],
    }


@router.get("/policymaker")
def policymaker():
    try:
        temperature = field_statistics("thetao")
        salinity = field_statistics("so")
        u = field_statistics("uo")
        v = field_statistics("vo")

        if u["mean"] is not None and v["mean"] is not None:
            current_speed = math.sqrt(
                u["mean"] ** 2 + v["mean"] ** 2
            )
        else:
            current_speed = None

        chlorophyll = get_chlorophyll_field()

        chl_values = [
            p["chlorophyll"]
            for p in chlorophyll.get("points", [])
            if p.get("chlorophyll") is not None
        ]

        mean_chlorophyll = (
            sum(chl_values) / len(chl_values)
            if chl_values
            else None
        )

        alerts = []

        if temperature["max"] is not None and temperature["max"] >= 30:
            alerts.append("High regional surface temperature")

        if current_speed is not None and current_speed >= 1:
            alerts.append("Elevated regional surface current")

        return {
            "dataset": "Copernicus Marine NRT + OceanX observations",
            "current_regional_status": {
                "temperature_c": temperature,
                "salinity_psu": salinity,
                "surface_current_speed_ms": current_speed,
                "chlorophyll": {
                    "mean": mean_chlorophyll,
                    "time": chlorophyll.get("time"),
                },
            },
            "recent_temperature_trend": get_temperature_trend(),
            "recent_salinity_trend": get_salinity_depth(),
            "condition_alerts": alerts,
            "observation_anomalies": get_anomalies(),
            "note": (
                "Trends shown here are based on the available recent "
                "OceanX observation data; this endpoint does not represent "
                "a long-term climatology."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load policymaker data: {str(e)}"
        )