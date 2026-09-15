import os

from dotenv import load_dotenv
import xarray as xr

load_dotenv()

B2_2_KEY_ID = os.getenv("B2_2_KEY_ID")
B2_2_APPLICATION_KEY = os.getenv("B2_2_APPLICATION_KEY")
B2_2_BUCKET_NAME = os.getenv("B2_2_BUCKET_NAME")
B2_2_ENDPOINT = os.getenv("B2_2_ENDPOINT")
B2_2_CHLOROPHYLL_PATH = os.getenv("B2_2_CHLOROPHYLL_PATH")


def get_b2_2_storage_options():
    return {
        "key": B2_2_KEY_ID,
        "secret": B2_2_APPLICATION_KEY,
        "client_kwargs": {
            "endpoint_url": B2_2_ENDPOINT
        }
    }


def open_chlorophyll():
    chlorophyll_url = (
        f"s3://{B2_2_BUCKET_NAME}/{B2_2_CHLOROPHYLL_PATH}"
    )

    return xr.open_dataset(
        chlorophyll_url,
        engine="h5netcdf",
        backend_kwargs={
            "storage_options": get_b2_2_storage_options()
        }
    )


def get_chlorophyll_metadata():
    ds = open_chlorophyll()

    try:
        return {
            "dataset": "INCOIS Oceansat-2 OCM Chlorophyll-a",
            "variable": "CHL",
            "units": "mg/m3",
            "time_start": str(ds.time.values[0]),
            "time_end": str(ds.time.values[-1]),
            "latitude_min": float(ds.latitude.min()),
            "latitude_max": float(ds.latitude.max()),
            "longitude_min": float(ds.longitude.min()),
            "longitude_max": float(ds.longitude.max()),
        }
    finally:
        ds.close()


def get_chlorophyll_field(observation_time=None):
    ds = open_chlorophyll()

    try:
        if observation_time:
            field = ds["CHL"].sel(
                time=observation_time,
                method="nearest"
            )
        else:
            field = ds["CHL"].isel(time=0)

        field = field.load()

        step = 4

        sampled = field.isel(
            latitude=slice(None, None, step),
            longitude=slice(None, None, step)
        )

        latitudes = sampled.latitude.values
        longitudes = sampled.longitude.values
        values = sampled.values

        points = []

        for i, latitude in enumerate(latitudes):
            for j, longitude in enumerate(longitudes):
                value = values[i, j]

                if value == value:
                    points.append({
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                        "chlorophyll": float(value)
                    })

        return {
            "time": str(sampled.time.values),
            "count": len(points),
            "points": points
        }

    finally:
        ds.close()
