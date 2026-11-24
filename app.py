from __future__ import annotations

import base64
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from services.cvar_research_service import (
    SCENARIOS,
    get_scenario_meta,
    get_strategy_metrics,
    get_three_arm_metrics,
    load_cvar_research_data,
)
from services.llm_client import generate_cvar_research_chat_answer, is_llm_configured


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "static"


def data_uri(path: Path, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


BACKGROUND_URI = data_uri(ASSETS / "mountain-data-bg.jpg", "image/jpeg")
AVATAR_PATH = ASSETS / "jianwei-leaf-balance-mark.png"
AVATAR_URI = data_uri(AVATAR_PATH, "image/png")

st.set_page_config(
    page_title="衡域｜黄金与比特币滚动CVaR研究",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    f"""
    <style>
    :root{{--ink:#06101a;--panel:rgba(5,14,23,.93);--line:rgba(240,205,135,.30);--gold:#f4d28b;--btc:#dc8957;--stable:#7fd8cb;--text:#fffaf0;--muted:#d4dce2;--green:#5ce0b3}}
    #MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{{display:none!important}}
    html,body,[class*="css"]{{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif;font-size:19px}}
    .stApp{{color:var(--text);background:#06101a url('{BACKGROUND_URI}') center bottom/cover fixed no-repeat}}
    .stApp:before{{content:"";position:fixed;inset:0;background:rgba(0,7,13,.48);pointer-events:none}}
    [data-testid="stAppViewContainer"]>.main,[data-testid="stSidebar"]{{position:relative;z-index:1;background:transparent}}
    [data-testid="stSidebar"]{{min-width:225px;max-width:225px;background:rgba(3,11,18,.96);border-right:1px solid rgba(244,210,139,.18);backdrop-filter:blur(18px)}}
    [data-testid="stSidebar"]>div:first-child{{padding:1.45rem 1rem}}
    .block-container{{max-width:1440px;padding:1.7rem 2rem 2.5rem}}
    h1,h2,h3{{font-family:"STSong","Songti SC","Noto Serif CJK SC",serif;color:#fffaf0}}
    h1{{font-size:clamp(2rem,3vw,3rem)!important;line-height:1.28;letter-spacing:.025em;margin:.25rem 0 .65rem}}
    h2{{font-size:1.62rem!important;margin-top:1.5rem}} h3{{font-size:1.28rem!important}}
    p,label,.stMarkdown{{color:var(--muted);font-size:18px;font-weight:500;line-height:1.78}}.stCaption,small{{color:#b9c4cb!important;font-size:15px!important;line-height:1.65!important}}
    .brand{{font-family:"STSong","Songti SC",serif;color:var(--gold);font-size:1.65rem;letter-spacing:.12em;padding:.15rem .35rem 1rem;border-bottom:1px solid rgba(244,210,139,.16);margin-bottom:1rem}}
    .brand-sub{{font-family:"Microsoft YaHei",sans-serif;font-size:15px;letter-spacing:.04em;color:#bcc6cc;display:block;margin-top:.4rem;line-height:1.55}}
    [data-testid="stSidebar"] [role="radiogroup"] label{{padding:.72rem .65rem;border-left:3px solid transparent;border-radius:7px}}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){{background:rgba(244,210,139,.10);border-left-color:var(--gold)}}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{{color:var(--gold)!important}}
    .side-status{{margin-top:1.2rem;padding:.85rem;border:1px solid rgba(92,224,179,.20);border-radius:10px;background:rgba(92,224,179,.05);color:#d3dde1;font-size:14px;line-height:1.7}}
    .status-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);margin-right:.4rem}}
    .masthead{{display:flex;justify-content:space-between;gap:1rem;align-items:center;border-bottom:1px solid var(--line);padding-bottom:.8rem;margin-bottom:1.15rem}}
    .masthead b{{font-family:"STSong","Songti SC",serif;color:var(--gold);font-size:1.42rem;letter-spacing:.12em}}.masthead span{{color:#d9e0e4;font-size:16px}}
    .subtitle{{max-width:940px;color:#e2e7ea;font-size:19px;line-height:1.78;margin-bottom:.9rem}}
    .research-status{{display:inline-block;margin:0 0 1.2rem;padding:.48rem .75rem;border-left:3px solid var(--gold);background:rgba(244,210,139,.07);color:#ddd4c3;font-size:15px;line-height:1.5}}
    .tags{{display:flex;flex-wrap:wrap;gap:.5rem;margin:.65rem 0 1rem}}.tag{{padding:.4rem .7rem;border:1px solid rgba(84,231,181,.25);border-radius:999px;background:rgba(84,231,181,.06);color:#ceeee5;font-size:14px;font-weight:650}}
    [data-testid="stVerticalBlockBorderWrapper"]{{background:var(--panel);border:1px solid var(--line)!important;border-radius:14px!important;backdrop-filter:blur(18px);box-shadow:0 18px 48px rgba(0,0,0,.28)}}
    .hero{{padding:1.15rem 1.25rem;border:1px solid rgba(244,210,139,.26);border-radius:14px;background:linear-gradient(135deg,rgba(244,210,139,.09),rgba(127,216,203,.04));margin-bottom:1rem}}
    .hero strong{{display:block;color:#fffaf0;font-family:"STSong","Songti SC",serif;font-size:1.35rem;margin-bottom:.35rem}}.hero span{{color:#d6dfe3;font-size:16px;line-height:1.75}}
    .flow{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.7rem;margin:1rem 0 1.4rem}}.flow-step{{position:relative;padding:.9rem;border:1px solid rgba(244,210,139,.18);border-radius:10px;background:rgba(4,13,22,.82)}}
    .flow-step:not(:last-child):after{{content:"→";position:absolute;right:-.58rem;top:50%;transform:translateY(-50%);color:var(--gold);z-index:2}}.flow-step b{{display:block;color:#fffaf0;margin:0 0 .35rem;font-size:17px}}.flow-step span{{color:#c8d1d6;font-size:15px;line-height:1.62}}
    .scenario-head{{padding:.85rem 1rem;border-left:3px solid var(--gold);background:rgba(244,210,139,.06);color:#e7e0d2;font-size:16px;line-height:1.7;margin:.7rem 0 1rem}}.scenario-head strong{{color:#fffaf0}}
    .constraint-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.75rem;margin:.9rem 0}}.constraint{{padding:1.05rem;border:1px solid rgba(255,255,255,.10);border-radius:10px;background:rgba(255,255,255,.025)}}.constraint b{{display:block;color:var(--gold);font-size:16px;margin-bottom:.35rem}}.constraint strong{{display:block;color:#fffaf0;font-family:Georgia,serif;font-size:1.65rem}}.constraint span{{color:#c1cbd1;font-size:15px;line-height:1.6}}
    .warning-card,.conclusion-card{{padding:.9rem 1rem;border-left:3px solid #e7a469;background:rgba(231,164,105,.08);color:#e5d8cb;font-size:15px;line-height:1.7;margin:.9rem 0}}.conclusion-card{{border-left-color:var(--stable);background:rgba(127,216,203,.07);color:#dce9e7;font-size:16px}}.conclusion-card strong{{color:#b8f0e7}}
    .assistant-profile{{display:flex;align-items:center;gap:1.25rem;margin:.25rem 0 1rem;padding:.85rem 1rem;border:1px solid rgba(205,255,142,.26);border-radius:16px;background:linear-gradient(100deg,rgba(205,255,142,.09),rgba(84,231,181,.045))}}.assistant-avatar{{width:145px;height:145px;object-fit:contain;border-radius:18px;image-rendering:pixelated;filter:drop-shadow(0 12px 18px rgba(0,0,0,.28))}}.assistant-name{{font-family:"STSong","Songti SC",serif;color:#fffaf0;font-size:1.55rem;font-weight:700}}.assistant-role{{color:#d7dfe3;font-size:15px;line-height:1.65;margin-top:.3rem}}
    [data-testid="stChatMessageAvatarCustom"]{{width:64px!important;height:64px!important;min-width:64px!important}}[data-testid="stChatMessageAvatarCustom"] img{{width:60px!important;height:60px!important;object-fit:contain!important;image-rendering:pixelated}}
    [data-testid="stChatInput"] textarea{{min-height:78px!important;font-size:17px!important;color:#fffaf0!important;-webkit-text-fill-color:#fffaf0!important;background:#0b1b29!important}}[data-testid="stChatInput"]{{border:1px solid rgba(244,210,139,.45);border-radius:13px;background:#0b1b29!important}}
    [data-testid="stButton"] button{{min-height:48px;border-radius:8px;font-size:16px;font-weight:700}}button[kind="primary"]{{background:#e5b95f!important;color:#18130b!important;border-color:#f5d997!important}}button[kind="secondary"]{{background:rgba(255,255,255,.035)!important;color:#dce2e5!important;border-color:rgba(255,255,255,.14)!important}}
    .st-key-mobile_navigation{{display:none}}
    @media(max-width:920px){{.flow{{grid-template-columns:1fr}}.flow-step:not(:last-child):after{{content:"↓";right:auto;left:50%;top:auto;bottom:-.82rem;transform:translateX(-50%)}}.constraint-grid{{grid-template-columns:1fr}}}}
    @media(max-width:700px){{html,body,[class*="css"]{{font-size:17px}}html,body,.stApp,[data-testid="stAppViewContainer"]{{overflow-x:hidden!important}}[data-testid="stSidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"]{{display:none!important}}[data-testid="stAppViewContainer"]>.main{{margin-left:0!important;width:100%!important}}.block-container,[data-testid="stMainBlockContainer"]{{padding:1rem .9rem 5rem!important;margin:0!important;max-width:100%!important;width:100%!important}}[data-testid="stHorizontalBlock"]{{flex-direction:column!important}}[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{{width:100%!important;flex:1 1 auto!important}}h1{{font-size:clamp(1.82rem,9vw,2.35rem)!important;line-height:1.3}}h2{{font-size:1.42rem!important}}p,label,.stMarkdown{{font-size:17px!important;line-height:1.72!important}}.masthead{{display:grid;gap:.25rem}}.masthead span{{font-size:15px}}.subtitle{{font-size:17px;line-height:1.7}}.research-status{{font-size:14px;margin-bottom:1rem}}.st-key-mobile_navigation{{display:block!important;position:sticky;top:.4rem;z-index:60;margin-bottom:.8rem}}.assistant-profile{{gap:.75rem;padding:.75rem}}.assistant-avatar{{width:96px;height:96px}}.assistant-name{{font-size:1.35rem}}[data-testid="stDataFrame"]{{overflow-x:auto!important}}[data-testid="stPlotlyChart"]{{overflow:hidden!important}}}}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data() -> dict:
    return load_cvar_research_data()


data = get_data()
NAVIGATION = ["首页", "环境与证据", "双资产配置", "历史验证", "稳定币研究", "见微 Agent"]
DEFAULT_SCENARIO = "情景A｜尾部风险优先"
st.session_state.setdefault("navigation", "首页")
st.session_state.setdefault("scenario", DEFAULT_SCENARIO)
st.session_state.setdefault("research_chat", [])


def render_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="masthead"><b>衡域</b><span>2026-11-24 研究版</span></div>'
        f'<h1>{title}</h1><div class="subtitle">{subtitle}</div>'
        '<div class="research-status">历史研究原型 · 非实时交易 · 不构成投资建议</div>',
        unsafe_allow_html=True,
    )


def current_scenario() -> tuple[dict, dict]:
    return get_scenario_meta(st.session_state.scenario), get_strategy_metrics(data, st.session_state.scenario)


def update_scenario(key: str) -> None:
    st.session_state.scenario = st.session_state[key]


def scenario_selector(key: str) -> None:
    if st.session_state.get(key) != st.session_state.scenario:
        st.session_state[key] = st.session_state.scenario
    st.selectbox("研究情景", list(SCENARIOS), key=key, on_change=update_scenario, args=(key,))


def metric_cards(metrics: dict) -> None:
    a, b, c, d = st.columns(4)
    a.metric("历史CAGR", f"{metrics['cagr']:.2%}")
    b.metric("年化波动", f"{metrics['annual_volatility']:.2%}")
    c.metric("最大回撤", f"{metrics['maximum_drawdown']:.2%}")
    d.metric("日CVaR95", f"{metrics['daily_cvar95_loss']:.3%}")


def transparent_chart_layout(height: int = 360) -> dict:
    return {
        "height": height,
        "margin": {"l": 12, "r": 12, "t": 45, "b": 20},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(4,12,20,.22)",
        "font": {"color": "#dce3e7"},
        "yaxis": {"title": "%", "gridcolor": "rgba(255,255,255,.06)"},
    }


def render_home() -> None:
    render_header(
        "RESEARCH OVERVIEW",
        "高不确定性环境下的黄金与比特币尾部风险配置",
        "不预测下一期涨跌，使用最近252日真实收益构造历史情景，在收益偏好与最差5%日损失之间研究黄金—比特币配置。",
    )
    st.markdown(
        '<div class="hero"><strong>最终产品选择双资产，不代表稳定币没有使用价值</strong>'
        '<span>稳定币在当前价格收益实验中没有显示出相对零收益现金的明确独立配置优势，因此不进入最终投资配置；'
        '其跨境结算、数字资产交易媒介和机构发行价值仍在研究范围内。</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="flow"><div class="flow-step"><b>经济与情绪</b><span>利率、美元、VIX与加密情绪改变风险背景。</span></div>'
        '<div class="flow-step"><b>六因子检验</b><span>未形成稳定、可交易的线性预测证据。</span></div>'
        '<div class="flow-step"><b>滚动CVaR</b><span>用252日历史情景控制尾部风险。</span></div>'
        '<div class="flow-step"><b>三种θ情景</b><span>比较不同收益重视程度下的双资产结果。</span></div>'
        '<div class="flow-step"><b>第三资产检验</b><span>现金与稳定币对照后保留黄金＋BTC。</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("## 新版双资产历史结果")
    overview = data["metrics"].query("strategy == 'GOLD_BTC'").copy()
    overview["情景"] = overview["profile"].map({"保守": "A｜尾部风险优先", "均衡": "B｜收益风险权衡", "进取": "C｜收益偏好增强"})
    st.dataframe(
        overview[["情景", "theta", "cagr", "annual_volatility", "maximum_drawdown", "daily_cvar95_loss"]].rename(
            columns={"theta": "θ", "cagr": "历史CAGR", "annual_volatility": "年化波动", "maximum_drawdown": "最大回撤", "daily_cvar95_loss": "日CVaR95"}
        ),
        hide_index=True,
        width="stretch",
        column_config={name: st.column_config.NumberColumn(format="percent") for name in ["历史CAGR", "年化波动", "最大回撤", "日CVaR95"]},
    )
    st.markdown('<div class="conclusion-card"><strong>当前证据：</strong>提高θ或BTC上限并没有带来更高的历史收益。三种情景是参数实验，不是个人风险等级，也不是未来收益排名。</div>', unsafe_allow_html=True)


def render_evidence() -> None:
    render_header(
        "ECONOMY & EVIDENCE",
        "经济环境、投资情绪与模型选择",
        "宏观环境用于提出问题和解释风险；当前证据不足以把六类因子直接转化为下一期交易信号。",
    )
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("为什么不能只使用固定比例")
            st.markdown("黄金的上涨与阶段性波动并存，BTC具有更高波动和更深尾部损失。利率、美元、股票市场和情绪变化可能改变资产风险结构，因此研究采用滚动窗口。")
            st.markdown("#### 六类影响因素")
            st.markdown("标普500、广义美元指数、美国2年期国债收益率、美国10年期国债收益率、VIX、加密市场情绪。")
            st.markdown('<div class="warning-card">线性检验没有形成稳定、经过多重校正的可交易预测证据。这不代表经济环境没有影响，只代表不能把当前结果直接写成下一期买卖信号。</div>', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.subheader("模型如何吸收近期环境")
            st.markdown("经济和情绪变化首先反映在近期资产收益、波动与尾部损失中。模型使用最近252日真实收益构造历史情景，再滚动更新CVaR。")
            st.latex(r"\min_w\left[CVaR_{95\%}(w)-\theta\cdot0.25\bar r^T w\right]")
            st.markdown('<div class="constraint-grid"><div class="constraint"><b>滚动窗口</b><strong>252日</strong><span>自然日简单收益</span></div><div class="constraint"><b>调仓检查</b><strong>21日</strong><span>黄金报价日步长</span></div><div class="constraint"><b>换手上限</b><strong>30%</strong><span>限制单次权重变化</span></div></div>', unsafe_allow_html=True)
            st.caption("交易成本在执行后从净值扣除，没有作为单独的γTC项进入当前优化目标。")


def render_allocation() -> None:
    render_header(
        "DUAL-ASSET CVAR",
        "黄金—比特币CVaR配置实验",
        "选择预设参数情景，查看相同历史样本下的收益—尾部风险结果。情景选择不是个人风险测评。",
    )
    scenario_selector("allocation_scenario")
    meta, metrics = current_scenario()
    st.markdown(f'<div class="scenario-head"><strong>{meta["name"]}</strong><br>θ={meta["theta"]:.1f} · BTC权重上限 {meta["btc_cap"]:.0%} · 黄金与BTC权重之和为100%</div>', unsafe_allow_html=True)
    metric_cards(metrics)
    st.markdown(
        f'<div class="constraint-grid"><div class="constraint"><b>收益偏好参数</b><strong>{meta["theta"]:.1f}</strong><span>越大越重视历史平均收益</span></div>'
        f'<div class="constraint"><b>BTC允许上限</b><strong>{meta["btc_cap"]:.0%}</strong><span>允许上限，不是实际目标权重</span></div>'
        '<div class="constraint"><b>成功调仓</b><strong>48次</strong><span>本次原型求解失败0次</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="warning-card"><strong>为什么暂时没有显示黄金/BTC最新比例？</strong><br>2026-11-24交接包提供了双资产三档汇总指标，但没有附带双资产逐次目标权重文件。第一版不会使用旧模型比例或猜测新权重；补齐新版targets后，这里将显示真实比例和模拟金额换算。</div>', unsafe_allow_html=True)
    explanation = {
        "A": "θ=0时，目标函数不奖励历史平均收益，主要寻找历史CVaR较低的黄金—BTC组合，同时BTC最多15%。",
        "B": "θ=0.6时，模型在CVaR基础上加入一定历史平均收益权重，同时BTC最多35%。",
        "C": "θ=1.5时，模型更重视历史平均收益，同时BTC最多60%；但本样本历史收益并未因此高于情景A。",
    }
    st.info(explanation[meta["short"]])


def render_history() -> None:
    render_header(
        "HISTORICAL VALIDATION",
        "三种研究情景的历史验证",
        "使用同一CVaR求解器、同一样本和执行规则，比较θ变化对收益与风险指标的实际影响。",
    )
    dual = data["metrics"].query("strategy == 'GOLD_BTC'").copy()
    dual["情景"] = dual["profile"].map({"保守": "A", "均衡": "B", "进取": "C"})
    fig = go.Figure()
    fig.add_bar(name="年化波动", x=dual["情景"], y=dual["annual_volatility"] * 100, marker_color="#f4d28b", text=[f"{v:.2%}" for v in dual["annual_volatility"]], textposition="outside")
    fig.add_bar(name="最大回撤绝对值", x=dual["情景"], y=dual["maximum_drawdown"].abs() * 100, marker_color="#dc8957", text=[f"{abs(v):.2%}" for v in dual["maximum_drawdown"]], textposition="outside")
    fig.update_layout(barmode="group", legend={"orientation": "h", "y": 1.14}, **transparent_chart_layout(390))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    c1, c2 = st.columns(2, gap="large")
    with c1:
        fig = go.Figure(go.Bar(x=dual["情景"], y=dual["cagr"] * 100, marker_color=["#f4d28b", "#d7a862", "#bd8050"], text=[f"{v:.2%}" for v in dual["cagr"]], textposition="outside"))
        fig.update_layout(title="历史CAGR", **transparent_chart_layout(330))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with c2:
        fig = go.Figure(go.Bar(x=dual["情景"], y=dual["daily_cvar95_loss"] * 100, marker_color=["#7fd8cb", "#67bdb2", "#509f98"], text=[f"{v:.3%}" for v in dual["daily_cvar95_loss"]], textposition="outside"))
        fig.update_layout(title="日CVaR95", **transparent_chart_layout(330))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown('<div class="conclusion-card"><strong>历史结果：</strong>三种情景的波动、回撤和CVaR非常接近，情景A的历史CAGR反而最高。θ表示目标函数设定，不代表收益排名，也不能据此推断未来表现。</div>', unsafe_allow_html=True)


def render_stablecoin() -> None:
    render_header(
        "STABLECOIN STUDY",
        "稳定币为什么没有进入最终配置",
        "在相同CVaR框架中使用现金控制组，区分风险资产敞口下降与稳定币本身的作用。",
    )
    scenario_selector("stable_scenario")
    comparison = get_three_arm_metrics(data, st.session_state.scenario)
    labels = comparison["label"].tolist()
    results_tab, use_tab, quality_tab = st.tabs(["三组结果", "稳定币应用", "数据质量"])
    with results_tab:
        a, b = st.columns(2, gap="large")
        with a:
            fig = go.Figure(go.Bar(x=labels, y=comparison["cagr"] * 100, marker_color=["#f4d28b", "#aebbc5", "#7fd8cb"], text=[f"{v:.2%}" for v in comparison["cagr"]], textposition="outside"))
            fig.update_layout(title="历史CAGR", **transparent_chart_layout())
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        with b:
            fig = go.Figure(go.Bar(x=labels, y=comparison["annual_volatility"] * 100, marker_color=["#f4d28b", "#aebbc5", "#7fd8cb"], text=[f"{v:.2%}" for v in comparison["annual_volatility"]], textposition="outside"))
            fig.update_layout(title="年化波动", **transparent_chart_layout())
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.dataframe(
            comparison[["label", "cagr", "annual_volatility", "maximum_drawdown", "daily_cvar95_loss"]].rename(columns={"label": "资产集合", "cagr": "历史CAGR", "annual_volatility": "年化波动", "maximum_drawdown": "最大回撤", "daily_cvar95_loss": "日CVaR95"}),
            hide_index=True,
            width="stretch",
            column_config={name: st.column_config.NumberColumn(format="percent") for name in ["历史CAGR", "年化波动", "最大回撤", "日CVaR95"]},
        )
        st.markdown('<div class="conclusion-card"><strong>研究结论：</strong>现金与稳定币均长期达到30%第三资产上限，二者风险收益结果接近。风险下降主要来自黄金和BTC敞口减少，尚未发现稳定币相对现金的明确独立配置优势。</div>', unsafe_allow_html=True)
    with use_tab:
        st.markdown("### 没有进入配置，不等于没有应用价值")
        st.markdown('<div class="constraint-grid"><div class="constraint"><b>跨境与结算</b><strong>支付工具</strong><span>在适用司法辖区和合规条件下，用于链上转移与跨时区结算。</span></div><div class="constraint"><b>数字资产交易</b><strong>计价媒介</strong><span>可作为购买BTC等数字资产时的美元计价和交易媒介。</span></div><div class="constraint"><b>机构发行</b><strong>商业模式</strong><span>发行机构可能通过储备资产获得利息或服务收入。</span></div></div>', unsafe_allow_html=True)
        st.warning("发行机构的储备收入不等于普通持币人的投资收益。借贷、质押或流动性池收益还会引入平台、合约和流动性风险。")
    with quality_tab:
        st.markdown("### Coin Metrics稳定币报价概览")
        source = data["stablecoin_sources"].copy()
        st.dataframe(source.rename(columns={"symbol": "币种", "count": "观测数", "start": "起始日", "end": "结束日", "min_price": "最低USD价", "max_price": "最高USD价"}), hide_index=True, width="stretch")
        st.markdown('<div class="warning-card"><strong>DAI跨源冲突：</strong>2025-04-30 Coin Metrics记录约1.090750美元，而DefiLlama同日约0.999899美元。当前原型保留Coin Metrics原始值，但尚未完成双源敏感性检验。</div>', unsafe_allow_html=True)


def chat_context() -> dict:
    meta, metrics = current_scenario()
    return {
        "version": data["version"],
        "status": data["data_status"],
        "sample": {"start": data["sample_start"], "end": data["sample_end"]},
        "scenario": meta,
        "metrics": {key: metrics[key] for key in ["cagr", "annual_volatility", "maximum_drawdown", "daily_cvar95_loss", "orders"]},
        "method": {"window_natural_days": 252, "alpha": 0.95, "expected_return_shrinkage": 0.25, "turnover_limit": 0.30, "gold_fee": 0.0005, "btc_fee": 0.0015},
        "stablecoin_conclusion": "No clear independent allocation advantage over zero-yield cash was established; both funding arms bind at the 30% cap.",
        "weights_available": False,
    }


def render_agent() -> None:
    render_header(
        "JIANWEI AGENT",
        "见微研究问答",
        "围绕当前CVaR情景连续追问。见微只能解释冻结研究结果，不能创造或修改资产权重。",
    )
    scenario_selector("agent_scenario")
    meta, metrics = current_scenario()
    with st.container(border=True):
        st.markdown(
            f'<div class="assistant-profile"><img class="assistant-avatar" src="{AVATAR_URI}" alt="见微助手形象"><div><div class="assistant-name">见微</div>'
            f'<div class="assistant-role">滚动CVaR研究解释Agent<br>{meta["name"]} · θ={meta["theta"]:.1f} · BTC上限 {meta["btc_cap"]:.0%}</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="tags"><span class="tag">绑定当前情景</span><span class="tag">支持连续追问</span><span class="tag">不修改模型权重</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="scenario-head">历史CAGR <strong>{metrics["cagr"]:.2%}</strong> · 年化波动 <strong>{metrics["annual_volatility"]:.2%}</strong> · 最大回撤 <strong>{metrics["maximum_drawdown"]:.2%}</strong> · 日CVaR95 <strong>{metrics["daily_cvar95_loss"]:.3%}</strong></div>', unsafe_allow_html=True)
        if not st.session_state.research_chat:
            with st.chat_message("assistant", avatar=str(AVATAR_PATH)):
                st.markdown("你好，我是见微。你可以问我CVaR、三种θ情景、经济环境与模型的关系，以及为什么稳定币最终没有进入双资产配置。")
        for message in st.session_state.research_chat:
            avatar = str(AVATAR_PATH) if message["role"] == "assistant" else None
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
        prompt = st.chat_input("问见微：为什么这样设置θ？稳定币还有什么应用？")
        if prompt:
            st.session_state.research_chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar=str(AVATAR_PATH)):
                with st.spinner("见微正在核对新版研究数据……"):
                    answer = generate_cvar_research_chat_answer(st.session_state.research_chat, chat_context())
                st.markdown(answer)
            st.session_state.research_chat.append({"role": "assistant", "content": answer})
        if st.session_state.research_chat and st.button("清空本次问答", type="secondary"):
            st.session_state.research_chat = []
            st.rerun()


def sync_navigation(source: str) -> None:
    st.session_state.navigation = st.session_state[source]


with st.sidebar:
    st.markdown('<div class="brand">衡域<span class="brand-sub">滚动CVaR研究 · 见微Agent</span></div>', unsafe_allow_html=True)
    if st.session_state.get("sidebar_nav") != st.session_state.navigation:
        st.session_state.sidebar_nav = st.session_state.navigation
    st.radio("导航", NAVIGATION, key="sidebar_nav", label_visibility="collapsed", on_change=sync_navigation, args=("sidebar_nav",))
    mode = "见微在线" if is_llm_configured() else "见微本地说明模式"
    st.markdown(f'<div class="side-status"><span class="status-dot"></span>新版数据已载入<br>{data["version"]} · {mode}</div>', unsafe_allow_html=True)

with st.container(key="mobile_navigation"):
    if st.session_state.get("mobile_nav") != st.session_state.navigation:
        st.session_state.mobile_nav = st.session_state.navigation
    st.selectbox("页面切换", NAVIGATION, key="mobile_nav", label_visibility="collapsed", on_change=sync_navigation, args=("mobile_nav",))

page = st.session_state.navigation
if page == "首页":
    render_home()
elif page == "环境与证据":
    render_evidence()
elif page == "双资产配置":
    render_allocation()
elif page == "历史验证":
    render_history()
elif page == "稳定币研究":
    render_stablecoin()
else:
    render_agent()
