import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master de Elite
st.set_page_config(page_title="06 SOPR Neon Terminal", layout="wide")

# Cores Alpha Definidas
AQUA = "#00FBFF"
BLUE = "#3D5AFE"
WHITE = "#FFFFFF"

# CSS Injetado para Brilho Máximo
st.markdown(f"""
<style>
    .main {{ background-color: #050505; }}
    div[data-testid='stMetric'] {{ 
        background-color: #0A0A0A; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #222;
        box-shadow: 0 0 15px rgba(61, 90, 254, 0.1);
    }}
    /* Efeito de Brilho nos Títulos das Métricas */
    [data-testid="stMetricLabel"] {{
        color: {WHITE} !important;
        text-shadow: 0 0 5px rgba(255,255,255,0.5);
    }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_sopr_neon_engine():
    try:
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()

        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        volume = df['Volume']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
        
        data = pd.DataFrame({'price': price, 'volume': volume})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # Motor VWRP (Janela 90 dias)
        window = 90
        data['pv'] = data['price'] * data['volume']
        data['vwrp'] = data['pv'].rolling(window=window).sum() / data['volume'].rolling(window=window).sum()
        
        # SOPR Z-Score
        data['sopr_raw'] = data['price'] / data['vwrp']
        data['log_sopr'] = np.log(data['sopr_raw'].replace(0, np.nan)).ffill()
        
        z_window = 350
        data['mean'] = data['log_sopr'].rolling(window=z_window).mean()
        data['std'] = data['log_sopr'].rolling(window=z_window).std()
        
        # Inversão Alpha: Capitulação = Aqua (Cima) | Euforia = Blue (Baixo)
        data['z'] = ((data['mean'] - data['log_sopr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_sopr_neon_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # 1. TÍTULO COM GLOW DINÂMICO
    current_glow = BLUE if last_z < 0 else AQUA
    st.markdown(f"""
        <h1 style='text-align: center; color: {current_glow}; 
        text-shadow: 0 0 10px {current_glow}, 0 0 20px {current_glow}, 0 0 40px {current_glow}; 
        font-family: serif; font-size: 3rem; transition: 0.8s;'>
            ✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦
        </h1>
    """, unsafe_allow_html=True)

    # 2. SENTIMENTO COM BRILHO NEON
    status, s_color = "NEUTRAL", WHITE
    if last_z >= 2.0: status, s_color = "💎 EXTREME CAPITULATION", AQUA
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 PAIN ZONE", AQUA
    elif last_z <= -2.0: status, s_color = "🔴 EXTREME EUPHORIA", BLUE
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 PROFIT ZONE", BLUE

    c1, c2, c3 = st.columns([1, 1, 1.8])
    with c1: st.metric("PRICE", f"${data['price'].iloc[-1]:,.2f}")
    with c2: st.metric("Z-SCORE", f"{last_z:.2f}")
    with c3:
        st.markdown(f"""
            <h1 style='text-align: right; color: {s_color}; 
            text-shadow: 0 0 10px {s_color}, 0 0 20px {s_color}; 
            font-size: 28px; margin-top: 10px;'>{status}</h1>
        """, unsafe_allow_html=True)

    # 3. CONSTRUÇÃO DO GRÁFICO NEON
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])
    
    # Preço
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # --- EFEITO NEON Z-SCORE (3 CAMADAS) ---
    # Camada 1: O Brilho Exterior (Largo e muito transparente)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], line=dict(color=WHITE, width=8), opacity=0.1, hoverinfo='skip'), row=2, col=1)
    # Camada 2: O Brilho Médio
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], line=dict(color=WHITE, width=4), opacity=0.3, hoverinfo='skip'), row=2, col=1)
    # Camada 3: O Núcleo (A linha visível)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color=WHITE, width=1.5)), row=2, col=1)

    # Linhas de Escala Neon
    for val, color, name in [(-3, BLUE, "Limit"), (-2, BLUE, "Threshold"), (2, AQUA, "Threshold"), (3, AQUA, "Limit")]:
        fig.add_hline(y=val, line=dict(color=color, width=2), row=2, col=1)
        # Adiciona um "glow" às linhas horizontais também
        fig.add_hline(y=val, line=dict(color=color, width=6), opacity=0.2, row=2, col=1)

    # Fills (Zonas de Intensidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.3)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.3)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="#050505", 
        plot_bgcolor="#050505", 
        height=900, 
        margin=dict(l=50, r=50, t=30, b=50), 
        showlegend=False
    )
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.5, 3.5])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
