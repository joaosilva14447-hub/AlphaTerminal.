import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master de Elite
st.set_page_config(page_title="06 SOPR Pro Terminal", layout="wide")

# Paleta Institucional
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
def fetch_sopr_selective_glow():
    try:
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()

        # Extração de Dados (Lida com MultiIndex)
        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        volume = df['Volume']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
        
        data = pd.DataFrame({'price': price, 'volume': volume})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # Motor VWRP (Volume-Weighted Realized Price) - Janela 90 dias
        window = 90
        data['pv'] = data['price'] * data['volume']
        data['vwrp'] = data['pv'].rolling(window=window).sum() / data['volume'].rolling(window=window).sum()
        
        # SOPR Z-Score Calculation
        data['sopr_raw'] = data['price'] / data['vwrp']
        data['log_sopr'] = np.log(data['sopr_raw'].replace(0, np.nan)).ffill()
        
        z_window = 350
        data['mean'] = data['log_sopr'].rolling(window=z_window).mean()
        data['std'] = data['log_sopr'].rolling(window=z_window).std()
        
        # Inversão: Capitulação (Aqua) = Topo | Euforia (Blue) = Baixo
        data['z'] = ((data['mean'] - data['log_sopr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_sopr_selective_glow()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # 1. TÍTULO SÓLIDO (Sem Brilho)
    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓹𝓮𝓷𝓽 𝓞𝓾𝓽𝓹𝓾𝓽 𝓟𝓻𝓸𝓯𝓲𝓽 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # 2. LÓGICA DE SENTIMENTO COM BRILHO SELETIVO
    status, s_color, glow_style = "NEUTRAL", WHITE, ""

    if last_z >= 2.0:
        status, s_color = "💎 EXTREME CAPITULATION (BUY)", AQUA
        glow_style = f"text-shadow: 0 0 10px {AQUA}, 0 0 20px {AQUA};"
    elif 1.0 <= last_z < 2.0:
        status, s_color = "🔹 FEAR / PAIN", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0:
        status, s_color = "🔴 EXTREME EUPHORIA (SELL)", BLUE
        glow_style = f"text-shadow: 0 0 10px {BLUE}, 0 0 20px {BLUE};"
    elif -2.0 < last_z <= -1.0:
        status, s_color = "🔸 HIGH OPTIMISM", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SOPR Z-SCORE", f"{last_z:.2f} SD")
    # Apenas o Status recebe o Glow se for Extremo
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; {glow_style} font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # 3. CONSTRUÇÃO DO GRÁFICO COM BRILHO NAS LINHAS INFERIORES
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Preço (Linha Sólida)
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # --- EFEITO NEON NA LINHA Z-SCORE (Plot Inferior) ---
    # Camada de Brilho (Sombra)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], line=dict(color='white', width=5), opacity=0.2, hoverinfo='skip'), row=2, col=1)
    # Linha Principal
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Linhas de Escala com Brilho
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        # Linha de Glow (Mais larga)
        fig.add_hline(y=val, line=dict(color=color, width=4), opacity=0.2, row=2, col=1)
        # Linha de Base
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills (Zonas)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.35)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.35)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
