from __future__ import annotations

import os
import base64
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from services.data_service import load_dashboard_data
from services.llm_client import generate_advice, generate_chat_answer
from services.portfolio_engine import calculate_personalized_plan

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "static"


def data_uri(path: Path, mime_type: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


BACKGROUND_URI = data_uri(ASSETS / "mountain-data-bg.jpg", "image/jpeg")
GOLD_ICON_URI = data_uri(ASSETS / "gold-bars.png", "image/png")
BITCOIN_ICON_URI = data_uri(ASSETS / "bitcoin-coin.png", "image/png")
JIANWEI_AVATAR_PATH = ASSETS / "jianwei-leaf-balance-mark.png"
JIANWEI_AVATAR_URI = data_uri(JIANWEI_AVATAR_PATH, "image/png")

st.set_page_config(page_title="衡域｜见微投资问答", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    :root {--ink:#06101a;--panel:rgba(5,14,23,.93);--line:rgba(240,205,135,.34);--gold:#f4d28b;--copper:#dc8957;--text:#fffaf0;--muted:#d5dbe0;--emerald:#54e7b5}
    #MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
    html,body,[class*="css"]{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif;font-size:18px}
    .stApp{color:var(--text);background-color:var(--ink);background-image:url('/app/static/mountain-data-bg.png');background-size:cover;background-position:center bottom;background-attachment:fixed}
    .stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:rgba(0,7,13,.30);z-index:0}
    [data-testid="stAppViewContainer"]{background:transparent!important}
    [data-testid="stAppViewContainer"]>.main,[data-testid="stSidebar"]{position:relative;z-index:1;background:transparent}
    [data-testid="stSidebar"]{min-width:205px;max-width:205px;background:rgba(3,11,18,.94);border-right:1px solid rgba(237,199,119,.20);backdrop-filter:blur(18px);transform:none!important;z-index:100!important}
    [data-testid="stSidebar"]>div:first-child{padding:1.65rem 1rem}[data-testid="stSidebarCollapseButton"]{display:none}
    .block-container{max-width:none;padding:2.1rem 2.25rem 1.5rem}
    h1,h2,h3{font-family:"STSong","Songti SC","Noto Serif CJK SC",serif;color:var(--text)}
    h1{font-size:clamp(2.1rem,3vw,3.25rem)!important;letter-spacing:.055em;margin:.2rem 0 .35rem;text-shadow:0 2px 18px rgba(0,0,0,.42)}h2{font-size:1.65rem!important}p,label,.stMarkdown,.stCaption{color:var(--muted);font-size:18px;font-weight:500;line-height:1.72}.stCaption,small{color:#cbd2d8!important;font-size:15px!important;font-weight:500!important;line-height:1.65}
    .brand{font-family:"STSong","Songti SC",serif;color:var(--gold);font-size:1.62rem;letter-spacing:.11em;padding:.1rem .35rem 1.25rem;border-bottom:1px solid rgba(237,199,119,.17);margin-bottom:1.25rem}
    .brand-sub{font-family:"Microsoft YaHei",sans-serif;font-size:15px;letter-spacing:.12em;color:#8996a1;display:block;margin-top:.42rem}
    [data-testid="stSidebar"] [role="radiogroup"]{gap:.45rem}[data-testid="stSidebar"] [role="radiogroup"] label{background:transparent;padding:.78rem .68rem;border-radius:6px;border-left:3px solid transparent;font-weight:600}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:rgba(237,199,119,.10);border-left-color:var(--gold)}[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{color:var(--gold)!important}
    .side-meta{position:fixed;bottom:1.5rem;left:1.25rem;width:165px;color:#b8c2ca;font-size:15px;font-weight:500;line-height:1.7}
    .product-masthead{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding:0 0 .85rem;margin-bottom:1.35rem}.product-name{font-family:"STSong","Songti SC",serif;color:var(--gold);font-size:1.55rem;letter-spacing:.16em}.assistant-name{color:#eee4d3;font-size:1.05rem;letter-spacing:.08em}
    .eyebrow{color:var(--gold);letter-spacing:.13em;font-size:15px;font-weight:700}.page-subtitle{font-size:18px;color:#e0e5e9;max-width:860px;margin-bottom:1.35rem;font-weight:500;line-height:1.75}
    .topline{display:flex;justify-content:space-between;align-items:center;padding-bottom:.35rem;margin-bottom:.35rem}.date{color:#9aa6b0;font-size:15px;letter-spacing:.04em}
    [data-testid="stVerticalBlockBorderWrapper"]{background:var(--panel);border:1px solid var(--line)!important;border-radius:14px!important;backdrop-filter:blur(18px);box-shadow:0 22px 60px rgba(0,0,0,.34)}
    [data-testid="stVerticalBlockBorderWrapper"]>div{padding:.15rem .35rem}
    .card-heading{font-family:"STSong","Songti SC",serif;color:var(--text);font-size:1.5rem;font-weight:700;margin:.25rem 0 .35rem}.card-intro{color:#cbd3da;font-size:16px;font-weight:500;line-height:1.7;margin-bottom:.8rem}
    .stepper{display:grid;grid-template-columns:repeat(5,1fr);gap:.35rem;margin:.9rem 0 1.45rem}.step{text-align:center;color:#8f9ba5;font-size:15px;position:relative}
    .step:before{content:"";position:absolute;top:15px;left:-50%;width:100%;height:1px;background:#53606d;z-index:0}.step:first-child:before{display:none}
    .step-dot{position:relative;z-index:1;width:31px;height:31px;margin:0 auto .55rem;border:1px solid #697785;border-radius:50%;display:grid;place-items:center;background:#101b26;font-size:.78rem}
    .step.active,.step.done{color:#f2eadb}.step.active .step-dot,.step.done .step-dot{border-color:var(--gold);color:#16120b;background:#e9bd68;box-shadow:0 0 22px rgba(233,189,104,.22)}
    .question-kicker{color:#c0c8cf;font-size:15px;font-weight:600;margin-top:.4rem}.question-title{font-family:"STSong","Songti SC",serif;color:var(--text);font-size:clamp(1.55rem,2.2vw,2.25rem);font-weight:700;margin:.2rem 0 .35rem;letter-spacing:.035em}.question-help{color:#d3d9de;font-size:17px;font-weight:500;margin-bottom:1.2rem;line-height:1.7}
    [data-testid="stSlider"] [data-baseweb="slider"]>div>div{background:#687583}[data-testid="stSlider"] [role="slider"]{background:var(--gold);border-color:white;box-shadow:0 0 16px rgba(237,199,119,.38)}
    [data-testid="stButton"] button{background:#e5b95f;color:#18130b;border:1px solid #f5d997;border-radius:7px;min-height:52px;font-size:18px;font-weight:700;letter-spacing:.04em;box-shadow:0 10px 28px rgba(183,119,35,.20)}
    [data-testid="stButton"] button:hover{background:#f0cc7e;color:#120e08;border-color:#ffe6ac}button[kind="secondary"]{background:rgba(255,255,255,.035)!important;color:#d8dde1!important;border-color:rgba(255,255,255,.14)!important;box-shadow:none!important}
    .engine-head{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;border-bottom:1px solid var(--line);padding-bottom:.85rem}.engine-title{font-family:"STSong","Songti SC",serif;color:var(--text);font-size:1.5rem;letter-spacing:.035em}.engine-role{text-align:right;color:#d8c7a6;font-size:15px;line-height:1.55;white-space:nowrap}.dynamic-label{display:inline-block;margin-top:.45rem;color:var(--gold);font-size:15px}
    .asset-icon{display:block;width:66px;height:58px;object-fit:contain;margin:.65rem auto .15rem}.asset-name{text-align:center;color:#d8b66d;font-size:16px}.asset-weight{text-align:center;color:var(--text);font-family:Georgia,"Times New Roman",serif;font-size:1.6rem;font-weight:700}
    .metric-row{display:grid;grid-template-columns:1fr 1fr;gap:1px;border-top:1px solid var(--line);margin-top:.2rem}.metric-box{padding:.9rem 1rem .6rem}.metric-box+.metric-box{border-left:1px solid var(--line)}.metric-label{font-size:15px;color:#9aa5ae}.metric-value{font-family:Georgia,serif;font-size:1.5rem;color:#f8f2e8;margin-top:.2rem}
    .tiny-bar{display:flex;gap:4px;margin-top:.48rem}.tiny-bar i{height:5px;width:22px;background:#303d49;border-radius:1px}.tiny-bar i.on{background:var(--emerald)}
    .logic-note{border-top:1px solid var(--line);margin-top:.65rem;padding-top:.85rem;color:#aeb7bf;font-size:15px;line-height:1.65}.anchor-scale{display:grid;grid-template-columns:repeat(3,1fr);margin:.55rem 0 .9rem;color:#9ba5ad;font-size:15px;text-align:center}.anchor-scale span{border-top:1px solid rgba(237,199,119,.35);padding-top:.35rem}
    .status-chip{display:inline-flex;align-items:center;gap:.35rem;color:#69dfb5;font-size:15px}.status-chip:before{content:"";width:7px;height:7px;border-radius:50%;background:#45d6a4;box-shadow:0 0 10px #45d6a4}
    .result-banner{padding:1rem 1.1rem;border-left:2px solid var(--gold);background:rgba(237,199,119,.06);color:#ded6c8;font-size:16px;line-height:1.65}
    [data-testid="stExpander"]{background:rgba(6,15,24,.70);border-color:var(--line)}[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{background:rgba(5,13,21,.82);color:#f7f1e5;border-color:rgba(237,199,119,.18)}[data-testid="stAlert"]{background:rgba(7,17,27,.88);color:#d9e0e5;border-color:rgba(237,199,119,.22)}
    [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{font-size:18px!important;min-height:52px;color:#fffaf0!important;font-weight:600}
    [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]){min-height:660px;padding:1rem .8rem 1.3rem!important;background:rgba(3,11,18,.96);border-color:rgba(244,210,139,.42)!important}
    [data-testid="stChatInput"]{margin-top:1.25rem;border:1px solid rgba(244,210,139,.55);border-radius:14px;background:rgba(12,25,37,.96);box-shadow:0 12px 32px rgba(0,0,0,.32)}
    [data-testid="stChatInput"] textarea{font-size:18px!important;min-height:84px!important;padding:1rem 3.5rem 1rem 1rem!important;color:#fffaf0!important;font-weight:500;line-height:1.6}
    [data-testid="stChatInput"] textarea::placeholder{color:#aeb8c0!important;opacity:1}
    [data-testid="stChatInput"] button{width:46px!important;height:46px!important}
    [data-testid="stChatMessage"]{font-size:18px;line-height:1.78;padding:1rem .8rem;border-radius:12px;margin:.45rem 0;background:rgba(255,255,255,.025);gap:1rem}[data-testid="stChatMessage"] p{color:#eef2f5!important;font-weight:500}
    [data-testid="stChatMessageAvatarCustom"]{width:72px!important;height:72px!important;min-width:72px!important;flex:0 0 72px!important;background:rgba(205,255,142,.10)!important;border:1px solid rgba(205,255,142,.34)!important}[data-testid="stChatMessageAvatarCustom"] img{width:68px!important;height:68px!important;object-fit:contain!important;image-rendering:pixelated}
    .assistant-profile{display:flex;align-items:center;gap:1.35rem;margin:.35rem 0 1.2rem;padding:.85rem 1.2rem;border:1px solid rgba(205,255,142,.26);border-radius:16px;background:linear-gradient(100deg,rgba(205,255,142,.09),rgba(84,231,181,.045))}.assistant-avatar{width:160px;height:160px;object-fit:contain;object-position:center;border-radius:20px;filter:drop-shadow(0 12px 18px rgba(0,0,0,.28));image-rendering:pixelated}.assistant-profile-name{font-family:"STSong","Songti SC",serif;color:#fffaf0;font-size:1.55rem;font-weight:700;letter-spacing:.08em}.assistant-profile-role{color:#d8dee3;font-size:16px;font-weight:500;margin-top:.35rem;line-height:1.65}
    .interpret-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin-top:.8rem}.interpret-item{padding:1rem 1.1rem;border:1px solid rgba(237,199,119,.18);border-radius:10px;background:rgba(255,255,255,.025)}.interpret-item b{display:block;color:var(--gold);font-size:18px;margin-bottom:.45rem}.interpret-item div{color:#e0e5e9;font-size:17px;font-weight:500;line-height:1.75}
    .method-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:.8rem;margin-top:.8rem}.method-item{background:rgba(5,14,23,.76);border:1px solid var(--line);padding:1.05rem;border-radius:10px}.method-item b{color:var(--gold);display:block;margin-bottom:.35rem}.method-item span{color:#b8c1c8;font-size:16px;line-height:1.7}
    @media(max-width:1200px){.engine-title{font-size:1.12rem}.engine-role{font-size:.62rem}.block-container{padding:1.7rem 1.5rem}.page-subtitle{margin-bottom:1rem}}
    @media(max-width:920px){[data-testid="stSidebar"]{min-width:175px;max-width:175px}.block-container{padding:1.25rem 1rem}.stepper{grid-template-columns:repeat(5,minmax(70px,1fr));overflow-x:auto}.side-meta{display:none}.interpret-grid{grid-template-columns:1fr}.product-masthead{align-items:flex-start;gap:.6rem}.assistant-name{text-align:right}}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f"<style>.stApp{{background-image:url('{BACKGROUND_URI}')!important}}</style>",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_data() -> dict:
    return load_dashboard_data()


data = get_data()
frozen = data["frozen"]
allocation = data["allocation"]
latest_state = allocation["market_state_at_signal"]
state_names = {"normal": "正常", "macro_stress": "宏观压力", "crypto_stress": "加密压力"}

DEFAULTS = {"assessment_step":0,"answer_horizon_years":7,"answer_max_drawdown_pct":20,"answer_liquidity_need":"低","answer_loss_reaction":"继续持有","answer_bitcoin_acceptance":66,"investment_amount":100000.0,"current_gold":0.0,"current_bitcoin":0.0,"chat_messages":[]}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def current_answers() -> dict:
    return {"horizon_years":st.session_state.answer_horizon_years,"max_drawdown":st.session_state.answer_max_drawdown_pct/100,"liquidity_need":st.session_state.answer_liquidity_need,"loss_reaction":st.session_state.answer_loss_reaction,"bitcoin_acceptance":st.session_state.answer_bitcoin_acceptance}


def current_plan() -> dict:
    return calculate_personalized_plan(current_answers(),st.session_state.investment_amount,st.session_state.current_gold,st.session_state.current_bitcoin,allocation)


def render_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="product-masthead"><span class="product-name">衡域</span><span class="assistant-name">见微 · 投资问答</span></div><div class="topline"><span class="eyebrow">{eyebrow}</span><span class="date">数据截止 {allocation["as_of_date"]}</span></div><h1>{title}</h1><div class="page-subtitle">{subtitle}</div>',unsafe_allow_html=True)


def render_stepper(active: int) -> None:
    labels = ["投资期限","你能接受的回撤","流动性需求","亏损反应","比特币接受度"]
    items = []
    for index,label in enumerate(labels):
        status = "done" if index < active else "active" if index == active else ""
        symbol = "✓" if index < active else str(index+1)
        items.append(f'<div class="step {status}"><div class="step-dot">{symbol}</div>{label}</div>')
    st.markdown(f'<div class="stepper">{"".join(items)}</div>',unsafe_allow_html=True)


def sync_answer(widget_key: str, answer_key: str) -> None:
    st.session_state[answer_key] = st.session_state[widget_key]


def prepare_widget(widget_key: str, answer_key: str) -> None:
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[answer_key]


def render_question(step: int) -> None:
    if step == 0:
        st.markdown('<div class="question-kicker">投资目标</div><div class="question-title">你的计划投资期限</div><div class="question-help">更长的持有期通常意味着更强的波动消化能力。</div>',unsafe_allow_html=True)
        prepare_widget("widget_horizon_years","answer_horizon_years")
        st.slider("计划投资期限（年）",1,10,key="widget_horizon_years",label_visibility="collapsed",on_change=sync_answer,args=("widget_horizon_years","answer_horizon_years"))
    elif step == 1:
        st.markdown('<div class="question-kicker">风险承受度</div><div class="question-title">你能接受的回撤</div><div class="question-help">如果账户出现阶段性亏损，你认为自己最多能承受多大的跌幅？这不是系统承诺的亏损上限。</div>',unsafe_allow_html=True)
        prepare_widget("widget_max_drawdown_pct","answer_max_drawdown_pct")
        st.slider("你能接受的回撤（%）",10,50,step=5,key="widget_max_drawdown_pct",label_visibility="collapsed",on_change=sync_answer,args=("widget_max_drawdown_pct","answer_max_drawdown_pct"))
    elif step == 2:
        st.markdown('<div class="question-kicker">资金约束</div><div class="question-title">流动性需求</div><div class="question-help">未来三年内，你动用这笔资金的可能性有多高？</div>',unsafe_allow_html=True)
        prepare_widget("widget_liquidity_need","answer_liquidity_need")
        st.select_slider("流动性需求",["高","中","低"],key="widget_liquidity_need",label_visibility="collapsed",on_change=sync_answer,args=("widget_liquidity_need","answer_liquidity_need"))
    elif step == 3:
        st.markdown('<div class="question-kicker">行为偏好</div><div class="question-title">面对短期亏损时</div><div class="question-help">如果组合短期下跌20%，你更可能怎么做？</div>',unsafe_allow_html=True)
        prepare_widget("widget_loss_reaction","answer_loss_reaction")
        st.radio("亏损反应",["立即清仓","明显减仓","继续持有","逢低增加"],key="widget_loss_reaction",horizontal=True,label_visibility="collapsed",on_change=sync_answer,args=("widget_loss_reaction","answer_loss_reaction"))
    else:
        st.markdown('<div class="question-kicker">资产认知</div><div class="question-title">比特币接受度</div><div class="question-help">综合认知、经验与心理感受，你对比特币高波动的接受程度是多少？</div>',unsafe_allow_html=True)
        prepare_widget("widget_bitcoin_acceptance","answer_bitcoin_acceptance")
        st.slider("比特币接受度",0,100,key="widget_bitcoin_acceptance",label_visibility="collapsed",on_change=sync_answer,args=("widget_bitcoin_acceptance","answer_bitcoin_acceptance"))


def render_result_panel(plan: dict) -> None:
    st.markdown('<div class="engine-head"><div><div class="engine-title">你的配置方案</div><span class="dynamic-label">根据你的回答计算</span></div><div class="engine-role">黄金 × 比特币<br>当前建议比例</div></div>',unsafe_allow_html=True)
    gold_col, btc_col = st.columns(2)
    with gold_col:
        st.markdown(f'<img class="asset-icon" src="{GOLD_ICON_URI}" alt="黄金金条"><div class="asset-name">黄金</div><div class="asset-weight">{plan["gold_weight"]:.1%}</div>',unsafe_allow_html=True)
    with btc_col:
        st.markdown(f'<img class="asset-icon" src="{BITCOIN_ICON_URI}" alt="比特币标志"><div class="asset-name" style="color:#d98a58">比特币</div><div class="asset-weight">{plan["bitcoin_weight"]:.1%}</div>',unsafe_allow_html=True)
    fig = go.Figure(go.Pie(values=[plan["gold_weight"],plan["bitcoin_weight"]],labels=["黄金","比特币"],hole=.72,sort=False,marker={"colors":["#edc777","#b9683d"],"line":{"color":"rgba(255,255,255,.32)","width":1}},textinfo="none",hovertemplate="%{label} %{percent}<extra></extra>"))
    fig.update_layout(height=255,margin={"l":12,"r":12,"t":8,"b":0},paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",showlegend=False,annotations=[{"text":f"风险评分<br><b>{plan['risk_score']:.0f}</b>","x":.5,"y":.5,"showarrow":False,"font":{"color":"#f4ead7","size":15}}])
    st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
    vol = plan["backtest_reference"]["annualized_volatility"]
    st.markdown(f'<div class="metric-row"><div class="metric-box"><div class="metric-label">历史参考年化波动</div><div class="metric-value">{vol:.1%}</div><div class="tiny-bar"><i class="on"></i><i class="on"></i><i class="on"></i><i></i><i></i></div></div><div class="metric-box"><div class="metric-label">你能接受的回撤</div><div class="metric-value">{st.session_state.answer_max_drawdown_pct}%</div><div class="tiny-bar"><i class="on"></i><i class="on"></i><i></i><i></i><i></i></div></div></div><div class="anchor-scale"><span>偏稳健</span><span>较均衡</span><span>偏进取</span></div><div class="logic-note">方案会根据你的五项回答，在历史参考方案之间计算当前比例。历史表现不代表未来结果。</div>',unsafe_allow_html=True)


def render_interpretation(plan: dict) -> None:
    with st.container(border=True):
        st.markdown('<div class="card-heading">见微解读</div><div class="card-intro">从配置结论、配置理由、风险和下一步四个方面理解当前方案。</div>',unsafe_allow_html=True)
        api_ready = bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_API_BASE") and os.getenv("LLM_MODEL"))
        status_col, action_col = st.columns([1, 1])
        with status_col:
            st.markdown(f'<span class="status-chip">{"见微在线" if api_ready else "见微离线说明模式"}</span>',unsafe_allow_html=True)
        with action_col:
            generate = st.button("生成见微解读",use_container_width=True,type="primary")
        if generate:
            try:
                with st.spinner("见微正在整理配置结论、理由、风险与下一步……"):
                    st.session_state.latest_advice = generate_advice(plan,{"market_state":latest_state,"signal_date":allocation["latest_signal_date"],"data_as_of":allocation["as_of_date"],**current_answers()})
            except Exception as exc:
                st.error(f"见微暂时无法完成在线解读：{exc}")
        advice = st.session_state.get("latest_advice")
        if advice:
            reasons = "<br>".join(f"• {escape(str(item))}" for item in advice.get("reasons", []))
            warnings = "<br>".join(f"• {escape(str(item))}" for item in advice.get("warnings", []))
            st.markdown(
                '<div class="interpret-grid">'
                f'<div class="interpret-item"><b>配置结论</b><div>{escape(str(advice.get("summary", "")))}</div></div>'
                f'<div class="interpret-item"><b>配置理由</b><div>{reasons}</div></div>'
                f'<div class="interpret-item"><b>风险</b><div>{warnings}</div></div>'
                f'<div class="interpret-item"><b>下一步</b><div>{escape(str(advice.get("rebalance_message", "按计划定期复查。")))}</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("点击“生成见微解读”，这里会给出完整说明；生成按钮和加载状态均保留在本区域。")


def render_assessment() -> None:
    render_header("PERSONAL ALLOCATION","风险偏好问卷与配置方案","回答五个问题，系统会根据你的回答计算黄金与比特币的参考配置。")
    left,right = st.columns([1.15,1],gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="card-heading">风险偏好问卷</div><div class="card-intro">完成五个问题，形成与你的期限、资金需求和风险感受相匹配的参考。</div>',unsafe_allow_html=True)
            step = int(st.session_state.assessment_step)
            render_stepper(step)
            render_question(step)
            st.markdown("<br>",unsafe_allow_html=True)
            back,forward = st.columns([.34,1])
            if step > 0 and back.button("上一步",use_container_width=True,type="secondary"):
                st.session_state.assessment_step -= 1
                st.rerun()
            next_label = "生成我的配置" if step == 4 else "继续评估  →"
            if forward.button(next_label,use_container_width=True):
                if step < 4: st.session_state.assessment_step += 1
                else: st.session_state.assessment_complete = True
                st.rerun()
            plan = current_plan()
            st.markdown(f'<div class="result-banner">当前风险评分 <b>{plan["risk_score"]:.1f}</b> / 100。每次修改答案，右侧比例都会由同一套规则实时重算。</div>',unsafe_allow_html=True)
            with st.expander("按投资金额换算",expanded=False):
                st.number_input("计划投资金额（元）",min_value=0.0,step=1000.0,key="investment_amount")
                a,b = st.columns(2)
                a.number_input("当前黄金市值（元）",min_value=0.0,step=1000.0,key="current_gold")
                b.number_input("当前比特币市值（元）",min_value=0.0,step=1000.0,key="current_bitcoin")
    with right:
        with st.container(border=True):
            plan = current_plan()
            render_result_panel(plan)
    st.markdown("<div style='height:.8rem'></div>",unsafe_allow_html=True)
    render_interpretation(current_plan())


def render_plan() -> None:
    plan = current_plan()
    render_header("MY PLAN","我的配置方案","把个性化权重换算为金额，并明确下一次检查与调仓边界。")
    left,right = st.columns([1.1,.9],gap="large")
    with left:
        with st.container(border=True): render_result_panel(plan)
    with right:
        with st.container(border=True):
            st.subheader("目标金额")
            st.number_input("计划投资金额（元）",min_value=0.0,step=1000.0,key="investment_amount")
            st.markdown(f"### 黄金　¥{plan['target_gold']:,.0f}")
            st.caption(f"当前市值 ¥{plan['current_gold']:,.0f} · 调整 {plan['gold_change']:+,.0f}")
            st.markdown(f"### 比特币　¥{plan['target_bitcoin']:,.0f}")
            st.caption(f"当前市值 ¥{plan['current_bitcoin']:,.0f} · 调整 {plan['bitcoin_change']:+,.0f}")
            st.info("仅在计划检查日重新评估；候选比特币权重变化不足2个百分点时不交易。")


def render_history() -> None:
    plan = current_plan(); profile = plan["profile"]
    render_header("WALK-FORWARD EVIDENCE","历史参考方案","展示与当前风险区间最接近的历史检验结果，仅作参考，不代表未来收益。")
    path = data["q4_paths"].query("method == 'baseline' and profile == @profile")
    perf = data["q4_performance"].query("method == 'baseline' and profile == @profile").iloc[0]
    with st.container(border=True):
        a,b,c = st.columns(3)
        a.metric("净年化收益",f"{perf['cagr']:.2%}"); b.metric("年化波动",f"{perf['annualized_volatility']:.2%}"); c.metric("最大回撤",f"{perf['maximum_drawdown']:.2%}")
        fig = go.Figure(go.Scatter(x=path["date"],y=path["wealth"],mode="lines",line={"color":"#e7bb69","width":2},fill="tozeroy",fillcolor="rgba(231,187,105,.08)"))
        fig.update_layout(height=410,margin={"l":12,"r":12,"t":22,"b":12},paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(4,12,20,.2)",font={"color":"#aeb8c0"},xaxis={"gridcolor":"rgba(255,255,255,.06)"},yaxis={"gridcolor":"rgba(255,255,255,.06)","title":"组合净值"})
        st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def render_chat() -> None:
    plan = current_plan()
    render_header("JIANWEI Q&A","见微问答","连续提问配置方案、投资概念与风险。涉及你的方案时，见微会引用当前问卷计算出的配置。")
    with st.container(border=True):
        st.markdown(
            f'<div class="assistant-profile"><img class="assistant-avatar" src="{JIANWEI_AVATAR_URI}" alt="见微助手形象"><div><div class="assistant-profile-name">见微</div><div class="assistant-profile-role">你的投资问答助手<br>解释配置、投资概念与风险</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="result-banner">当前配置：黄金 <b>{plan["gold_weight"]:.1%}</b> · 比特币 <b>{plan["bitcoin_weight"]:.1%}</b> · 风险评分 <b>{plan["risk_score"]:.1f}</b> / 100。调整问卷后，此处会同步更新。</div>',
            unsafe_allow_html=True,
        )
        if not st.session_state.chat_messages:
            with st.chat_message("assistant", avatar=str(JIANWEI_AVATAR_PATH)):
                st.markdown("你好，我是见微。你可以问我：为什么这样配置？回撤是什么意思？比特币波动大时需要立刻调仓吗？也可以继续追问我的上一条回答。")
        for message in st.session_state.chat_messages:
            avatar = str(JIANWEI_AVATAR_PATH) if message["role"] == "assistant" else None
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

        prompt = st.chat_input("继续向见微提问；可以追问上一轮回答……")
        if prompt:
            st.session_state.chat_messages.append({"role":"user","content":prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            try:
                with st.chat_message("assistant", avatar=str(JIANWEI_AVATAR_PATH)):
                    with st.spinner("见微正在结合当前配置思考……"):
                        answer = generate_chat_answer(
                            st.session_state.chat_messages,
                            plan,
                            {"market_state":latest_state,"signal_date":allocation["latest_signal_date"],"data_as_of":allocation["as_of_date"],**current_answers()},
                        )
                    st.markdown(answer)
                st.session_state.chat_messages.append({"role":"assistant","content":answer})
            except Exception as exc:
                error_message = f"见微暂时无法回答：{exc}"
                with st.chat_message("assistant", avatar=str(JIANWEI_AVATAR_PATH)):
                    st.error(error_message)
                st.session_state.chat_messages.append({"role":"assistant","content":error_message})
        if st.session_state.chat_messages and st.button("清空本次问答",type="secondary"):
            st.session_state.chat_messages = []
            st.rerun()


def render_research() -> None:
    render_header("MODEL EVIDENCE","方法说明","从风险测度、因子检验、市场状态到走步回测，说明配置结论的计算依据。")
    q1 = frozen["Q1"]
    st.markdown(f'<div class="method-grid"><div class="method-item"><b>Q1 · 风险画像</b><span>黄金年化波动 {q1["gold"]["annualized_volatility"]:.1%}；比特币年化波动 {q1["bitcoin"]["annualized_volatility"]:.1%}。两类资产并非同一风险量级。</span></div><div class="method-item"><b>Q2 · 因子检验</b><span>滚动关联用于描述环境变化；FDR校正后不宣称稳定因果或价格预测能力。</span></div><div class="method-item"><b>Q3 · 状态识别</b><span>正常、宏观压力、加密压力三种状态只用于风险提示，不覆盖配置引擎权重。</span></div><div class="method-item"><b>Q4 · 走步回测</b><span>252日风险估计、21个共同报价日检查、2个百分点缓冲、单边10bp交易成本。</span></div></div>',unsafe_allow_html=True)
    st.warning("方法说明：个性化层不会让大模型自由给权重；确定性引擎只在三组正式配置校准锚点之间进行可审计的连续插值，并把结构化上下文交给见微解释。历史回测不保证未来表现。")


with st.sidebar:
    st.markdown('<div class="brand">衡域<span class="brand-sub">见微 · 投资问答</span></div>',unsafe_allow_html=True)
    navigation = st.radio("导航",["风险偏好问卷","我的配置方案","见微问答","历史参考方案","方法说明"],label_visibility="collapsed")
    api_ready = bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_API_BASE") and os.getenv("LLM_MODEL"))
    st.markdown(f'<div class="side-meta"><span class="status-chip">{state_names.get(latest_state,latest_state)}市场状态</span><br>根据你的回答计算<br>{"见微在线" if api_ready else "见微离线说明模式"}<br><br>历史参考 · 不构成投资建议</div>',unsafe_allow_html=True)

if navigation == "风险偏好问卷": render_assessment()
elif navigation == "我的配置方案": render_plan()
elif navigation == "见微问答": render_chat()
elif navigation == "历史参考方案": render_history()
else: render_research()
