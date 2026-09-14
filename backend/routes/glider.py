from fastapi import APIRouter, HTTPException
from backend.services.glider_service import (
    get_gliders,
    get_glider_trajectory,
    get_glider_profile,
)

router = APIRouter(prefix="/api/glider", tags=["Glider"])


@router.get("/gliders")
def gliders():
    return get_gliders()


@router.get("/{glider_id}/trajectory")
def trajectory(glider_id: str):
    result = get_glider_trajectory(glider_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Glider not found")

    return result


@router.get("/{glider_id}/profile")
def profile(
    glider_id: str,
    observation_time: str | None = None,
):
    result = get_glider_profile(glider_id, observation_time)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Glider or profile not found"
        )

    return result