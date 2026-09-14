import xarray as xr
from pathlib import Path


MODEL_FILE = Path(
    "data/raw/glider_model/glorys_glider_bob_20160701_20160714.nc"
)


print("=" * 70)
print("GLORYS GLIDER MODEL VERIFICATION")
print("=" * 70)

print(f"\nFile: {MODEL_FILE}")
print(f"Exists: {MODEL_FILE.exists()}")

if not MODEL_FILE.exists():
    raise FileNotFoundError(
        f"Model file not found: {MODEL_FILE}"
    )


# --------------------------------------------------
# Open NetCDF
# --------------------------------------------------

ds = xr.open_dataset(MODEL_FILE)

print("\nDataset:")
print(ds)


# --------------------------------------------------
# Dimensions
# --------------------------------------------------

print("\n" + "=" * 70)
print("DIMENSIONS")
print("=" * 70)

for name, size in ds.sizes.items():
    print(f"{name}: {size}")


# --------------------------------------------------
# Coordinates
# --------------------------------------------------

print("\n" + "=" * 70)
print("COORDINATES")
print("=" * 70)

for coord in ["time", "depth", "latitude", "longitude"]:
    if coord in ds.coords:
        values = ds[coord].values

        print(f"\n{coord}:")
        print(f"  first: {values[0]}")
        print(f"  last : {values[-1]}")
        print(f"  count: {len(values)}")


# --------------------------------------------------
# Variables
# --------------------------------------------------

print("\n" + "=" * 70)
print("DATA VARIABLES")
print("=" * 70)

for variable in ds.data_vars:
    print(
        f"{variable}: "
        f"dims={ds[variable].dims}, "
        f"shape={ds[variable].shape}"
    )


# --------------------------------------------------
# Geographic bounds
# --------------------------------------------------

print("\n" + "=" * 70)
print("GEOGRAPHIC BOUNDS")
print("=" * 70)

print(
    "Latitude :",
    float(ds.latitude.min()),
    "to",
    float(ds.latitude.max())
)

print(
    "Longitude:",
    float(ds.longitude.min()),
    "to",
    float(ds.longitude.max())
)


# --------------------------------------------------
# Depth
# --------------------------------------------------

print("\n" + "=" * 70)
print("DEPTH")
print("=" * 70)

print(
    "Depth:",
    float(ds.depth.min()),
    "to",
    float(ds.depth.max()),
    "m"
)


# --------------------------------------------------
# Time
# --------------------------------------------------

print("\n" + "=" * 70)
print("TIME")
print("=" * 70)

print("First model time:", ds.time.values[0])
print("Last model time :", ds.time.values[-1])


# --------------------------------------------------
# Basic statistics
# --------------------------------------------------

print("\n" + "=" * 70)
print("BASIC VARIABLE CHECK")
print("=" * 70)

for variable in ["thetao", "so"]:

    data = ds[variable]

    print(f"\n{variable}")

    print("  min:", float(data.min(skipna=True)))
    print("  max:", float(data.max(skipna=True)))
    print("  mean:", float(data.mean(skipna=True)))

    total = data.size
    missing = int(data.isnull().sum())

    print("  total cells:", total)
    print("  missing cells:", missing)
    print(
        "  valid cells:",
        total - missing
    )


# --------------------------------------------------
# Metadata
# --------------------------------------------------

print("\n" + "=" * 70)
print("IMPORTANT ATTRIBUTES")
print("=" * 70)

for key, value in ds.attrs.items():
    print(f"{key}: {value}")


ds.close()

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)