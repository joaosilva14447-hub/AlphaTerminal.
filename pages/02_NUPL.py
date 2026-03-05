import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Institucional ANUPL Evolution
st.set_page_config(page_title="02 ANUPL Terminal", layout="wide")

st.markdown("<style>.main { background-color: #0F0F0F; } div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }</style>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_anupl_evolution():
    try:
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        df = df[['Close']] if not isinstance(df.columns, pd.MultiIndex) else df['Close']
        df.columns = ['close']
        
        # Cálculo ANUPL (Proxy Realized via SMA 365)
        df['realized_proxy'] = df['close'].rolling(window=365).mean()
        # Invertido: Realized > Market = Positivo (Oversold/Aqua)
        df['anupl'] = (df['realized_proxy'] - df['close']) / df['close']
        
        # CAMADA ESTATÍSTICA: SD sobre o próprio ANUPL
        df['anupl_mean'] = df['anupl'].rolling(window=350).mean()
        df['anupl_std'] = df['anupl'].rolling(window=350).std()
        
        # Bandas de Stress de Sentimento
        df['upper_3'] = -2.5 # Nível Fixo de Euforia Extrema
        df['upper_2'] = -1.5 # Nível Fixo de Otimismo
        df['lower_2'] = 1.5  # Nível Fixo de Medo
        df['lower_3'] = 2.5  # Nível Fixo de Capitulação
        
        return df.dropna()
    except: return pd.DataFrame()

data = fetch_anupl_evolution()

if not data.empty:
    last_v = data['anupl'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE; font-family: serif;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # MATRIZ DE SENTIMENTO REFINADA
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_v >= 2.0: status, s_color = "💎 CAPITULATION (AQUA)", "#00FBFF"
    elif 1.0 <= last_v < 2.0: status, s_color = "🔹 HOPE / ANXIETY", "rgba(0, 251, 255, 0.6)"
    elif last_v <= -2.0: status, s_color = "🔴 EUPHORIA (BLUE)", "#3D5AFE"
    elif -1.0 >= last_v > -2.0: status, s_color = "🔸 OPTIMISM / BELIEF", "rgba(61, 90, 254, 0.6)"

    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("BTC PRICE", f"${data['close'].iloc[-1]:,.2f}")
    c2.metric("SENTIMENT (SD)", f"{last_v:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color};'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # 1. PREÇO LOGARÍTMICO
    fig.add_trace(go.Scatter(x=data.index, y=data['close'], name="Price", line=dict(color='white', width=2)), row=1, col=1)

    # 2. ANUPL INDICATOR
    fig.add_trace(go.Scatter(x=data.index, y=data['anupl'], name="Sentiment", line=dict(color='#888', width=1.5)), row=2, col=1)

    # BANDS - SINALIZAÇÃO DE ZONAS (Estilo Institucional)
    # Upside (Blue Zone)
    fig.add_hline(y=-1.5, line=dict(color="#3D5AFE", width=1, dash="dot"), row=2, col=1)
    fig.add_hline(y=-2.5, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    
    # Downside (Aqua Zone)
    fig.add_hline(y=1.5, line=dict(color="#00FBFF", width=1, dash="dot"), row=2, col=1)
    fig.add_hline(y=2.5, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)

    # PREENCHIMENTO DINÂMICO DE PSICOLOGIA
    # Blue Fill (Extreme Euphoria)
    fig.add_trace(go.Scatter(x=data.index, y=[-1.5]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl'] <= -1.5, data['anupl'], -1.5), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.6)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Aqua Fill (Extreme Capitulation)
    fig.add_trace(go.Scatter(x=data.index, y=[1.5]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl'] >= 1.5, data['anupl'], 1.5), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.6)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, gridcolor="#222")
    fig.update_yaxes(row=2, col=1, gridcolor="#222", autorange='reversed', range=[-4, 4], title="Psychology SD")
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
