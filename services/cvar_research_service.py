from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "cvar_20261124"

TARGET_GROUPS = {
    "GOLD_BTC": ("dual_targets", "dual", "CASH"),
    "GOLD_BTC_CASH": ("cash_targets", "cash", "CASH"),
    "GOLD_BTC_STABLE": ("stable_targets", "stable", "STABLE"),
}

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
    targets = {
        strategy: _load_target_group(folder, model, third_asset)
        for strategy, (folder, model, third_asset) in TARGET_GROUPS.items()
    }
    return {
        "metrics": metrics,
        "methodology": methodology,
        "stablecoin_sources": stablecoin_sources,
        "targets": targets,
        "version": "2026-11-24",
        "sample_start": "2022-02-17",
        "sample_end": "2026-01-29",
        "data_status": "研究性原型",
    }


def _load_target_group(folder: str, expected_model: str, third_asset: str) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in sorted((DATA_ROOT / folder).glob("*.csv")):
        frame = pd.read_csv(path, parse_dates=["date", "signal_date"])
        required = {"date", "signal_date", "model", "profile", "GOLD", "BTC", third_asset, "fee"}
        if set(frame.columns) != required or len(frame) != 48:
            raise ValueError(f"Invalid target contract: {path.name}")
        if set(frame["model"]) != {expected_model} or frame["date"].duplicated().any():
            raise ValueError(f"Invalid target identity: {path.name}")
        weight_sum = frame[["GOLD", "BTC", third_asset]].sum(axis=1)
        if (weight_sum.sub(1).abs() > 1e-9).any():
            raise ValueError(f"Target weights do not sum to one: {path.name}")
        frame["profile_label"] = path.stem
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


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


def get_target_history(data: dict, scenario_name: str, strategy: str = "GOLD_BTC") -> pd.DataFrame:
    meta = get_scenario_meta(scenario_name)
    targets = data["targets"].get(strategy, pd.DataFrame())
    if targets.empty:
        return targets.copy()
    return targets.loc[targets["profile_label"] == meta["profile"]].copy()


def get_latest_target(data: dict, scenario_name: str, strategy: str = "GOLD_BTC") -> dict | None:
    history = get_target_history(data, scenario_name, strategy)
    if history.empty:
        return None
    return history.sort_values("date").iloc[-1].to_dict()

