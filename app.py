import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="Alpha Macro Terminal", layout="wide")

st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓜𝓪𝓬𝓻𝓸: 𝓒𝔂𝓬𝓵𝓮 𝓜𝓪𝓼𝓽𝓮𝓻 ✦</h1>", unsafe_allow_html=True)

@st.cache_data(ttl=86400) # Atualiza dados uma vez por dia
def get_data():
    # Puxa o histórico máximo do Bitcoin
    df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    else:
        df = df[['Close']]
    df.columns = ['close']
    
    # Cálculo de Ciclo (Log Z-Score 350 dias)
    df['log_price'] = np.log(df['close'])
    window = 350
    df['mean'] = df['log_price'].rolling(window=window).mean()
    df['std'] = df['log_price'].rolling(window=window).std()
    df['z_score'] = (df['log_price'] - df['mean']) / df['std']
    return df

try:
    data = get_data()
    current_z = data['z_score'].iloc[-1]
    current_p = data['close'].iloc[-1]

    # --- INDICADORES DE TOPO ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço BTC", f"${current_p:,.2f}")
    c2.metric("Z-Score Atual", f"{current_z:.2f}")
    
    status = "NEUTRO"
    color = "white"
    if current_z <= -1.5:
        status = "💎 GENERATIONAL BOTTOM (BUY)"
        color = "#09DBB5"
    elif current_z >= 1.8:
        status = "🔴 CYCLE PEAK (SELL)"
        color = "#3D5AFE"
    
    c3.markdown(f"**ESTADO:** <span style='color:{color};'>{status}</span>", unsafe_allow_html=True)

    # --- GRÁFICO INTERATIVO ---
    fig = go.Figure()
    # Linha do Z-Score
    fig.add_trace(go.Scatter(x=data.index, y=data['z_score'], name="Z-Score", line=dict(color='white', width=1.5)))
    
    # Zonas Alpha
    fig.add_hrect(y0=-3, y1=-1.5, fillcolor="#09DBB5", opacity=0.3, line_width=0, annotation_text="COMPRA")
    fig.add_hrect(y0=1.8, y1=5, fillcolor="#3D5AFE", opacity=0.3, line_width=0, annotation_text="VENDA")
    
    fig.update_layout(
        template="plotly_dark", 
        height=600, 
        paper_bgcolor="#0F0F0F", 
        plot_bgcolor="#0F0F0F",
        yaxis_title="Z-Score Stress Level",
        xaxis_title="Histórico (2010 - 2026)"
    )
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")