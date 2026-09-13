from services.comparison_service import compare_argo_with_model
import numpy as np

print("Running full Argo ↔ GLORYS comparison...")
print("Please wait...\n")

results = compare_argo_with_model()

print("========== COMPARISON SUMMARY ==========")

print("Total matched observations:", len(results))

valid_temp = [
    r for r in results
    if r["observed_temperature"] is not None
    and r["model_temperature"] is not None
]

valid_sal = [
    r for r in results
    if r["observed_salinity"] is not None
    and r["model_salinity"] is not None
]

print("Valid temperature comparisons:", len(valid_temp))
print("Valid salinity comparisons:", len(valid_sal))

# Temperature metrics
if valid_temp:
    temp_diff = np.array([
        r["model_temperature"] - r["observed_temperature"]
        for r in valid_temp
    ])

    print("\n--- Temperature ---")
    print("Bias:", np.mean(temp_diff))
    print("MAE:", np.mean(np.abs(temp_diff)))
    print("RMSE:", np.sqrt(np.mean(temp_diff ** 2)))

# Salinity metrics
if valid_sal:
    sal_diff = np.array([
        r["model_salinity"] - r["observed_salinity"]
        for r in valid_sal
    ])

    print("\n--- Salinity ---")
    print("Bias:", np.mean(sal_diff))
    print("MAE:", np.mean(np.abs(sal_diff)))
    print("RMSE:", np.sqrt(np.mean(sal_diff ** 2)))

print("\n========================================")
print("Comparison completed successfully.")