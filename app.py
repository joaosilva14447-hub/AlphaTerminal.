import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Institucional ACD
st.set_page_config(page_title="ACD Terminal", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0F0F0F; }
    div[data-testid="stMetric"] { 
        background-color: #161616; 
        padding: 20px; 
        border-radius: 5px; 
        border: 1px solid #333; 
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_alpha_data():
    df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    else:
        df = df[['Close']]
    df.columns = ['close']
    
    # MATEMÁTICA DE CICLO ACD
    df['log_price'] = np.log(df['close'])
    window = 350
    df['mean'] = df['log_price'].rolling(window=window).mean()
    df['std'] = df['log_price'].rolling(window=window).std()
    
    # Lógica ACD: Preço < Média = Positivo (Oversold) | Preço > Média = Negativo (Overbought)
    df['z_score'] = (df['mean'] - df['log_price']) / df['std']
    return df.dropna()

try:
    data = fetch_alpha_data()
    last_z = data['z_score'].iloc[-1]
    
    # Título Centralizado em Azul (#3D5AFE) Estilo "Italiano"
    st.markdown("<h1 style='text-align: center; color: #3D5AFE; font-family: serif;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓒𝔂𝓬𝓵𝓮 𝓓𝓮𝓿𝓲𝓪𝓽𝓲𝓸𝓷 ✦</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555; margin-bottom: 30px;'>Institutional Macro Cycle Monitor</p>", unsafe_allow_html=True)

    # --- NOVA MATRIZ DE SINAIS ACD ---
    status = "NEUTRAL"
    s_color = "#FFFFFF" # Branco para Neutro
    
    if last_z >= 2.0:
        status = "💎 OVERSOLD (BOTTOM)"
        s_color = "#00FBFF" # Aqua
    elif 1.0 <= last_z < 2.0:
        status = "🔹 SLIGHT OVERSOLD"
        s_color = "rgba(0, 251, 255, 0.6)" # Aqua Suave
    elif -1.0 < last_z <= -2.0 or last_z <= -2.0: # Ajuste para garantir leitura de Overbought
        if last_z <= -2.0:
            status = "🔴 OVERBOUGHT (TOP)"
            s_color = "#3D5AFE" # Blue
        else:
            status = "🔸 SLIGHT OVERBOUGHT"
            s_color = "rgba(61, 90, 254, 0.6)" # Blue Suave
    elif -1.0 >= last_z > -2.0:
        status = "🔸 SLIGHT OVERBOUGHT"
        s_color = "rgba(61, 90, 254, 0.6)"

    # Header de Métricas
    c1, c2, c3 = st.columns([1, 1, 1.2])
    with c1: st.metric("BITCOIN PRICE", f"${data['close'].iloc[-1]:,.2f}")
    with c2: st.metric("ACD LEVEL (SD)", f"{last_z:.2f}")
    with c3:
        st.markdown(f"<h1 style='text-align: right; color: {s_color}; margin-top: 10px; font-family: sans-serif;'>{status}</h1>", unsafe_allow_html=True)

    # --- CONSTRUÇÃO DO PLOT ---
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        row_heights=[0.65, 0.35]
    )

    # 1. BTC PRICE LOG CHART (65%)
    fig.add_trace(
        go.Scatter(x=data.index, y=data['close'], name="Price", line=dict(color='white', width=2.0)),
        row=1, col=1
    )

    # 2. ACD INDICATOR (35%)
    fig.add_trace(
        go.Scatter(x=data.index, y=data['z_score'], name="ACD", line=dict(color='#888', width=1.5)),
        row=2, col=1
    )

    # LIMITES DE SINAL (±1, ±2 e ±3 SD)
    # Zonas de Convicção (Tracejado Forte)
    fig.add_hline(y=-2.0, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=2.0, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)
    
    # Zonas "Slight" (Tracejado Fino/Ponto)
    fig.add_hline(y=-1.0, line=dict(color="rgba(61, 90, 254, 0.4)", width=1, dash="dot"), row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color="rgba(0, 251, 255, 0.4)", width=1, dash="dot"), row=2, col=1)
    
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1), row=2, col=1)

    # PREENCHIMENTO DINÂMICO (Trigger em ±2 SD para Convicção Máxima)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=data.index, y=np.where(data['z_score'] <= -2.0, data['z_score'], -2.0),
        fill='tonexty', fillcolor='rgba(61, 90, 254, 0.7)', line=dict(width=0), showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=data.index, y=np.where(data['z_score'] >= 2.0, data['z_score'], 2.0),
        fill='tonexty', fillcolor='rgba(0, 251, 255, 0.7)', line=dict(width=0), showlegend=False
    ), row=2, col=1)

    # LAYOUT
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F",
        height=1000, margin=dict(l=60, r=60, t=50, b=60),
        showlegend=False, dragmode="pan"
    )

    fig.update_yaxes(type="log", row=1, col=1, gridcolor="#222", title="BTC Price (Log)")
    fig.update_yaxes(
        row=2, col=1, gridcolor="#222", title="ACD Stress (SD)", 
        autorange='reversed', range=[-4, 4]
    )
    fig.update_xaxes(gridcolor="#222", range=[data.index[-1800], data.index[-1] + pd.Timedelta(days=60)])

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})

except Exception as e:
    st.error(f"Erro no Terminal: {e}")

