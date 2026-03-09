import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. High-Performance Terminal Config
st.set_page_config(page_title="07 Puell Multiple Terminal", layout="wide")

# Definição de Cores Institucionais
AQUA = "#00FBFF"
BLUE = "#3D5AFE"
WHITE = "#FFFFFF"

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { 
        background-color: #161616; 
        padding: 20px; 
        border-radius: 5px; 
        border: 1px solid #333; 
    }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_puell_master_engine():
    try:
        # Download Robusto via Ticker para evitar erros de MultiIndex
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        # Extração de Preço Unitário
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # 2. Lógica de Recompensa de Bloco (Halvings)
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            elif d < pd.Timestamp('2016-07-09'): return 25.0
            elif d < pd.Timestamp('2020-05-11'): return 12.5
            elif d < pd.Timestamp('2024-04-20'): return 6.25
            else: return 3.125 # Recompensa atual em 2026
            
        data['reward'] = [get_reward(d) for d in data.index]
        data['issuance_usd'] = data['reward'] * 144 * data['price']
        
        # 3. Cálculo do Rácio Puell (Média 365d)
        data['ma_issuance'] = data['issuance_usd'].rolling(window=365).mean()
        data['puell_raw'] = data['issuance_usd'] / data['ma_issuance']
        
        # 4. Motor Z-Score Invertido (Janela 350d)
        data['log_p'] = np.log(data['puell_raw'].replace(0, np.nan)).ffill()
        window = 350
        data['mean'] = data['log_p'].rolling(window=window).mean()
        data['std'] = data['log_p'].rolling(window=window).std()
        
        # Inversão Alpha: Z Positivo (Capitulação) | Z Negativo (Euforia)
        data['z'] = ((data['mean'] - data['log_p']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_puell_master_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # AJUSTE: Título Blindado com Azul Institucional (MVRV Style)
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # --- MATRIZ DE SENTIMENTO GRANULAR ---
    status, s_color = "NEUTRAL", WHITE
    
    # Lógica OVERSOLD (Aqua - Capitulação de Mineradores)
    if last_z >= 2.0:
        status, s_color = "💎 MINER CAPITULATION (BUY)", AQUA
    elif 1.0 <= last_z < 2.0:
        status, s_color = "🔹 MINER STRESS", "rgba(0, 251, 255, 0.7)"
        
    # Lógica OVERBOUGHT (Blue - Euforia de Mineradores)
    elif last_z <= -2.0:
        status, s_color = "🔴 MINER EUPHORIA (SELL)", BLUE
    elif -1.99 <= last_z <= -1.0:
        status, s_color = "🔸 REVENUE EXPANSION", "rgba(61, 90, 254, 0.7)"
    
    else:
        status, s_color = "NEUTRAL", WHITE

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Construction
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Painel 1: Preço Logarítmico
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Painel 2: Oscilador Z-Score
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas Institucionais (3 SDs)
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills Sincronizados (Blue para Euforia / Aqua para Capitulação)
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
