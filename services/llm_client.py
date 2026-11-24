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
            # Long-form financial explanations can take longer than a short
            # chat reply. Keep connection failures fast, while allowing the
            # provider enough time to finish a useful answer before fallback.
            timeout=(5, 45),
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
    if any(term in text for term in ("稳定币", "usdt", "usdc", "dai", "现金层", "三资产")):
        return (
            "**直接结论**\n\n三资产研究把稳定币视为资金层工具，而不是与黄金、比特币同质的第三只风险资产。"
            "在均衡档现金对照中，稳定币层与零收益现金层的净年化收益、波动和最大回撤几乎重合；"
            "现有证据不足以证明稳定币具有独立的风险收益优势。\n\n"
            "**与你当前方案的关系**\n\n"
            f"{plan_line} 当前个性化权重仍由已冻结的黄金—比特币引擎计算，稳定币研究不会自动改写它。\n\n"
            "**主要限制**\n\nDAI部分日期存在数据源冲突，现金是假设零收益的理论控制变量，且稳定币与现金的微小差异尚未做显著性或等价性检验。"
        )
    if any(term in text for term in ("配置", "方案", "比例", "黄金", "比特币", "权重", "我的")):
        return (
            f"**直接结论**\n\n{plan_line}\n\n"
            "**为什么这样配**\n\n比例来自投资期限、可接受回撤、流动性需求、亏损反应和比特币接受度。黄金承担相对稳定的部分，比特币提供更高波动的风险暴露。\n\n"
            "**主要风险**\n\n历史表现不代表未来结果，比特币可能出现显著波动和回撤。\n\n"
            "**下一步**\n\n资金需求或风险感受变化时，重新填写问卷并比较新方案。"
        )
    if any(term in text for term in ("回撤", "亏损", "风险", "波动")):
        return (
            "回撤是资产或组合从阶段高点下跌的幅度。例如从100元跌到80元，回撤就是20%。"
            "问卷中的数值表示你在资金和心理上愿意承受的程度，不是系统能够保证的亏损上限。"
            "历史回撤只能帮助理解风险，未来仍可能出现更大的波动。"
        )
    if any(term in text for term in ("调仓", "买", "卖", "交易")):
        return (
            f"**当前方案**\n\n{plan_line}\n\n"
            "**是否调仓**\n\n不建议只因单日涨跌立即操作。按计划复查；比特币候选权重变化不足2个百分点时不交易。\n\n"
            "**操作前**\n\n确认近期资金安排，并考虑交易费用、税务与流动性。"
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
        "three_asset_research": {
            "asset_roles": "gold and bitcoin are risk assets; stablecoins are studied as a funding layer",
            "stablecoins": ["USDT", "USDC", "DAI"],
            "q4_sample": "2022-02-17 to 2026-01-29, 1443 days",
            "cash_control_conclusion": "Risk reduction mainly comes from lower gold and bitcoin exposure; no independent stablecoin advantage over zero-yield cash is established.",
            "limits": [
                "DAI has an unresolved Coin Metrics vs DefiLlama conflict in April-May 2025",
                "cash is a theoretical zero-yield USD control",
                "small stablecoin-vs-cash differences lack significance or equivalence tests",
                "Q2 is descriptive association, not prediction or causality",
            ],
        },
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


def _offline_cvar_research_answer(question: str, context: dict) -> str:
    text = question.lower()
    scenario = context["scenario"]
    metrics = context["metrics"]
    latest_target = context.get("latest_target")
    scenario_line = (
        f"当前查看的是 **{scenario['name']}**：θ={scenario['theta']:.1f}，"
        f"BTC权重上限为 **{scenario['btc_cap']:.0%}**。"
    )
    if any(term in text for term in ("稳定币", "现金", "usdt", "usdc", "dai")):
        return (
            "**直接结论**\n\n稳定币在当前历史试算中没有显示出相对零收益现金的明确独立配置优势。"
            "现金与稳定币组合都长期触及30%第三资产上限，风险下降主要来自黄金和BTC总敞口减少。\n\n"
            "稳定币仍可能用于跨境结算、数字资产交易媒介和机构发行，但这些使用价值不等于持币人的价格收益。"
        )
    if any(term in text for term in ("cvar", "尾部", "最差", "回撤")):
        return (
            f"{scenario_line}\n\nCVaR95表示历史最差约5%日收益情景的平均损失。"
            f"当前双资产情景的日CVaR95为 **{metrics['daily_cvar95_loss']:.3%}**，"
            f"历史最大回撤为 **{metrics['maximum_drawdown']:.2%}**。二者不是同一个指标，也都不是未来损失上限。"
        )
    if any(term in text for term in ("经济", "情绪", "因子", "vix", "利率", "美元")):
        return (
            "六类宏观与情绪因素用于检验是否存在稳定线性关联，但现有证据不足以支持将其直接转化为下一期交易信号。"
            "当前模型通过最近252日真实收益间接吸收近期市场环境，再使用滚动CVaR控制尾部风险。"
        )
    if any(term in text for term in ("比例", "权重", "配置", "情景", "theta", "θ")):
        if latest_target:
            return (
                f"**当前研究情景**\n\n{scenario_line}\n\n"
                f"最新一次历史目标于 **{latest_target['effective_date']}** 生效：黄金 **{latest_target['gold']:.1%}**、"
                f"BTC **{latest_target['bitcoin']:.1%}**。该目标来自 {latest_target['signal_date']} 的滚动CVaR信号，"
                "是历史研究结果，不是基于实时行情生成的即时投资建议。"
            )
        return (
            f"**当前研究情景**\n\n{scenario_line}\n\n"
            f"历史CAGR为 **{metrics['cagr']:.2%}**，年化波动为 **{metrics['annual_volatility']:.2%}**，"
            f"最大回撤为 **{metrics['maximum_drawdown']:.2%}**。"
            "当前情景尚未提供逐次目标权重文件，因此页面不会用其他情景的比例替代或推算。"
        )
    return (
        f"{scenario_line}\n\n我可以解释CVaR、三种θ情景、历史风险指标、经济环境与模型的关系，"
        "以及为什么稳定币最终没有进入双资产配置。"
    )


def generate_cvar_research_chat_answer(messages: list[dict], context: dict) -> str:
    """Answer research questions using only the frozen 2026-11-24 evidence."""
    config = get_llm_config()
    latest_question = next(
        (item.get("content", "") for item in reversed(messages) if item.get("role") == "user"),
        "",
    )
    if not is_llm_configured(config):
        return _offline_cvar_research_answer(latest_question, context)

    system_prompt = (ROOT / "prompts" / "cvar_research_chat_system_prompt.md").read_text(encoding="utf-8")
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": json.dumps(context, ensure_ascii=False)},
    ]
    api_messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in messages[-20:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    )
    try:
        body = _post_chat(
            config,
            {"model": config["model"], "temperature": 0.2, "messages": api_messages},
        )
        return body["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return "在线问答暂不可用，已切换为本地说明。\n\n" + _offline_cvar_research_answer(
            latest_question, context
        )
