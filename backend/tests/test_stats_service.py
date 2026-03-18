from __future__ import annotations

import pytest

from app.services.stats_service import compare_groups, descriptive_stats, detect_outliers, trend_analysis


def test_descriptive_stats_reports_core_metrics() -> None:
    stats = descriptive_stats([1, 2, 3, 4])

    assert stats["count"] == 4
    assert stats["mean"] == pytest.approx(2.5)
    assert stats["std"] == pytest.approx(1.2909944487)
    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
    assert stats["median"] == 2.5


def test_compare_groups_uses_welch_t_test() -> None:
    result = compare_groups([10, 12, 14], [20, 22, 24], label_a="low", label_b="high")

    assert result["low"]["mean"] == pytest.approx(12.0)
    assert result["high"]["mean"] == pytest.approx(22.0)
    assert result["significant_difference"] is True
    assert "low" in result["interpretation"]


def test_trend_analysis_detects_increasing_series() -> None:
    result = trend_analysis([1, 2, 3, 4])

    assert result["direction"] == "increasing"
    assert result["slope"] > 0
    assert result["r_squared"] == pytest.approx(1.0)


def test_detect_outliers_finds_extremes() -> None:
    result = detect_outliers([1, 1, 2, 2, 3, 100])

    assert result["count"] == 1
    assert result["values"] == [100]
    assert result["indices"] == [5]
