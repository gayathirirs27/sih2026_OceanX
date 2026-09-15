from fastapi import APIRouter, HTTPException
from backend.services.chlorophyll_service import (
    get_chlorophyll_metadata,
    get_chlorophyll_field,
)

router = APIRouter(
    prefix="/api/chlorophyll",
    tags=["Chlorophyll"]
)


@router.get("/metadata")
def metadata():
    return get_chlorophyll_metadata()


@router.get("/field")
def field(observation_time: str | None = None):
    try:
        return get_chlorophyll_field(observation_time)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load chlorophyll data: {str(e)}"
        )