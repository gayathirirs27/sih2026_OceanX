from backend.services.comparison_service import (
    get_glider_observations,
    compare_glider_with_model,
)

print("Loading Glider observations...")

observations = get_glider_observations()

print(f"Total observations: {len(observations)}")

# Test 100 observations spread across the dataset
indices = [
    0,
    10000,
    50000,
    100000,
    200000,
    300000,
    400000,
    500000,
    600000,
    700000,
    800000,
    900000,
]

sample = [
    observations[i]
    for i in indices
    if i < len(observations)
]

print(f"Testing {len(sample)} spread-out observations...")

results = compare_glider_with_model(sample)

print(f"Successful comparisons: {len(results)}")

for result in results:
    print()
    print(
        result["glider_id"],
        result["observation_time"],
        "depth=", result["depth"],
        "glider_temp=", result["glider_temperature"],
        "model_temp=", result["model_temperature"],
        "temp_diff=", result["temperature_difference"],
        "glider_salinity=", result["glider_salinity"],
        "model_salinity=", result["model_salinity"],
        "salinity_diff=", result["salinity_difference"],
    )