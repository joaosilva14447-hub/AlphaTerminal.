import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuração Master de Elite
st.set_page_config(page_title="08 Gaussian Ribbon Terminal", layout="wide")

# Paleta Alpha
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
def fetch_gaussian_engine():
    try:
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()
        
        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        data = pd.DataFrame({'price': price})
        
        # --- MOTOR GAUSSIANO (Simplified Filter) ---
        # Usamos 4 camadas de médias exponenciais para simular a curva de Gauss
        # Isto cria uma tendência muito mais "limpa" que uma EMA comum
        length = 100
        data['ema1'] = data['price'].ewm(span=length).mean()
        data['ema2'] = data['ema1'].ewm(span=length).mean()
        data['ema3'] = data['ema2'].ewm(span=length).mean()
        data['ema4'] = data['ema3'].ewm(span=length).mean()
        
        # O Ribbon é a combinação destas camadas
        data['ribbon_top'] = data['ema1']
        data['ribbon_bottom'] = data['ema4']
        
        # Lógica de Cor: Aqua se Preço > Ribbon, Blue se Preço < Ribbon
        data['trend'] = np.where(data['price'] > data['ribbon_top'], "Bullish", "Bearish")
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_gaussian_engine()

if not data.empty:
    current_trend = data['trend'].iloc[-1]
    t_color = AQUA if current_trend == "Bullish" else BLUE
    
    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓖𝓪𝓾𝓼𝓼𝓲𝓪𝓷 𝓣𝓻𝓮𝓷𝓭 𝓡𝓲𝓫𝓿𝓸𝓷 ✦</h1>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("TREND STATUS", current_trend)
    c3.markdown(f"<h1 style='text-align: right; color: {t_color}; font-size: 24px; margin-top: -5px;'>MARKET INERTIA: {current_trend.upper()}</h1>", unsafe_allow_html=True)

    # Gráfico de Preço com o Ribbon Sobreposto
    fig = go.Figure()

    # 1. Preço
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="BTC Price", line=dict(color='white', width=1.5)))

    # 2. O Gaussian Ribbon (Fill entre Top e Bottom)
    fig.add_trace(go.Scatter(x=data.index, y=data['ribbon_top'], line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(
        x=data.index, y=data['ribbon_bottom'], 
        fill='tonexty', 
        fillcolor='rgba(0, 251, 255, 0.2)' if current_trend == "Bullish" else 'rgba(61, 90, 254, 0.2)',
        line=dict(width=0), 
        name="Gaussian Ribbon"
    ))

    # 3. Linhas de Fronteira do Ribbon
    fig.add_trace(go.Scatter(x=data.index, y=data['ribbon_top'], line=dict(color=t_color, width=1, dash='dot'), showlegend=False))
    fig.add_trace(go.Scatter(x=data.index, y=data['ribbon_bottom'], line=dict(color=t_color, width=1, dash='dot'), showlegend=False))

    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="#0F0F0F", 
        plot_bgcolor="#0F0F0F", 
        height=800, 
        margin=dict(l=60, r=60, t=50, b=60),
        yaxis=dict(type="log", showgrid=False),
        xaxis=dict(showgrid=False)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
