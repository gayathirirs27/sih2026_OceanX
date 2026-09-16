from fastapi import APIRouter, HTTPException
import math

from backend.services.nrt_service import get_nrt_field

router = APIRouter(
    prefix="/api/stakeholder",
    tags=["Stakeholder - Forecaster"],
)


def regional_summary(variable, depth=0):
    data = get_nrt_field(
        variable=variable,
        depth=depth
    )

    values = [
        value
        for row in data["values"]
        for value in row
        if value is not None and math.isfinite(value)
    ]

    if not values:
        return {
            "variable": variable,
            "actual_depth": data["actual_depth"],
            "time": data["time"],
            "mean": None,
            "min": None,
            "max": None,
        }

    return {
        "variable": variable,
        "actual_depth": data["actual_depth"],
        "time": data["time"],
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


@router.get("/forecaster")
def forecaster():
    try:
        temperature = regional_summary("thetao", 0)
        salinity = regional_summary("so", 0)
        u = regional_summary("uo", 0)
        v = regional_summary("vo", 0)

        # Calculate regional mean current speed and direction
        if u["mean"] is not None and v["mean"] is not None:
            speed = math.sqrt(
                u["mean"] ** 2 +
                v["mean"] ** 2
            )

            direction = (
                math.degrees(
                    math.atan2(
                        u["mean"],
                        v["mean"]
                    )
                ) + 360
            ) % 360
        else:
            speed = None
            direction = None

        # Simple rule-based current-condition alerts
        alerts = []

        if (
            temperature["max"] is not None
            and temperature["max"] >= 30
        ):
            alerts.append(
                "High surface temperature"
            )

        if (
            speed is not None
            and speed >= 1.0
        ):
            alerts.append(
                "Strong surface current"
            )

        return {
            "dataset": "Copernicus Marine NRT",
            "mode": "current_conditions",
            "time": temperature["time"],

            "temperature": temperature,

            "salinity": salinity,

            "surface_current": {
                "u_ms": u["mean"],
                "v_ms": v["mean"],
                "speed_ms": speed,
                "direction_degrees": direction,
            },

            "alerts": alerts,

            "note": (
                "Current-condition indicators are derived "
                "from the latest available NRT field. "
                "This endpoint does not provide future forecasts."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to load forecaster data: {str(e)}"
            )
        )