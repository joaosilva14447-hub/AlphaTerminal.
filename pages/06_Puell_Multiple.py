import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Configuração de Autoridade
st.set_page_config(page_title="Alpha Terminal | Puell Multiple", layout="wide")

AQUA, BLUE = "#00FBFF", "#3D5AFE"

st.markdown(f"""
<style>
    .main {{ background-color: #0F0F0F; }}
    h1 {{ font-family: 'Inter', sans-serif; color: {BLUE}; text-align: center; }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_alpha_puell_data():
    try:
        # Download limpo
        raw = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if raw.empty: return None
        
        # Eliminação de MultiIndex (Padrão 2026)
        df = raw.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Extração de Preço Unitário
        data = pd.DataFrame(index=df.index)
        data['price'] = df['Close'].astype(float)
        
        # Lógica de Emissão (Protocolo Bitcoin)
        def calc_reward(dt):
            if dt < pd.Timestamp('2012-11-28'): return 50.0
            if dt < pd.Timestamp('2016-07-09'): return 25.0
            if dt < pd.Timestamp('2020-05-11'): return 12.5
            if dt < pd.Timestamp('2024-04-20'): return 6.25
            return 3.125
            
        data['daily_issuance'] = [calc_reward(d) * 144 for d in data.index]
        data['revenue_usd'] = data['daily_issuance'] * data['price']
        
        # Cálculo do Puell Multiple (Média 365 dias)
        # Usamos min_periods=1 para não apagar dados recentes se houver falhas no histórico
        data['ma_365'] = data['revenue_usd'].rolling(window=365, min_periods=180).mean()
        data['puell'] = data['revenue_usd'] / data['ma_365']
        
        # Normalização Z-Score (350 dias)
        data['log_puell'] = np.log(data['puell'].replace(0, np.nan))
        data['z_mean'] = data['log_puell'].rolling(window=350, min_periods=100).mean()
        data['z_std'] = data['log_puell'].rolling(window=350, min_periods=100).std()
        
        # Z-Score Final (Invertido: Alta Capitulação = Topo do Gráfico)
        data['z'] = ((data['z_mean'] - data['log_puell']) / data['z_std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['price', 'z'])
    except:
        return None

# --- EXECUÇÃO ---
data = get_alpha_puell_data()

if data is not None:
    last_z = data['z'].iloc[-1]
    
    # Dashboard Metrics
    st.markdown(f"<h1>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    col2.metric("Z-SCORE", f"{last_z:.2f} SD")
    
    status = "NEUTRAL"
    s_color = "white"
    if last_z >= 2.0: status, s_color = "💎 CAPITULATION (BUY)", AQUA
    elif last_z <= -2.0: status, s_color = "🔴 EUPHORIA (SELL)", BLUE
    col3.subheader(f":{s_color}[{status}]")

    # Plot
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Preço (Log)
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Z-Score
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)
    
    # Zonas de Stress (Fills)
    fig.add_hline(y=2.0, line=dict(color=AQUA, dash="dash"), row=2, col=1)
    fig.add_hline(y=-2.0, line=dict(color=BLUE, dash="dash"), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=800, showlegend=False, paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F")
    fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1) # Inversão Alpha
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Engine Timeout: Yahoo Finance data stream interrupted. Clear cache and retry.")
