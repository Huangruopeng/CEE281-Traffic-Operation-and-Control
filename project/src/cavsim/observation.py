"""Detector auditing, state estimation, and one-interval forecasting."""

from __future__ import annotations

from typing import Any
import math

import numpy as np
import pandas as pd


def audit_detector_counts(
    observations: pd.DataFrame,
    crossings: pd.DataFrame,
    sensor_id: str = "D1",
    sample_intervals: int = 10,
) -> pd.DataFrame:
    """Independent event-log recount for a labeled detector sample."""
    obs = observations[observations["sensor_id"] == sensor_id].head(sample_intervals).copy()
    rows: list[dict[str, Any]] = []
    for _, row in obs.iterrows():
        events = crossings[
            (crossings["sensor_id"] == sensor_id)
            & (crossings["time_s"] > row["interval_start_s"])
            & (crossings["time_s"] <= row["interval_end_s"] + 1e-9)
        ]
        event_count = int(len(events))
        rows.append({
            "sensor_id": sensor_id,
            "interval_start_s": row["interval_start_s"],
            "interval_end_s": row["interval_end_s"],
            "reported_count": int(row["count"]),
            "independent_event_log_count": event_count,
            "count_error_veh": int(row["count"]) - event_count,
            "auditor_label": "pass" if int(row["count"]) == event_count else "review",
            "audit_method": "recount unique crossing events in exact interval",
        })
    return pd.DataFrame(rows)


def _forecast_one_series(
    truth: pd.DataFrame,
    observed_counts: pd.Series,
    alpha: float,
    defect_id: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    n = len(truth)
    split = max(5, n // 2)
    state = math.nan
    history: list[float] = []
    rows: list[dict[str, Any]] = []
    for i in range(n - 1):
        x = float(observed_counts.iloc[i]) if np.isfinite(observed_counts.iloc[i]) else math.nan
        if np.isfinite(x):
            history.append(x)
            state = x if not np.isfinite(state) else alpha * x + (1.0 - alpha) * state
        baseline = float(np.mean(history[-3:])) if history else math.nan
        issue = float(truth.iloc[i]["interval_end_s"])
        target = float(truth.iloc[i + 1]["interval_end_s"])
        actual = float(truth.iloc[i + 1]["count"])
        quality = "missing_input_hold" if not np.isfinite(x) else "ok"
        for method, value in (("moving_average_3", baseline), ("exponential_smoothing", state)):
            rows.append({
                "issue_time_s": issue,
                "target_time_s": target,
                "segment_id": str(truth.iloc[i]["sensor_id"]),
                "variable_name": "interval_count",
                "units": "vehicles/30_s",
                "method": method,
                "estimated_state": state if method == "exponential_smoothing" else baseline,
                "predicted_value": value,
                "actual_withheld_truth": actual,
                "quality_indicator": quality,
                "observation_condition": defect_id,
                "evaluation_period": "development" if i + 1 < split else "evaluation",
                "absolute_error_vehicles": abs(value - actual) if np.isfinite(value) else math.nan,
            })
    detail = pd.DataFrame(rows)
    eval_rows = detail[detail["evaluation_period"] == "evaluation"]
    result = {
        "observation_condition": defect_id,
        "alpha": alpha,
        "development_intervals": split,
        "evaluation_intervals": n - split,
    }
    for method in ["moving_average_3", "exponential_smoothing"]:
        sub = eval_rows[eval_rows["method"] == method]
        result[f"{method}_mae_veh_per_interval"] = float(sub["absolute_error_vehicles"].mean())
    return detail, result


def evaluate_forecasts(observations: pd.DataFrame, sensor_id: str = "D1") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Tune smoothing on development data and score identical held-out intervals."""
    truth = observations[observations["sensor_id"] == sensor_id].sort_values("interval_end_s").reset_index(drop=True)
    if len(truth) < 10:
        raise ValueError("At least ten detector intervals are required for forecast evaluation")
    split = max(5, len(truth) // 2)
    grid = np.arange(0.1, 1.0, 0.1)
    scores = []
    for alpha in grid:
        detail, _ = _forecast_one_series(truth, truth["count"], float(alpha), "complete")
        dev = detail[(detail["method"] == "exponential_smoothing") & (detail["target_time_s"] <= truth.iloc[split - 1]["interval_end_s"])]
        scores.append((float(dev["absolute_error_vehicles"].mean()), float(alpha)))
    alpha = min(scores)[1]

    complete_detail, complete_result = _forecast_one_series(truth, truth["count"], alpha, "complete")
    defective = truth.copy()
    missing_mask = (np.arange(len(defective)) % 5 == 3)
    defective.loc[missing_mask, ["count", "mean_speed_mps", "occupancy_pct"]] = np.nan
    defective.loc[missing_mask, "quality_flag"] = "missing"
    defect_detail, defect_result = _forecast_one_series(truth, defective["count"], alpha, "every_5th_interval_missing")
    details = pd.concat([complete_detail, defect_detail], ignore_index=True)
    summary = pd.DataFrame([complete_result, defect_result])
    return details, summary, defective

