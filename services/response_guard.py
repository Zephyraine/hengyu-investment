from __future__ import annotations


FORBIDDEN_PHRASES = ("保证收益", "稳赚", "必然上涨", "无风险")


def validate_advisor_payload(payload: dict, plan: dict) -> tuple[bool, str]:
    required = {
        "risk_profile",
        "gold_weight",
        "bitcoin_weight",
        "summary",
        "reasons",
        "warnings",
        "rebalance_message",
    }
    missing = required - payload.keys()
    if missing:
        return False, f"缺少字段：{', '.join(sorted(missing))}"
    if payload["risk_profile"] != plan["profile"]:
        return False, "模型返回的风险档位与量化引擎不一致。"
    if abs(float(payload["gold_weight"]) - plan["gold_weight"]) > 1e-6:
        return False, "模型试图修改黄金权重。"
    if abs(float(payload["bitcoin_weight"]) - plan["bitcoin_weight"]) > 1e-6:
        return False, "模型试图修改比特币权重。"
    combined = " ".join(
        [str(payload["summary"]), *map(str, payload["reasons"]), *map(str, payload["warnings"])]
    )
    if any(phrase in combined for phrase in FORBIDDEN_PHRASES):
        return False, "模型回答包含禁止的收益承诺。"
    return True, "PASS"
