from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "cvar_20261124"

SCENARIOS = {
    "情景A｜尾部风险优先": {"profile": "保守", "theta": 0.0, "btc_cap": 0.15, "short": "A"},
    "情景B｜收益风险权衡": {"profile": "均衡", "theta": 0.6, "btc_cap": 0.35, "short": "B"},
    "情景C｜收益偏好增强": {"profile": "进取", "theta": 1.5, "btc_cap": 0.60, "short": "C"},
}


def load_cvar_research_data() -> dict:
    metrics = pd.read_csv(DATA_ROOT / "three_arm_prototype_metrics.csv")
    expected_strategies = {"GOLD_BTC", "GOLD_BTC_CASH", "GOLD_BTC_STABLE"}
    if set(metrics["strategy"]) != expected_strategies or len(metrics) != 9:
        raise ValueError("The 2026-11-24 research metrics contract is invalid.")
    methodology = json.loads((DATA_ROOT / "three_arm_methodology.json").read_text(encoding="utf-8"))
    stablecoin_sources = pd.read_csv(DATA_ROOT / "stablecoin_source_summary.csv")
    return {
        "metrics": metrics,
        "methodology": methodology,
        "stablecoin_sources": stablecoin_sources,
        "version": "2026-11-24",
        "sample_start": "2022-02-17",
        "sample_end": "2026-01-29",
        "data_status": "研究性原型",
    }


def get_scenario_meta(scenario_name: str) -> dict:
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown research scenario: {scenario_name}")
    return {"name": scenario_name, **SCENARIOS[scenario_name]}


def get_strategy_metrics(data: dict, scenario_name: str, strategy: str = "GOLD_BTC") -> dict:
    meta = get_scenario_meta(scenario_name)
    profile = meta["profile"]
    rows = data["metrics"].query("strategy == @strategy and profile == @profile")
    if len(rows) != 1:
        raise ValueError(f"Missing metrics for {strategy}/{meta['profile']}")
    return {**rows.iloc[0].to_dict(), **meta}


def get_three_arm_metrics(data: dict, scenario_name: str) -> pd.DataFrame:
    meta = get_scenario_meta(scenario_name)
    profile = meta["profile"]
    comparison = data["metrics"].query("profile == @profile").copy()
    comparison["label"] = comparison["strategy"].map(
        {
            "GOLD_BTC": "黄金＋BTC",
            "GOLD_BTC_CASH": "＋零收益现金",
            "GOLD_BTC_STABLE": "＋稳定币篮子",
        }
    )
    return comparison

