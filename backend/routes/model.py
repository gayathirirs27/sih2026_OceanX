from fastapi import APIRouter, HTTPException, Query
import os
import numpy as np
import xarray as xr
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/model", tags=["Model"])


# ============================================================
# BACKBLAZE B2 ACCOUNT 1 CONFIGURATION
# ============================================================

B2_1_KEY_ID = os.getenv("B2_1_KEY_ID")
B2_1_APPLICATION_KEY = os.getenv("B2_1_APPLICATION_KEY")
B2_1_BUCKET_NAME = os.getenv("B2_1_BUCKET_NAME")
B2_1_ENDPOINT = os.getenv("B2_1_ENDPOINT")
B2_1_MODEL_PATH = os.getenv("B2_1_MODEL_PATH")


def get_b2_storage_options():
    return {
        "key": B2_1_KEY_ID,
        "secret": B2_1_APPLICATION_KEY,
        "client_kwargs": {
            "endpoint_url": B2_1_ENDPOINT
        }
    }


def open_model():
    """
    Open the GLORYS model stored in Backblaze B2 Account 1.

    The NetCDF is opened remotely. xarray reads only the
    requested data when a field is selected.
    """

    if not B2_1_BUCKET_NAME:
        raise RuntimeError("B2_1_BUCKET_NAME is not configured")

    if not B2_1_MODEL_PATH:
        raise RuntimeError("B2_1_MODEL_PATH is not configured")

    model_url = f"s3://{B2_1_BUCKET_NAME}/{B2_1_MODEL_PATH}"

    return xr.open_dataset(
        model_url,
        engine="h5netcdf",
        backend_kwargs={
            "storage_options": get_b2_storage_options()
        }
    )


# ============================================================
# MODEL METADATA
# ============================================================

@router.get("/metadata")
def get_model_metadata():
    """
    Return metadata required by the frontend for the 3D model
    visualization.

    This endpoint does NOT open/download the large NetCDF file.
    """

    return {
        "dataset": "GLORYS12V1",

        "file": "glorys/oceanx_model_fields_2025.nc",

        "variables": [
            "thetao",
            "so",
            "uo",
            "vo"
        ],

        "variable_descriptions": {
            "thetao": "Sea water potential temperature",
            "so": "Sea water salinity",
            "uo": "Eastward sea water velocity",
            "vo": "Northward sea water velocity"
        },

        "dimensions": {
            "time": 90,
            "depth": 31,
            "latitude": 241,
            "longitude": 241
        },

        "depths": [
            0.49402499198913574,
            1.5413750410079956,
            2.6456689834594727,
            3.8194949626922607,
            5.078224182128906,
            6.440614223480225,
            7.92956018447876,
            9.572997093200684,
            11.404999732971191,
            13.467140197753906,
            15.810070037841797,
            18.495559692382812,
            21.598819732666016,
            25.211410522460938,
            29.444730758666992,
            34.43415069580078,
            40.344051361083984,
            47.37369155883789,
            55.76428985595703,
            65.80726623535156,
            77.85385131835938,
            92.3260726928711,
            109.72930145263672,
            130.66600036621094,
            155.85069274902344,
            186.12559509277344,
            222.47520446777344,
            266.0403137207031,
            318.1274108886719,
            380.2130126953125,
            453.9377136230469
        ],

        "time_start": "2025-01-01T00:00:00",

        "time_end": "2025-03-31T00:00:00",

        "bounds": {
            "min_latitude": 5.0,
            "max_latitude": 25.0,
            "min_longitude": 80.0,
            "max_longitude": 100.0
        }
    }


# ============================================================
# MODEL FIELD
# ============================================================

@router.get("/field")
def get_model_field(
    variable: str = Query(
        "thetao",
        description="Model variable: thetao, so, uo or vo"
    ),

    time_index: int = Query(
        0,
        ge=0,
        description="Time index from 0 to 89"
    ),

    depth: float = Query(
        0,
        ge=0,
        description="Requested depth in metres"
    )
):
    """
    Return a single 2D model field for the requested
    time and nearest available depth.

    The frontend can use this endpoint for the 3D visualization,
    depth slider and time slider.
    """

    allowed_variables = [
        "thetao",
        "so",
        "uo",
        "vo"
    ]

    if variable not in allowed_variables:
        raise HTTPException(
            status_code=400,
            detail=f"Variable must be one of {allowed_variables}"
        )

    ds = None

    try:
        # Open the model from Backblaze B2 Account 1
        ds = open_model()

        # ----------------------------------------------------
        # Validate time
        # ----------------------------------------------------

        if time_index >= ds.sizes["time"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid time_index. "
                    f"Available indices: 0-{ds.sizes['time'] - 1}"
                )
            )

        # ----------------------------------------------------
        # Find nearest available depth
        # ----------------------------------------------------

        available_depths = ds.depth.values

        nearest_depth_index = int(
            np.abs(available_depths - depth).argmin()
        )

        actual_depth = float(
            available_depths[nearest_depth_index]
        )

        # ----------------------------------------------------
        # Select ONLY the requested 2D field
        # ----------------------------------------------------

        data = ds[variable].isel(
            time=time_index,
            depth=nearest_depth_index
        )

        # Load only this selected field
        data_values = data.values

        # ----------------------------------------------------
        # Handle missing values
        # ----------------------------------------------------

        valid_mask = np.isfinite(data_values)

        valid_points = int(valid_mask.sum())

        missing_points = int(
            (~valid_mask).sum()
        )

        valid_values = data_values[valid_mask]

        if len(valid_values) > 0:
            min_value = float(valid_values.min())
            max_value = float(valid_values.max())
        else:
            min_value = None
            max_value = None

        # Convert NaN to null for JSON
        values = np.where(
            np.isfinite(data_values),
            data_values,
            None
        ).tolist()

        # ----------------------------------------------------
        # Response for frontend
        # ----------------------------------------------------

        return {
            "variable": variable,

            "requested_depth": depth,

            "actual_depth": actual_depth,

            "depth_index": nearest_depth_index,

            "time_index": time_index,

            "time": str(
                ds.time.values[time_index]
            ),

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
            detail=f"Unable to load model field: {str(e)}"
        )

    finally:
        if ds is not None:
            ds.close()