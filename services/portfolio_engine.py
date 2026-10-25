from __future__ import annotations

from typing import Any


PROFILE_LABELS = {
    "conservative": "保守",
    "balanced": "平衡",
    "aggressive": "进取",
}
LABEL_TO_PROFILE = {label: key for key, label in PROFILE_LABELS.items()}


def suggest_profile(horizon_years: int, max_drawdown: float, btc_comfort: str) -> str:
    score = 0
    score += 0 if horizon_years <= 1 else 1 if horizon_years <= 3 else 2
    score += 0 if max_drawdown < 0.20 else 1 if max_drawdown < 0.35 else 2
    score += {"低": 0, "中": 1, "高": 2}[btc_comfort]
    if score <= 2:
        return "conservative"
    if score <= 4:
        return "balanced"
    return "aggressive"


def calculate_plan(
    profile: str,
    total_amount: float,
    current_gold: float,
    current_bitcoin: float,
    allocation: dict,
) -> dict:
    if profile not in allocation["profiles"]:
        raise ValueError("Unknown profile.")
    if min(total_amount, current_gold, current_bitcoin) < 0:
        raise ValueError("Amounts cannot be negative.")
    weights = allocation["profiles"][profile]["target_weights"]
    target_gold = total_amount * weights["gold"]
    target_bitcoin = total_amount * weights["bitcoin"]
    return {
        "profile": profile,
        "profile_label": PROFILE_LABELS[profile],
        "total_amount": total_amount,
        "gold_weight": weights["gold"],
        "bitcoin_weight": weights["bitcoin"],
        "target_gold": target_gold,
        "target_bitcoin": target_bitcoin,
        "current_gold": current_gold,
        "current_bitcoin": current_bitcoin,
        "gold_change": target_gold - current_gold,
        "bitcoin_change": target_bitcoin - current_bitcoin,
    }


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _piecewise_interpolate(score: float, values: tuple[float, float, float]) -> float:
    """Interpolate between approved conservative, balanced and aggressive anchors."""
    conservative, balanced, aggressive = values
    if score <= 20:
        return conservative
    if score <= 50:
        ratio = (score - 20) / 30
        return conservative + ratio * (balanced - conservative)
    if score <= 80:
        ratio = (score - 50) / 30
        return balanced + ratio * (aggressive - balanced)
    return aggressive


def calculate_risk_score(
    horizon_years: str | int | float,
    max_drawdown: str | float,
    liquidity_need: str,
    loss_reaction: str,
    bitcoin_acceptance: str | int | float,
) -> tuple[float, dict[str, float]]:
    """Return a continuous 0–100 score from five user-controlled inputs."""
    horizon_map = {
        "6个月以内": 0.0,
        "6个月—1年": 0.25,
        "1—3年": 0.50,
        "3—5年": 0.75,
        "5年以上": 1.0,
    }
    drawdown_map = {
        "10%以内": 0.0,
        "约20%": 0.25,
        "约30%": 0.50,
        "约40%": 0.75,
        "50%左右": 1.0,
    }
    liquidity_map = {
        "一年内很可能使用": 0.0,
        "可能使用一部分": 0.5,
        "基本不会使用": 1.0,
        # Backward-compatible values for saved sessions.
        "高": 0.0,
        "中": 0.5,
        "低": 1.0,
    }
    reaction_map = {
        "全部卖出": 0.0,
        "卖出一部分": 0.25,
        "暂时观望": 0.50,
        "继续持有": 0.75,
        "在可承受范围内增加": 1.0,
        # Backward-compatible values for saved sessions.
        "立即清仓": 0.0,
        "明显减仓": 0.3,
        "逢低增加": 1.0,
    }
    acceptance_map = {
        "完全不愿意": 0.0,
        "少量可以": 0.25,
        "可以接受一定比例": 0.50,
        "接受较高比例": 0.75,
        "充分理解风险并愿意承担": 1.0,
    }
    if liquidity_need not in liquidity_map:
        raise ValueError("Unknown liquidity need.")
    if loss_reaction not in reaction_map:
        raise ValueError("Unknown loss reaction.")

    horizon_score = (
        horizon_map[horizon_years]
        if isinstance(horizon_years, str) and horizon_years in horizon_map
        else _clamp((float(horizon_years) - 1) / 9)
    )
    drawdown_score = (
        drawdown_map[max_drawdown]
        if isinstance(max_drawdown, str) and max_drawdown in drawdown_map
        else _clamp((float(max_drawdown) - 0.10) / 0.40)
    )
    acceptance_score = (
        acceptance_map[bitcoin_acceptance]
        if isinstance(bitcoin_acceptance, str) and bitcoin_acceptance in acceptance_map
        else _clamp(float(bitcoin_acceptance) / 100)
    )

    components = {
        "投资期限": horizon_score,
        "回撤承受": drawdown_score,
        "流动性需求": liquidity_map[liquidity_need],
        "亏损反应": reaction_map[loss_reaction],
        "比特币接受度": acceptance_score,
    }
    weights = {
        "投资期限": 0.20,
        "回撤承受": 0.30,
        "流动性需求": 0.15,
        "亏损反应": 0.20,
        "比特币接受度": 0.15,
    }
    score = sum(components[name] * weights[name] for name in components) * 100
    return round(score, 2), components


def calculate_personalized_plan(
    answers: dict[str, Any],
    total_amount: float,
    current_gold: float,
    current_bitcoin: float,
    allocation: dict,
) -> dict:
    """Create a continuous recommendation bounded by the three approved Q4-M0 anchors."""
    if min(total_amount, current_gold, current_bitcoin) < 0:
        raise ValueError("Amounts cannot be negative.")

    score, components = calculate_risk_score(
        answers["horizon_years"],
        answers["max_drawdown"],
        str(answers["liquidity_need"]),
        str(answers["loss_reaction"]),
        answers["bitcoin_acceptance"],
    )
    profile_order = ("conservative", "balanced", "aggressive")
    btc_anchors = tuple(
        allocation["profiles"][name]["target_weights"]["bitcoin"] for name in profile_order
    )
    btc_weight = _piecewise_interpolate(score, btc_anchors)
    gold_weight = 1.0 - btc_weight
    profile = "conservative" if score < 35 else "balanced" if score < 65 else "aggressive"

    metric_names = ("cagr_net", "annualized_volatility", "maximum_drawdown", "daily_cvar_95_loss")
    interpolated_metrics = {}
    for metric in metric_names:
        anchors = tuple(allocation["profiles"][name]["backtest"][metric] for name in profile_order)
        interpolated_metrics[metric] = _piecewise_interpolate(score, anchors)

    target_gold = total_amount * gold_weight
    target_bitcoin = total_amount * btc_weight
    return {
        "profile": profile,
        "profile_label": PROFILE_LABELS[profile],
        "risk_score": score,
        "score_components": components,
        "total_amount": total_amount,
        "gold_weight": gold_weight,
        "bitcoin_weight": btc_weight,
        "target_gold": target_gold,
        "target_bitcoin": target_bitcoin,
        "current_gold": current_gold,
        "current_bitcoin": current_bitcoin,
        "gold_change": target_gold - current_gold,
        "bitcoin_change": target_bitcoin - current_bitcoin,
        "backtest_reference": interpolated_metrics,
        "method": allocation["selected_method"]["id"],
        "personalization_method": "五因子连续评分 + 正式锚点分段线性插值",
    }
