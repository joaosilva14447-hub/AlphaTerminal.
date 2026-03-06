import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração de Interface Hedge Fund
st.set_page_config(page_title="03 MVRV Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_mvrv_precision_engine():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # 1. Base Realizada (Proxy 365d)
        data['realized'] = data['price'].rolling(window=365).mean()
        
        # 2. Rácio Logarítmico (Reativo)
        data['log_ratio'] = np.log(data['price'] / data['realized'])
        
        # 3. Motor Z-Score Invertido (Mean - Current)
        window = 350
        data['mean'] = data['log_ratio'].rolling(window=window).mean()
        data['std'] = data['log_ratio'].rolling(window=window).std()
        
        # Clipping a 3.5 para permitir overshoot visual na linha de 3
        data['z'] = ((data['mean'] - data['log_ratio']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_mvrv_precision_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓜𝓥𝓡𝓥 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # --- NOVA MATRIZ DE SENTIMENTO GRANULAR ---
    status, s_color = "NEUTRAL", "#FFFFFF"

    # Lógica OVERSOLD (Aqua - Topo do gráfico)
    if last_z >= 2.0:
        status, s_color = "💎 EXTREME OVERSOLD", "#00FBFF"
    elif 1.51 <= last_z < 2.0:
        status, s_color = "🔹 OVERSOLD", "rgba(0, 251, 255, 0.8)"
    elif 1.0 <= last_z <= 1.50:
        status, s_color = "🔹 SLIGHT OVERSOLD", "rgba(0, 251, 255, 0.5)"
    
    # Lógica OVERBOUGHT (Blue - Fundo do gráfico)
    elif last_z <= -2.0:
        status, s_color = "🔴 EXTREME OVERBOUGHT", "#3D5AFE"
    elif -1.99 <= last_z <= -1.51:
        status, s_color = "🔸 OVERBOUGHT", "rgba(61, 90, 254, 0.8)"
    elif -1.50 <= last_z <= -1.0:
        status, s_color = "🔸 SLIGHT OVERBOUGHT", "rgba(61, 90, 254, 0.5)"
    
    else:
        status, s_color = "NEUTRAL", "#FFFFFF"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("MVRV Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Construction
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Escala de 3 SDs
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills Sincronizados
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', 
        range=[-3.3, 3.3], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
