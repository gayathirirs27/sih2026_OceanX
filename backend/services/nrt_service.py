import os

import xarray as xr
from dotenv import load_dotenv

load_dotenv()

B2_2_KEY_ID = os.getenv("B2_2_KEY_ID")
B2_2_APPLICATION_KEY = os.getenv("B2_2_APPLICATION_KEY")
B2_2_BUCKET_NAME = os.getenv("B2_2_BUCKET_NAME")
B2_2_ENDPOINT = os.getenv("B2_2_ENDPOINT")

NRT_CURRENTS_PATH = "nrt_currents_2026-09-15.nc"
NRT_SALINITY_PATH = "nrt_salinity_2026-09-15.nc"
NRT_TEMP_PATH = "nrt_temp_2026-09-15.nc"


def get_b2_2_storage_options():
    return {
        "key": B2_2_KEY_ID,
        "secret": B2_2_APPLICATION_KEY,
        "client_kwargs": {
            "endpoint_url": B2_2_ENDPOINT
        }
    }


def open_nrt_file(path):
    url = f"s3://{B2_2_BUCKET_NAME}/{path}"

    return xr.open_dataset(
        url,
        engine="h5netcdf",
        backend_kwargs={
            "storage_options": get_b2_2_storage_options()
        }
    )


def get_nrt_metadata():
    datasets = {
        "currents": open_nrt_file(NRT_CURRENTS_PATH),
        "salinity": open_nrt_file(NRT_SALINITY_PATH),
        "temperature": open_nrt_file(NRT_TEMP_PATH),
    }

    try:
        ds = datasets["temperature"]

        return {
            "dataset": "Copernicus Marine NRT",
            "time": str(ds.time.values[0]),
            "depths": ds.depth.values.tolist(),
            "latitude": ds.latitude.values.tolist(),
            "longitude": ds.longitude.values.tolist(),
            "bounds": {
                "min_latitude": float(ds.latitude.min()),
                "max_latitude": float(ds.latitude.max()),
                "min_longitude": float(ds.longitude.min()),
                "max_longitude": float(ds.longitude.max()),
            },
            "variables": {
                "currents": ["uo", "vo"],
                "salinity": ["so"],
                "temperature": ["thetao"],
            }
        }

    finally:
        for ds in datasets.values():
            ds.close()

def get_nrt_field(variable="thetao", depth=0):
    variable_files = {
        "thetao": NRT_TEMP_PATH,
        "so": NRT_SALINITY_PATH,
        "uo": NRT_CURRENTS_PATH,
        "vo": NRT_CURRENTS_PATH,
    }

    if variable not in variable_files:
        raise ValueError(
            "Variable must be one of: thetao, so, uo, vo"
        )

    ds = open_nrt_file(variable_files[variable])

    try:
        available_depths = ds.depth.values

        nearest_depth_index = int(
            abs(available_depths - depth).argmin()
        )

        actual_depth = float(
            available_depths[nearest_depth_index]
        )

        data = ds[variable].isel(
            time=0,
            depth=nearest_depth_index
        )

        data = data.load()

        values = data.values

        valid_mask = values == values

        valid_points = int(valid_mask.sum())
        missing_points = int((~valid_mask).sum())

        valid_values = values[valid_mask]

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

        output_values = [
        [
            None if value != value else float(value)
            for value in row
        ]
        for row in values
        ]

        return {
            "variable": variable,
            "requested_depth": depth,
            "actual_depth": actual_depth,
            "depth_index": nearest_depth_index,
            "time": str(ds.time.values[0]),
            "latitude": ds.latitude.values.tolist(),
            "longitude": ds.longitude.values.tolist(),
            "valid_points": valid_points,
            "missing_points": missing_points,
            "min_value": min_value,
            "max_value": max_value,
            "values": output_values,
        }

    finally:
        ds.close()