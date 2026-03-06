import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master
st.set_page_config(page_title="03 MVRV Ratio Raw", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_mvrv_raw_data():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # --- CÁLCULO MVRV RATIO (RAW DATA) ---
        # Realized Price Proxy (Custo Médio de Aquisição)
        data['realized_price'] = data['price'].rolling(window=365).mean()
        
        # MVRV Ratio Pura: Preço de Mercado / Preço Realizado
        # Não há desvios padrão aqui, apenas o rácio direto.
        data['mvrv_ratio'] = data['price'] / data['realized_price']
        
        return data.dropna()
    except Exception as e:
        return pd.DataFrame()

data = fetch_mvrv_raw_data()

if not data.empty:
    last_ratio = data['mvrv_ratio'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #00FBFF;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓜𝓥𝓡𝓥 𝓡𝓪𝓽𝓲𝓸 (𝓡𝓪𝔀) ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais Baseada no Rácio Clássico
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_ratio >= 3.7: status, s_color = "🔴 MARKET TOP ZONE", "#3D5AFE"
    elif last_ratio <= 1.0: status, s_color = "💎 ACCUMULATION ZONE", "#00FBFF"

    c1, c2, c3 = st.columns([1, 1, 1.5])
    c1.metric("BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("MVRV RATIO", f"{last_ratio:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px;'>{status}</h1>", unsafe_allow_html=True)

    # Gráfico Multipainel
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Subplot 1: Preço do BTC
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Subplot 2: MVRV Ratio (Data Pura)
    fig.add_trace(go.Scatter(x=data.index, y=data['mvrv_ratio'], name="MVRV Ratio", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Referência do Rácio Clássico (3.7 para Topos, 1.0 para Fundos)
    fig.add_hline(y=3.7, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=2.4, line=dict(color="rgba(255,255,255,0.1)", width=1), row=2, col=1) # Mid-line

    # Fills de Convicção baseados no Rácio
    fig.add_trace(go.Scatter(x=data.index, y=[3.7]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['mvrv_ratio'] >= 3.7, data['mvrv_ratio'], 3.7), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=data.index, y=[1.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['mvrv_ratio'] <= 1.0, data['mvrv_ratio'], 1.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Clean
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    fig.update_yaxes(row=2, col=1, showgrid=False, title="MVRV Ratio")
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
