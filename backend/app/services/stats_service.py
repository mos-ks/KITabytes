"""Statistical analysis service for materials testing data."""

import numpy as np
from scipy import stats as scipy_stats
from typing import Optional


def descriptive_stats(values: list[float]) -> dict:
    """Compute descriptive statistics for a list of values."""
    arr = np.array(values)
    return {
        "count": len(arr),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "median": float(np.median(arr)),
        "q25": float(np.percentile(arr, 25)),
        "q75": float(np.percentile(arr, 75)),
    }


def compare_groups(group_a: list[float], group_b: list[float], label_a: str = "A", label_b: str = "B") -> dict:
    """Compare two groups using t-test and descriptive stats."""
    stats_a = descriptive_stats(group_a)
    stats_b = descriptive_stats(group_b)

    # Welch's t-test (does not assume equal variance)
    t_stat, p_value = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

    significant = bool(p_value < 0.05)

    return {
        label_a: stats_a,
        label_b: stats_b,
        "t_statistic": float(t_stat),
        "p_value": float(p_value),
        "significant_difference": significant,
        "interpretation": (
            f"The difference between {label_a} and {label_b} is "
            f"{'statistically significant' if significant else 'not statistically significant'} "
            f"(p={p_value:.4f})."
        ),
    }


def trend_analysis(values: list[float], timestamps: Optional[list[float]] = None) -> dict:
    """Analyze trend in a series of values using linear regression."""
    n = len(values)
    if n < 3:
        return {"error": "Need at least 3 data points for trend analysis"}

    x = np.array(timestamps) if timestamps else np.arange(n, dtype=float)
    y = np.array(values)

    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

    if p_value < 0.05:
        if slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
    else:
        direction = "no significant trend"

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_value ** 2),
        "p_value": float(p_value),
        "std_err": float(std_err),
        "direction": direction,
        "interpretation": (
            f"Linear regression shows a {direction} trend "
            f"(slope={slope:.6f}, R²={r_value**2:.4f}, p={p_value:.4f})."
        ),
    }


def detect_outliers(values: list[float], method: str = "iqr") -> dict:
    """Detect outliers using IQR method."""
    arr = np.array(values)
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outlier_mask = (arr < lower) | (arr > upper)
    outlier_indices = np.where(outlier_mask)[0].tolist()
    outlier_values = arr[outlier_mask].tolist()

    return {
        "count": len(outlier_values),
        "indices": outlier_indices,
        "values": outlier_values,
        "lower_bound": float(lower),
        "upper_bound": float(upper),
        "interpretation": (
            f"Found {len(outlier_values)} outlier(s) outside the range "
            f"[{lower:.4f}, {upper:.4f}] using IQR method."
        ),
    }
