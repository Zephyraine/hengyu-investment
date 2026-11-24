from __future__ import annotations

import hashlib
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


def get_research_data_fingerprint() -> str:
    """Return a stable cache key that changes whenever packaged research data changes."""
    digest = hashlib.sha256()
    for path in sorted(item for item in DATA_ROOT.rglob("*") if item.is_file()):
        digest.update(path.relative_to(DATA_ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()

SCENARIOS = {
    "情景A｜尾部风险优先": {"profile": "保守", "theta": 0.0, "btc_cap": 0.15, "short": "A"},
    "情景B｜收益风险权衡": {"profile": "均衡", "theta": 0.6, "btc_cap": 0.35, "short": "B"},
    "情景C｜收益偏好增强": {"profile": "进取", "theta": 1.5, "btc_cap": 0.60, "short": "C"},
}

PREFERENCE_OPTIONS = {
    "horizon": {
        "6个月以内": 0.0,
        "6个月—1年": 0.25,
        "1—3年": 0.50,
        "3—5年": 0.75,
        "5年以上": 1.0,
    },
    "drawdown": {
        "10%以内": 0.0,
        "约20%": 0.25,
        "约30%": 0.50,
        "约40%": 0.75,
        "50%左右": 1.0,
    },
    "liquidity": {
        "一年内很可能使用": 0.0,
        "可能使用一部分": 0.50,
        "基本不会使用": 1.0,
    },
    "loss_reaction": {
        "全部卖出": 0.0,
        "卖出一部分": 0.25,
        "暂时观望": 0.50,
        "继续持有": 0.75,
        "在可承受范围内增加": 1.0,
    },
    "bitcoin_acceptance": {
        "完全不愿意": 0.0,
        "少量可以": 0.25,
        "可以接受一定比例": 0.50,
        "接受较高比例": 0.75,
        "充分理解风险并愿意承担": 1.0,
    },
}

PREFERENCE_WEIGHTS = {
    "horizon": 0.20,
    "drawdown": 0.30,
    "liquidity": 0.15,
    "loss_reaction": 0.20,
    "bitcoin_acceptance": 0.15,
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
    targets = data.get("targets", {}).get(strategy, pd.DataFrame())
    if targets.empty:
        return targets.copy()
    return targets.loc[targets["profile_label"] == meta["profile"]].copy()


def get_latest_target(data: dict, scenario_name: str, strategy: str = "GOLD_BTC") -> dict | None:
    history = get_target_history(data, scenario_name, strategy)
    if history.empty:
        return None
    return history.sort_values("date").iloc[-1].to_dict()


def calculate_preference_score(answers: dict[str, str]) -> tuple[float, dict[str, float]]:
    components: dict[str, float] = {}
    for key, weight in PREFERENCE_WEIGHTS.items():
        value = answers.get(key)
        if value not in PREFERENCE_OPTIONS[key]:
            raise ValueError(f"Unknown preference answer: {key}")
        components[key] = PREFERENCE_OPTIONS[key][value]
    score = sum(components[key] * PREFERENCE_WEIGHTS[key] for key in components) * 100
    return round(score, 2), components


def _interpolate_three(score: float, values: tuple[float, float, float]) -> float:
    if not 0 <= score <= 100:
        raise ValueError("Preference score must be between 0 and 100.")
    low, middle, high = values
    if score <= 50:
        return low + (score / 50) * (middle - low)
    return middle + ((score - 50) / 50) * (high - middle)


def get_personalized_allocation(data: dict, score: float) -> dict:
    scenario_names = list(SCENARIOS)
    latest = [get_latest_target(data, name) for name in scenario_names]
    if any(item is None for item in latest):
        raise ValueError("All three dual-asset target anchors are required.")
    theta = _interpolate_three(score, tuple(SCENARIOS[name]["theta"] for name in scenario_names))
    btc_cap = _interpolate_three(score, tuple(SCENARIOS[name]["btc_cap"] for name in scenario_names))
    bitcoin = _interpolate_three(score, tuple(float(item["BTC"]) for item in latest if item))
    metrics = {}
    for field in ("cagr", "annual_volatility", "maximum_drawdown", "daily_cvar95_loss"):
        anchors = tuple(float(get_strategy_metrics(data, name)[field]) for name in scenario_names)
        metrics[field] = _interpolate_three(score, anchors)
    return {
        "score": score,
        "theta": theta,
        "btc_cap": btc_cap,
        "GOLD": 1 - bitcoin,
        "BTC": bitcoin,
        "date": latest[0]["date"],
        "signal_date": latest[0]["signal_date"],
        "reference_metrics": metrics,
    }


def get_personalized_target_history(data: dict, score: float) -> pd.DataFrame:
    histories = [get_target_history(data, name).sort_values("date").reset_index(drop=True) for name in SCENARIOS]
    if any(len(frame) != 48 for frame in histories):
        raise ValueError("All three dual-asset target histories are required.")
    if not all(histories[0]["date"].equals(frame["date"]) for frame in histories[1:]):
        raise ValueError("Dual-asset target dates are not aligned.")
    bitcoin = [
        _interpolate_three(score, tuple(float(frame.loc[index, "BTC"]) for frame in histories))
        for index in range(len(histories[0]))
    ]
    return pd.DataFrame(
        {
            "date": histories[0]["date"],
            "signal_date": histories[0]["signal_date"],
            "GOLD": [1 - value for value in bitcoin],
            "BTC": bitcoin,
        }
    )

