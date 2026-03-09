import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Configuração Master de Elite
st.set_page_config(page_title="07 Puell Multiple Alpha", layout="wide")

# Cores Institucionais
AQUA = "#00FBFF"
BLUE = "#3D5AFE"
WHITE = "#FFFFFF"

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_puell_master_engine():
    try:
        # Download Robusto
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max")
        if df.empty: return pd.DataFrame()

        # Limpeza de Índices e Colunas (Garante compatibilidade total)
        data = pd.DataFrame(index=df.index)
        data['price'] = df['Close'].astype(float)
        data.index = pd.to_datetime(data.index).tz_localize(None)
        
        # 2. Protocolo de Emissão Bitcoin (Halvings)
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            if d < pd.Timestamp('2016-07-09'): return 25.0
            if d < pd.Timestamp('2020-05-11'): return 12.5
            if d < pd.Timestamp('2024-04-20'): return 6.25
            return 3.125 # Recompensa 2026
            
        data['issuance_coins'] = [get_reward(d) * 144 for d in data.index]
        data['issuance_usd'] = data['issuance_coins'] * data['price']
        
        # 3. Cálculo do Puell (Média 365)
        data['ma_issuance'] = data['issuance_usd'].rolling(window=365, min_periods=100).mean()
        data['puell_raw'] = data['issuance_usd'] / data['ma_issuance']
        
        # 4. Motor Z-Score (Janela 350) - Baseado na lógica SOPR
        data['log_p'] = np.log(data['puell_raw'].replace(0, np.nan)).ffill()
        z_window = 350
        data['mean'] = data['log_p'].rolling(window=z_window, min_periods=100).mean()
        data['std'] = data['log_p'].rolling(window=z_window, min_periods=100).std()
        
        # Inversão: Z Positivo (Aqua) = Capitulação/Compra | Z Negativo (Blue) = Euforia/Venda
        data['z'] = ((data['mean'] - data['log_p']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['price', 'z'])
    except Exception as e:
        st.error(f"Engine Error: {e}")
        return pd.DataFrame()

data = fetch_puell_master_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # --- MATRIZ DE SENTIMENTO E GLOW (Sincronizado com SOPR) ---
    status, s_color, glow_css = "NEUTRAL", WHITE, ""

    if last_z >= 2.0:
        status, s_color = "💎 MINER CAPITULATION (BUY)", AQUA
        glow_css = f"text-shadow: 0 0 10px {AQUA}, 0 0 20px {AQUA}, 0 0 30px #00FFFF;"
    elif 1.0 <= last_z < 2.0:
        status, s_color = "🔹 MINER STRESS", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0:
        status, s_color = "🔴 MINER EUPHORIA (SELL)", BLUE
        glow_css = f"text-shadow: 0 0 10px {BLUE}, 0 0 20px {BLUE}, 0 0 30px #3D5AFE;"
    elif -2.0 < last_z <= -1.0:
        status, s_color = "🔸 REVENUE EXPANSION", "rgba(61, 90, 254, 0.7)"

    # Título Dinâmico Alpha
       st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # --- PLOT DESIGN (SOPR ARCHITECTURE) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Preço
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Oscilador Z
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Níveis Institucionais
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # --- FILLS DINÂMICOS (Correção de Lógica) ---
    # Euforia (Zona Blue/Venda)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False, hoverinfo='skip'), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), 
                             fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    # Capitulação (Zona Aqua/Compra)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False, hoverinfo='skip'), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), 
                             fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=900, 
                      margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.5, 3.5])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
