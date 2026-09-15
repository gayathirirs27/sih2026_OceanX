from fastapi import APIRouter, HTTPException, Query

from backend.services.nrt_service import (
    get_nrt_metadata,
    get_nrt_field,
)


router = APIRouter(prefix="/api/nrt", tags=["NRT"])


@router.get("/metadata")
def metadata():
    try:
        return get_nrt_metadata()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load NRT metadata: {str(e)}"
        )


@router.get("/field")
def field(
    variable: str = Query("thetao"),
    depth: float = Query(0, ge=0)
):
    try:
        return get_nrt_field(
            variable=variable,
            depth=depth
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to load NRT field: {str(e)}"
        )