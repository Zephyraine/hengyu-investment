
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# --- 页面配置 ---
st.set_page_config(
    page_title="黄金定价分析看板",
    page_icon="📈",
    layout="wide"
)

# --- 1. 数据加载与预处理 ---
@st.cache_data
def load_and_process_data():
    df = pd.read_excel('data/黄金定价_情绪合并版.xlsx')
    df_clean = df.dropna().copy()
    df_clean['日收益率'] = df_clean['黄金价格'].pct_change()
    df_clean['滚动波动率_60天'] = df_clean['日收益率'].rolling(60).std() * np.sqrt(252) * 100
    return df_clean

# --- 2. 模型训练与预测函数 ---
@st.cache_data
def train_model_and_predict(df_clean):
    X = df_clean[['美元指数', '美债收益率', 'emotion_factor']]
    y = df_clean['黄金价格']
    model_full = LinearRegression()
    model_full.fit(X, y)
    
    window = 252
    train_data = df_clean.iloc[-window-1:-1]
    X_train = train_data[['美元指数', '美债收益率', 'emotion_factor']]
    y_train = train_data['黄金价格']
    model_roll = LinearRegression()
    model_roll.fit(X_train, y_train)
    
    latest = df_clean.iloc[-1]
    X_latest = latest[['美元指数', '美债收益率', 'emotion_factor']].values.reshape(1, -1)
    
    predicted_tomorrow = model_roll.predict(X_latest)[0]
    fair_price = model_full.predict(X_latest)[0]
    
    return model_full, predicted_tomorrow, fair_price, latest

# --- 3. 加载数据 ---
df_clean = load_and_process_data()
model_full, predicted_tomorrow, fair_price, latest = train_model_and_predict(df_clean)

# --- 4. 标题与关键指标 ---
st.title("📊 黄金资产量化分析看板")
st.markdown("基于美元指数、美债收益率和情绪因子的三因子定价模型")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📅 报告日期", latest['日期'].strftime('%Y-%m-%d'))
with col2:
    st.metric("💰 当前金价", f"${latest['黄金价格']:.2f}")
with col3:
    st.metric("🎯 模型合理价格", f"${fair_price:.2f}", 
              delta=f"{((fair_price / latest['黄金价格'] - 1) * 100):.2f}%")
with col4:
    st.metric("📈 预测明日价格", f"${predicted_tomorrow:.2f}",
              delta=f"{((predicted_tomorrow / latest['黄金价格'] - 1) * 100):.2f}%")

st.divider()

# --- 5. 价格走势图 ---
st.subheader("📉 黄金价格 vs 模型拟合走势")
X_all = df_clean[['美元指数', '美债收益率', 'emotion_factor']]
df_clean['拟合价格'] = model_full.predict(X_all)

fig = px.line(df_clean, x='日期', y=['黄金价格', '拟合价格'],
              title='实际价格 vs 模型拟合价格',
              labels={'value': '价格 (美元/盎司)', 'variable': '图例'},
              color_discrete_map={'黄金价格': 'black', '拟合价格': 'blue'})
fig.add_scatter(x=[latest['日期']], y=[latest['黄金价格']], 
                mode='markers', marker=dict(color='red', size=10),
                name=f'最新: {latest["黄金价格"]:.0f}')
fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 6. 模型诊断 ---
st.subheader("🔍 模型诊断与解读")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**📋 模型方程**")
    st.code(f"金价 = {model_full.intercept_:.2f} + {model_full.coef_[0]:.2f}×美元指数 + {model_full.coef_[1]:.2f}×美债收益率 + {model_full.coef_[2]:.2f}×情绪因子")

with col2:
    st.markdown("**📊 模型表现**")
    r2 = model_full.score(X_all, df_clean['黄金价格'])
    st.metric("模型 R²", f"{r2:.4f}")

st.divider()

# --- 7. 黄金配置建议工具 ---
st.subheader("⚙️ 黄金配置建议工具")

risk_level = st.radio(
    "选择您的风险偏好：",
    ['保守', '稳健', '激进'],
    index=1,
    horizontal=True
)

stock_pct = st.slider(
    "您的股票仓位 (%)：",
    min_value=0, max_value=100, value=50, step=5
)

if risk_level == '保守':
    base = 20
elif risk_level == '稳健':
    base = 12
else:
    base = 8

adjustment = (stock_pct - 50) / 100 * 5
gold_pct = max(0, min(30, base + adjustment))

if st.button("💡 生成配置建议"):
    st.success(f"根据您的风险偏好（{risk_level}）和股票仓位（{stock_pct}%），建议黄金配置比例为：**{gold_pct:.1f}%**")

st.caption("📌 数据来源：Investing.com, Yahoo Finance, alternative.me | 模型：三因子线性回归")
