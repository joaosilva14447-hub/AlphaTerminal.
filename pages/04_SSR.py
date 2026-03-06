import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master do Terminal
st.set_page_config(page_title="04 SSR Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_ssr_engine():
    try:
        # Fetch BTC and USDT (Proxy para Liquidez Global)
        df = yf.download(["BTC-USD", "USDT-USD"], period="max", interval="1d", progress=False)
        
        if df.empty: return pd.DataFrame()

        # Tratamento de MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            price_btc = df['Close']['BTC-USD']
            vol_usdt = df['Volume']['USDT-USD']
        else:
            price_btc = df['Close']
            vol_usdt = df['Volume']

        data = pd.DataFrame({'price': price_btc, 'usdt_vol': vol_usdt}).dropna()
        
        # --- CÁLCULO SSR PROXY ---
        data['usdt_vol'] = data['usdt_vol'].replace(0, np.nan).ffill()
        data['ssr_raw'] = data['price'] / (data['usdt_vol'].rolling(window=20).mean())
        
        # 1. Transformação Logarítmica
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        # 2. Motor Z-Score Reativo (Sem smoothing)
        window = 350
        data['mean'] = data['log_ssr'].rolling(window=window).mean()
        data['std'] = data['log_ssr'].rolling(window=window).std()
        
        # --- INVERSÃO PARA PARIDADE ---
        # Z+ (Aqua) = Alto Buying Power = OVERSOLD
        # Z- (Blue) = Baixo Buying Power = OVERBOUGHT
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_ssr_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # TÍTULO AJUSTADO PARA BLUE (#3D5AFE)
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # --- NOVA MATRIZ DE SENTIMENTO GRANULAR ---
    status, s_color = "NEUTRAL", "#FFFFFF"

    # Lógica OVERSOLD (Aqua - Liquidez Abundante)
    if last_z >= 2.0:
        status, s_color = "💎 EXTREME OVERSOLD (HIGH BUYING POWER)", "#00FBFF"
    elif 1.51 <= last_z < 2.0:
        status, s_color = "🔹 OVERSOLD (BUYING PRESSURE)", "rgba(0, 251, 255, 0.7)"
    elif 1.0 <= last_z <= 1.50:
        status, s_color = "🔹 SLIGHT OVERSOLD", "rgba(0, 251, 254, 0.5)"
    
    # Lógica OVERBOUGHT (Blue - Liquidez Escassa)
    elif last_z <= -2.0:
        status, s_color = "🔴 EXTREME OVERBOUGHT (LOW BUYING POWER)", "#3D5AFE"
    elif -1.99 <= last_z <= -1.51:
        status, s_color = "🔸 OVERBOUGHT (SELL PRESSURE)", "rgba(61, 90, 254, 0.8)"
    elif -1.50 <= last_z <= -1.0:
        status, s_color = "🔸 SLIGHT OVERBOUGHT", "rgba(61, 90, 254, 0.5)"
    
    else:
        status, s_color = "NEUTRAL / ACCUMULATION", "#FFFFFF"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SSR Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Multipainel
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Escala 3 SD
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills Sincronizados (0.4 Opacidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', 
        range=[-3.3, 3.3], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
