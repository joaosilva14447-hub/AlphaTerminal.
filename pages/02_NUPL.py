import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração ANUPL
st.set_page_config(page_title="ANUPL Terminal", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0F0F0F; }
    div[data-testid="stMetric"] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_anupl_data():
    df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    else:
        df = df[['Close']]
    df.columns = ['close']
    # SMA 365 como Proxy de Realized Price
    df['realized_proxy'] = df['close'].rolling(window=365).mean()
    # Fórmula: (Realized - Market) / Market (Invertido para o teu padrão)
    df['anupl'] = (df['realized_proxy'] - df['close']) / df['close']
    return df.dropna()

try:
    data = fetch_anupl_data()
    last_v = data['anupl'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE; font-family: serif;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais ANUPL
    status = "NEUTRAL"
    s_color = "#FFFFFF"
    if last_v >= 0.5: status, s_color = "💎 CAPITULATION (BUY)", "#00FBFF"
    elif 0.2 <= last_v < 0.5: status, s_color = "🔹 FEAR / HOPE", "rgba(0, 251, 255, 0.6)"
    elif last_v <= -0.5: status, s_color = "🔴 EUPHORIA (SELL)", "#3D5AFE"
    elif -0.2 >= last_v > -0.5: status, s_color = "🔸 OPTIMISM", "rgba(61, 90, 254, 0.6)"

    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("BTC PRICE", f"${data['close'].iloc[-1]:,.2f}")
    c2.metric("ANUPL", f"{last_v:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color};'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['close'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['anupl'], name="ANUPL", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Níveis de Stress
    fig.add_hline(y=-0.5, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=0.5, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)

    # Preenchimentos
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl'] <= -0.5, data['anupl'], -0.5), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.7)', line=dict(width=0)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl'] >= 0.5, data['anupl'], 0.5), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.7)', line=dict(width=0)), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=900, showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(row=2, col=1, autorange='reversed')
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro: {e}")
