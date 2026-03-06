import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# High-Performance Terminal Config
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

@st.cache_data(ttl=3600)
def fetch_puell_pro_clean_engine():
    try:
        # 1. Download de Dados com tratamento MultiIndex
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()
        
        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        data = pd.DataFrame({'price': price})
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
        
        # 3. DIFERENCIAÇÃO: Ajuste por Volatilidade de 30 dias
        # Filtra o "ruído" do preço simples para focar no stress dos mineradores
        vol = data['price'].pct_change().rolling(window=30).std()
        data['adj_issuance'] = data['issuance_usd'] / (1 + vol)
        
        # 4. Cálculo do Rácio (Puell) e Normalização Macro (350d)
        data['ma_issuance'] = data['adj_issuance'].rolling(window=365).mean()
        data['puell_raw'] = data['adj_issuance'] / data['ma_issuance']
        
        data['log_p'] = np.log(data['puell_raw'].replace(0, np.nan)).ffill()
        window = 350
        data['mean'] = data['log_p'].rolling(window=window).mean()
        data['std'] = data['log_p'].rolling(window=window).std()
        
        # Inversão Alpha: Z+ (Aqua/Cima) = Capitulação | Z- (Blue/Baixo) = Euforia
        data['z'] = ((data['mean'] - data['log_p']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_puell_pro_clean_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento Sólida
    status, s_color = "NEUTRAL", WHITE
    if last_z >= 2.0: status, s_color = "💎 MINER CAPITULATION (BUY)", AQUA
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 MINER REVENUE STRESS", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0: status, s_color = "🔴 MINER EUPHORIA (SELL)", BLUE
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 HIGH REVENUE EXPANSION", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Construção do Plot
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Painel 1: Preço em Escala Logarítmica
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Painel 2: Oscilador Z-Score
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Linhas de Fronteira Institucionais
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
    
    # Escala Invertida: Capitulação em Cima, Euforia em Baixo
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', 
        range=[-3.3, 3.3], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
