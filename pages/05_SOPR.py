import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master de Elite
st.set_page_config(page_title="06 SOPR High-Fidelity", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_sopr_vwrp_engine():
    try:
        # 1. Download BTC Price and Volume
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()

        # Extração Robusta (MultiIndex Support)
        if isinstance(df.columns, pd.MultiIndex):
            price = df['Close']['BTC-USD']
            volume = df['Volume']['BTC-USD']
        else:
            price = df['Close']
            volume = df['Volume']
            
        data = pd.DataFrame({'price': price, 'volume': volume})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # --- MOTOR VWRP (Volume-Weighted Realized Price) ---
        # Calculamos o preço médio ponderado pelo volume (Janela de 90 dias)
        # Aproximação fiel ao SOPR On-Chain: Preço Atual / Preço Médio de Aquisição
        window = 90
        data['pv'] = data['price'] * data['volume']
        data['vwrp'] = data['pv'].rolling(window=window).sum() / data['volume'].rolling(window=window).sum()
        
        # SOPR = Preço de Venda (Atual) / Preço de Custo (VWRP)
        data['sopr_raw'] = data['price'] / data['vwrp']
        
        # 1. Compressão Logarítmica para Estabilidade
        data['log_sopr'] = np.log(data['sopr_raw'].replace(0, np.nan)).ffill()
        
        # 2. Motor Z-Score (Janela Institucional 350 dias para normalizar o sinal)
        z_window = 350
        data['mean'] = data['log_sopr'].rolling(window=z_window).mean()
        data['std'] = data['log_sopr'].rolling(window=z_window).std()
        
        # 3. Inversão de Paridade: DOR = Aqua (Cima) | PRAZER = Blue (Baixo)
        # Fórmula: $$Z = \frac{\mu - x}{\sigma}$$
        data['z'] = ((data['mean'] - data['log_sopr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except Exception as e:
        st.error(f"SOPR Engine Error: {str(e)}")
        return pd.DataFrame()

data = fetch_sopr_vwrp_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento (Baseada em Realização de Lucro/Prejuízo)
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0:
        status, s_color = "💎 EXTREME CAPITULATION (LOSS TAKING)", "#00FBFF"
    elif 1.0 <= last_z < 2.0:
        status, s_color = "🔹 FEAR / PAIN", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0:
        status, s_color = "🔴 EXTREME EUPHORIA (PROFIT TAKING)", "#3D5AFE"
    elif -2.0 < last_z <= -1.0:
        status, s_color = "🔸 HIGH OPTIMISM", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SOPR Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Escala 3 SD
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills 0.4 Opacidade
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
