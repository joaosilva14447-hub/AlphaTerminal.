import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração de Interface Hedge Fund
st.set_page_config(page_title="03 NUPL Terminal", layout="wide")

# Definição de Cores Estáticas
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

@st.cache_data(ttl=120)
def fetch_nupl_clean_engine():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        # Injeção de Preço em Tempo Real
        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # --- LÓGICA DE DIFERENCIAÇÃO 180 DIAS (Long-Term Sentiment) ---
        data['realized_180'] = data['price'].rolling(window=180).mean()
        
        # Fórmula NUPL: (Market - Realized) / Market
        data['nupl_raw'] = (data['price'] - data['realized_180']) / data['price']
        
        # Motor Estatístico Macro (Janela 350 dias)
        window = 350
        data['mean'] = data['nupl_raw'].rolling(window=window).mean()
        data['std'] = data['nupl_raw'].rolling(window=window).std()
        
        # Z-Score Invertido: Aqua (DOR/Cima) | Blue (PRAZER/Baixo)
        data['z'] = ((data['mean'] - data['nupl_raw']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_nupl_clean_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # --- MATRIZ DE SENTIMENTO (Sem Glow) ---
    status, s_color = "NEUTRAL / ACCUMULATION", WHITE
    if last_z >= 2.0: status, s_color = "💎 MAX CAPITULATION (BUY)", AQUA
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 FEAR / PAIN", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0: status, s_color = "🔴 EXTREME EUPHORIA (SELL)", BLUE
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 OPTIMISM / BELIEF", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("NUPL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Construção do Plot (Sólido e Sem Brilho)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Preço
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Z-Score (Linha Única Sólida)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Linhas de Escala Puras
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Preenchimentos Sólidos (Fills)
    # Zona de Euforia (Blue)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    # Zona de Capitulação (Aqua)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    
    # Escala Invertida Padronizada
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', 
        range=[-3.3, 3.3], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
