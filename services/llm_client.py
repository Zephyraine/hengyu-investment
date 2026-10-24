from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.response_guard import validate_advisor_payload


ROOT = Path(__file__).resolve().parents[1]


def _read_setting(name: str, default: str = "") -> str:
    """Read deployment settings from env first, then Streamlit Cloud secrets."""
    env_value = os.getenv(name, "").strip()
    if env_value:
        return env_value
    try:
        import streamlit as st

        value: Any = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value).strip() if value is not None else default


def get_llm_config() -> dict[str, str]:
    return {
        "api_key": _read_setting("LLM_API_KEY"),
        "base_url": _read_setting("LLM_API_BASE").rstrip("/"),
        "model": _read_setting("LLM_MODEL"),
        "api_path": _read_setting("LLM_API_PATH", "/chat/completions"),
    }


def is_llm_configured(config: dict[str, str] | None = None) -> bool:
    config = config or get_llm_config()
    return bool(config["api_key"] and config["base_url"] and config["model"])


def _chat_endpoint(base_url: str, api_path: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LLM_API_BASE 必须是有效的 http(s) 地址。")
    if base_url.endswith("/chat/completions"):
        return base_url
    path = api_path.strip() or "/chat/completions"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"


def _session() -> requests.Session:
    retry = Retry(
        total=1,
        connect=0,
        read=0,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    # Avoid leaking a developer machine's localhost proxy into production calls.
    session.trust_env = _read_setting("LLM_TRUST_ENV_PROXY", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    return session


def _post_chat(config: dict[str, str], payload: dict) -> dict:
    endpoint = _chat_endpoint(config["base_url"], config["api_path"])
    with _session() as session:
        response = session.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            # Keep the public demo responsive when a configured provider has
            # expired or is unreachable. The caller falls back to local copy.
            timeout=(3, 6),
        )
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict) or not body.get("choices"):
        raise ValueError("在线模型返回格式不完整。")
    return body


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
            f"风险评分{plan.get('risk_score', '—')}分，属于{plan['profile_label']}区间。"
            f"当前市场状态：{state_label}。"
        ),
        "reasons": [
            "比例根据五项回答和历史方案计算。",
            "黄金偏稳定，比特币波动更高。",
        ],
        "warnings": [
            "历史回测不保证未来表现。",
            "比特币可能发生显著波动和回撤。",
            "本工具用于竞赛研究展示，不构成个人投资建议。",
        ],
        "rebalance_message": "按计划复查；比特币权重变化不足2个百分点时不交易。",
        "mode": "offline_demo",
    }


def generate_advice(plan: dict, context: dict) -> dict:
    config = get_llm_config()
    if not is_llm_configured(config):
        return _offline_payload(plan, context["market_state"])

    system_prompt = (ROOT / "prompts" / "advisor_system_prompt.md").read_text(encoding="utf-8")
    user_payload = {
        "quantitative_plan": plan,
        "market_context": context,
        "instruction": "Return only one valid JSON object matching the required schema.",
    }
    request_payload = {
        "model": config["model"],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }
    try:
        try:
            body = _post_chat(config, request_payload)
        except requests.HTTPError as exc:
            # Some OpenAI-compatible gateways do not implement response_format.
            status = exc.response.status_code if exc.response is not None else None
            if status not in {400, 404, 422}:
                raise
            compatible_payload = dict(request_payload)
            compatible_payload.pop("response_format", None)
            body = _post_chat(config, compatible_payload)
        payload = json.loads(body["choices"][0]["message"]["content"])
    except (requests.RequestException, ValueError, KeyError, TypeError, json.JSONDecodeError):
        fallback = _offline_payload(plan, context["market_state"])
        fallback["mode"] = "offline_fallback"
        fallback["guard_message"] = "在线解释暂不可用，已自动切换为本地说明。"
        return fallback
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
            f"{plan_line}\n\n比例来自五项问卷回答。黄金偏稳定，比特币波动更高；情况变化时可重新填写问卷。"
        )
    if any(term in text for term in ("回撤", "亏损", "风险", "波动")):
        return (
            "回撤是资产或组合从阶段高点下跌的幅度。问卷中的数值代表你的承受程度，不是系统能够保证的亏损上限。"
        )
    if any(term in text for term in ("调仓", "买", "卖", "交易")):
        return (
            f"{plan_line}\n\n按计划复查；比特币权重变化不足2个百分点时不交易。操作前考虑费用和资金安排。"
        )
    return (
        "我可以回答黄金与比特币配置、投资概念和风险。请把问题说得更具体一些。"
    )


def generate_chat_answer(messages: list[dict], plan: dict, context: dict) -> str:
    """Answer a multi-turn question while keeping the calculated plan read-only."""
    config = get_llm_config()
    latest_question = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "user"),
        "",
    )
    if not is_llm_configured(config):
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
    try:
        body = _post_chat(
            config,
            {"model": config["model"], "temperature": 0.3, "messages": api_messages},
        )
        return body["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return "在线问答暂不可用，已切换为本地说明。\n\n" + _offline_chat_answer(
            latest_question, plan, context
        )

