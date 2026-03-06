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
def fetch_mvrv_3sd_engine():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        # Injeção de Preço Live
        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # 1. Base Realizada (Proxy 365d)
        data['realized'] = data['price'].rolling(window=365).mean()
        
        # 2. Rácio Logarítmico para compressão macro
        data['log_ratio'] = np.log(data['price'] / data['realized'])
        
        # 3. Suavização original (mantida sem alteração)
        data['smooth'] = data['log_ratio'].rolling(window=14).mean()
        
        # 4. Motor Z-Score Invertido (Mean - Current)
        window = 350
        data['mean'] = data['smooth'].rolling(window=window).mean()
        data['std'] = data['smooth'].rolling(window=window).std()
        
        # --- AJUSTE DE ESCALA 3-SD ---
        # Clipping rigoroso a 3.0 para que o sinal nunca ultrapasse as linhas
        data['z'] = ((data['mean'] - data['smooth']) / data['std']).clip(-3.0, 3.0)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_mvrv_3sd_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓜𝓥𝓡𝓥 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais (Paridade ACD/NUPL)
    status, s_color = "NEUTRAL / ACCUMULATION", "#FFFFFF"
    if last_z >= 2.0: 
        status, s_color = "💎 OVERSOLD (BUY ZONE)", "#00FBFF"
    elif last_z <= -2.0: 
        status, s_color = "🔴 OVERBOUGHT (SELL ZONE)", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.5])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("MVRV Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 28px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Construção do Plot
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # --- LINHAS DE ESCALA (APENAS 3 SDS) ---
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills Sincronizados (0.4 Opacidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Final Equalizado
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    
    # --- AJUSTE DE ESCALA RESTRITO ([-3, 3]) ---
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', 
        range=[-3.1, 3.1], # Pequena margem para a linha 3 não ficar colada à borda
        tickvals=[-3, -2, -1, 0, 1, 2, 3] # Apenas 3 SDs, sem as linhas 4 e 5
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
