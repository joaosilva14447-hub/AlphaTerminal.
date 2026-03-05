import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuração de Escala Unificada (Hedge Fund Standard)
@st.cache_data(ttl=300)
def get_unified_nupl():
    df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
    close = df['Close'].iloc[:, 0] if isinstance(df.columns, pd.MultiIndex) else df['Close']
    
    # Cálculo de Lucro/Prejuízo Relativo
    ma_365 = close.rolling(window=365).mean()
    raw_nupl = (close - ma_365) / close
    
    # NORMALIZAÇÃO PARA ESCALA ACD (Z-Score 350 dias)
    mean_nupl = raw_nupl.rolling(window=350).mean()
    std_nupl = raw_nupl.rolling(window=350).std()
    nupl_z = (raw_nupl - mean_nupl) / std_nupl
    
    return pd.DataFrame({"nupl_z": nupl_z}).dropna()

data = get_unified_nupl()
st.markdown("<h1 style='color: #3D5AFE;'>✦ NUPL: Unified Macro Scale</h1>", unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data['nupl_z'], line=dict(color='#3D5AFE', width=2)))

# Linhas de Referência Idênticas ao ACD
fig.add_hline(y=2, line_dash="dot", line_color="red", annotation_text="Extreme Premium")
fig.add_hline(y=-2, line_dash="dot", line_color="green", annotation_text="Extreme Discount")

fig.update_layout(template="plotly_dark", height=600, paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F")
st.plotly_chart(fig, use_container_width=True)
