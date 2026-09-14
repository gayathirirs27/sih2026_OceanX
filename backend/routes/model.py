from fastapi import APIRouter, HTTPException, Query

import xarray as xr
import numpy as np

from backend.services.comparison_service import open_model

router = APIRouter(prefix="/api/model", tags=["Model"])


@router.get("/metadata")
def get_model_metadata():
    ds = None

    try:
        ds = open_model()

        return {
            "dataset": "GLORYS12V1",
            "file": "glorys/glorys_janmar2025.nc",
            "variables": [
                "thetao",
                "so",
                "uo",
                "vo"
            ],
            "dimensions": {
                "time": ds.sizes["time"],
                "depth": ds.sizes["depth"],
                "latitude": ds.sizes["latitude"],
                "longitude": ds.sizes["longitude"]
            },
            "depths": ds.depth.values.tolist(),
            "time": [
                str(t)
                for t in ds.time.values
            ],
            "bounds": {
                "min_latitude": float(ds.latitude.min()),
                "max_latitude": float(ds.latitude.max()),
                "min_longitude": float(ds.longitude.min()),
                "max_longitude": float(ds.longitude.max())
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if ds is not None:
            ds.close()


@router.get("/field")
def get_model_field(
    variable: str = Query("thetao"),
    time_index: int = Query(0, ge=0),
    depth: float = Query(0, ge=0)
):
    allowed_variables = ["thetao", "so", "uo", "vo"]

    if variable not in allowed_variables:
        raise HTTPException(
            status_code=400,
            detail=f"Variable must be one of {allowed_variables}"
        )

    ds = None

    try:
        ds = open_model()

        # Validate time index
        if time_index >= ds.sizes["time"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid time_index. Available indices: "
                    f"0-{ds.sizes['time'] - 1}"
                )
            )

        # Find nearest available model depth
        available_depths = ds.depth.values

        nearest_depth_index = int(
            np.abs(available_depths - depth).argmin()
        )

        actual_depth = float(
            available_depths[nearest_depth_index]
        )

        # Extract requested depth slice
        data = ds[variable].isel(
            time=time_index,
            depth=nearest_depth_index
        )

        # Calculate valid/missing points
        valid_mask = np.isfinite(data.values)

        valid_points = int(valid_mask.sum())
        missing_points = int((~valid_mask).sum())

        valid_values = data.values[valid_mask]

        min_value = (
            float(valid_values.min())
            if len(valid_values) > 0
            else None
        )

        max_value = (
            float(valid_values.max())
            if len(valid_values) > 0
            else None
        )

        # Convert NaN to None for JSON
        values = np.where(
            np.isfinite(data.values),
            data.values,
            None
        ).tolist()

        return {
            "variable": variable,
            "requested_depth": depth,
            "actual_depth": actual_depth,
            "depth_index": nearest_depth_index,
            "time_index": time_index,
            "time": str(ds.time.values[time_index]),
            "latitude": ds.latitude.values.tolist(),
            "longitude": ds.longitude.values.tolist(),
            "valid_points": valid_points,
            "missing_points": missing_points,
            "min_value": min_value,
            "max_value": max_value,
            "values": values
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if ds is not None:
            ds.close()