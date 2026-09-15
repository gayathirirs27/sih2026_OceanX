from fastapi import APIRouter

from backend.services.analytics_service import (
    get_summary,
    get_temperature_trend,
    get_salinity_depth,
    get_model_performance,
    get_anomalies,
)


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)


# ============================================================
# ANALYTICS SUMMARY
# ============================================================

@router.get("/summary")
def analytics_summary():

    return get_summary()


# ============================================================
# TEMPERATURE TREND
# ============================================================

@router.get("/temperature-trend")
def temperature_trend():

    return get_temperature_trend()


# ============================================================
# SALINITY BY DEPTH
# ============================================================

@router.get("/salinity-depth")
def salinity_depth():

    return get_salinity_depth()


# ============================================================
# MODEL PERFORMANCE
# ============================================================

@router.get("/model-performance")
def model_performance():

    return get_model_performance()


# ============================================================
# ANOMALIES
# ============================================================

@router.get("/anomalies")
def anomalies():

    return get_anomalies()