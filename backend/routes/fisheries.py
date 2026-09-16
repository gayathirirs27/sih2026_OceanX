from fastapi import APIRouter, HTTPException
import math

from backend.services.nrt_service import get_nrt_field
from backend.services.chlorophyll_service import get_chlorophyll_field

router = APIRouter(prefix="/api/stakeholder", tags=["Stakeholder - Fisheries"])


def field_mean(variable, depth=0):
    data = get_nrt_field(variable, depth)

    values = [
        value
        for row in data["values"]
        for value in row
        if value is not None and math.isfinite(value)
    ]

    if not values:
        return None

    return sum(values) / len(values)


@router.get("/fisheries")
def fisheries():
    try:
        temperature = field_mean("thetao", 0)
        salinity = field_mean("so", 0)
        u = field_mean("uo", 0)
        v = field_mean("vo", 0)

        current_speed = None

        if u is not None and v is not None:
            current_speed = math.sqrt(u * u + v * v)

        chlorophyll = get_chlorophyll_field()

        chl_points = chlorophyll.get("points", [])

        chl_values = [
            p["chlorophyll"]
            for p in chl_points
            if p.get("chlorophyll") is not None
        ]

        mean_chlorophyll = (
            sum(chl_values) / len(chl_values)
            if chl_values
            else None
        )

        # Simple decision-support classification.
        if mean_chlorophyll is None:
            zone = "Unknown"
        elif mean_chlorophyll >= 1:
            zone = "Favourable"
        elif mean_chlorophyll >= 0.3:
            zone = "Moderate"
        else:
            zone = "Low"

        return {
            "dataset": "Copernicus Marine NRT + Chlorophyll",
            "temperature_surface_c": temperature,
            "salinity_surface_psu": salinity,
            "surface_current_speed_ms": current_speed,
            "chlorophyll": {
                "mean": mean_chlorophyll,
                "time": chlorophyll.get("time"),
            },
            "productivity_indicator": zone,
            "note": (
                "Zone classification is a simple chlorophyll-based "
                "decision-support indicator and does not represent "
                "fish presence or biomass."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load fisheries data: {str(e)}"
        )