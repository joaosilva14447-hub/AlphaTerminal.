import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração de Interface Hedge Fund
st.set_page_config(page_title="02 NUPL Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_nupl_reactive_data():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        # Injeção de Preço Live
        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # 1. Motor de Cálculo NUPL
        data['ma_365'] = data['price'].rolling(window=365).mean()
        
        # --- REMOÇÃO DO SMOOTHING (VOLATILIDADE REAL) ---
        # Calculamos o rácio logarítmico diretamente sem a média móvel de 14 dias
        data['raw_ratio'] = np.log(data['ma_365'] / data['price'])
        
        # 2. Normalização Z-Score (Janela Macro 350)
        # Calculado sobre o sinal bruto para capturar o "ruído" institucional
        window = 350
        data['mean'] = data['raw_ratio'].rolling(window=window).mean()
        data['std'] = data['raw_ratio'].rolling(window=window).std()
        
        # Clipping a 3.5 para permitir o "overshoot" visual nas linhas de 3 SD
        data['z'] = ((data['raw_ratio'] - data['mean']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_nupl_reactive_data()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais (Sincronizada por SDS)
    status, s_color = "NEUTRAL / HOLD", "#FFFFFF"
    if last_z >= 2.0: 
        status, s_color = "💎 CAPITULATION (BUY ZONE)", "#00FBFF"
    elif last_z <= -2.0: 
        status, s_color = "🔴 EUPHORIA (SELL ZONE)", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.5])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("NUPL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 28px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Multipainel (DNA ACD)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Subplot 1: Preço do BTC
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Subplot 2: NUPL Z-Score (Reativo)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # --- ESCALA DE 3 SDS (FIXA) ---
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills Sincronizados (0.4 Opacidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Sincronizado
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    
    # --- AJUSTE DE ESCALA (3 SDS COM PERMISSÃO DE OVERSHOOT) ---
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', # Tops down, Bottoms up
        range=[-3.3, 3.3], # Espaço para o sinal ultrapassar ligeiramente a linha 3
        tickvals=[-3, -2, -1, 0, 1, 2, 3] # Apenas as 3 escalas principais
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
