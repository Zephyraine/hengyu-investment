from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "app"


def _read_json(name: str) -> dict:
    with (DATA_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(name: str, date_columns: tuple[str, ...] = ("date",)) -> pd.DataFrame:
    frame = pd.read_csv(DATA_DIR / name)
    for column in date_columns:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column])
    return frame


def load_dashboard_data() -> dict:
    frozen = _read_json("frozen_numbers.json")
    allocation = _read_json("final_allocation.json")
    if frozen.get("status") != "frozen":
        raise ValueError("The dashboard requires a formally frozen result package.")
    if allocation["selected_method"]["id"] != frozen["Q4"]["selected_method_id"]:
        raise ValueError("Allocation method does not match frozen results.")

    profiles = allocation["profiles"]
    for name, profile in profiles.items():
        total = sum(profile["target_weights"].values())
        if abs(total - 1.0) > 1e-10:
            raise ValueError(f"Target weights for {name} do not sum to one.")

    return {
        "frozen": frozen,
        "allocation": allocation,
        "market": _read_csv("gold_btc_daily.csv"),
        "q1_rolling": _read_csv("q1_rolling_metrics.csv"),
        "q1_summary": _read_csv("q1_rolling_summary.csv", ()),
        "q2_summary": _read_csv("q2_rolling_summary.csv", ()),
        "q3_states": _read_csv("q3_state_labels.csv"),
        "q3_metrics": _read_csv("q3_state_conditional_metrics.csv", ()),
        "q3_events": _read_csv("q3_event_group_summary.csv", ()),
        "q4_performance": _read_csv("q4_performance.csv", ()),
        "q4_paths": _read_csv("q4_daily_paths.csv"),
    }
