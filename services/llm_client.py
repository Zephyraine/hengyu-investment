from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from services.response_guard import validate_advisor_payload


ROOT = Path(__file__).resolve().parents[1]


def _offline_payload(plan: dict, market_state: str) -> dict:
    state_label = {
        "normal": "正常",
        "macro_stress": "宏观压力",
        "crypto_stress": "加密压力",
    }.get(market_state, market_state)
    return {
        "risk_profile": plan["profile"],
        "gold_weight": plan["gold_weight"],
        "bitcoin_weight": plan["bitcoin_weight"],
        "summary": (
            f"你的连续风险评分为{plan.get('risk_score', '—')}分，处于{plan['profile_label']}参考区间。"
            f"当前市场参考状态为{state_label}，配置比例由你的问卷回答计算，见微负责解释。"
        ),
        "reasons": [
            "配置比例根据五项个人回答，并结合历史参考方案计算，而不是由问答模型自由生成。",
            "黄金承担组合的主要稳定作用，比特币提供更高风险暴露。",
        ],
        "warnings": [
            "历史回测不保证未来表现。",
            "比特币可能发生显著波动和回撤。",
            "本工具用于竞赛研究展示，不构成个人投资建议。",
        ],
        "rebalance_message": "仅在计划检查日重新评估；候选BTC权重变化不足2个百分点时不交易。",
        "mode": "offline_demo",
    }


def generate_advice(plan: dict, context: dict) -> dict:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_API_BASE", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    if not (api_key and base_url and model):
        return _offline_payload(plan, context["market_state"])

    system_prompt = (ROOT / "prompts" / "advisor_system_prompt.md").read_text(encoding="utf-8")
    user_payload = {
        "quantitative_plan": plan,
        "market_context": context,
        "instruction": "Return only one valid JSON object matching the required schema.",
    }
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = json.loads(response.json()["choices"][0]["message"]["content"])
    valid, reason = validate_advisor_payload(payload, plan)
    if not valid:
        fallback = _offline_payload(plan, context["market_state"])
        fallback["guard_message"] = reason
        return fallback
    payload["mode"] = "api"
    return payload


def _offline_chat_answer(question: str, plan: dict, context: dict) -> str:
    """Provide a useful local answer when no compatible LLM API is configured."""
    text = question.lower()
    plan_line = (
        f"你当前的参考配置是黄金 **{plan['gold_weight']:.1%}**、比特币 "
        f"**{plan['bitcoin_weight']:.1%}**，风险评分为 **{plan['risk_score']:.1f}/100**。"
    )
    if any(term in text for term in ("配置", "方案", "比例", "黄金", "比特币", "权重", "我的")):
        return (
            f"{plan_line}\n\n这个比例来自你的投资期限、可接受回撤、流动性需求、亏损反应和比特币接受度。"
            "黄金主要承担相对稳定的部分，比特币提供更高波动的风险暴露。它是参考方案，不是收益承诺；如果你的资金需求或风险感受改变，建议先更新问卷再比较新方案。"
        )
    if any(term in text for term in ("回撤", "亏损", "风险", "波动")):
        return (
            "回撤是资产或组合从阶段高点跌到随后低点的幅度。你在问卷中填写的是自己心理和资金上能承受的程度，"
            "不是系统能够保证的亏损上限。历史回撤只能帮助理解风险，未来可能出现更大的波动。"
        )
    if any(term in text for term in ("调仓", "买", "卖", "交易")):
        return (
            f"{plan_line}\n\n当前规则建议只在计划检查日重新评估；候选比特币权重变化不足2个百分点时不交易，"
            "以减少频繁操作。实际操作前还应考虑费用、税务、流动性和你近期的资金安排。"
        )
    return (
        "我可以解释黄金与比特币配置、常见投资概念和风险。当前处于离线说明模式，因此回答会较简洁。"
        "你可以补充问题，例如“为什么黄金比例更高”或“可接受回撤是什么意思”。"
    )


def generate_chat_answer(messages: list[dict], plan: dict, context: dict) -> str:
    """Answer a multi-turn question while keeping the calculated plan read-only."""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_API_BASE", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    latest_question = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "user"),
        "",
    )
    if not (api_key and base_url and model):
        return _offline_chat_answer(latest_question, plan, context)

    system_prompt = (ROOT / "prompts" / "chat_system_prompt.md").read_text(encoding="utf-8")
    plan_context = {
        "current_plan": {
            "profile_label": plan["profile_label"],
            "risk_score": plan["risk_score"],
            "gold_weight": plan["gold_weight"],
            "bitcoin_weight": plan["bitcoin_weight"],
            "target_gold": plan["target_gold"],
            "target_bitcoin": plan["target_bitcoin"],
            "gold_change": plan["gold_change"],
            "bitcoin_change": plan["bitcoin_change"],
        },
        "questionnaire_and_market_context": context,
    }
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": json.dumps(plan_context, ensure_ascii=False)},
    ]
    api_messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in messages[-20:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    )
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0.3, "messages": api_messages},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
