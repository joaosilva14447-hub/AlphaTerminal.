import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import numpy as np

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | Matrix Scanner", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0B0E11; }
    .status-box {
        padding: 15px; border-radius: 4px;
        border-left: 4px solid #00FBFF;
        background-color: #161A1E; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE DE DADOS (MATRIX LOGIC) ---
@st.cache_data(ttl=60)
def fetch_matrix_data(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # --- CAMADA 1: MOMENTUM (Squeeze Pro Histogram) ---
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz], axis=1)
    col_hist = [c for c in df.columns if 'SQZ_2' in c][0]
    
    # --- CAMADA 2: VOLUME ROBUSTO (Z-Score & SMA) ---
    # Calculamos o desvio padrão do volume para ignorar variações normais
    df['VOL_SMA'] = ta.sma(df['Volume'], length=20)
    df['VOL_STD'] = df['Volume'].rolling(window=20).std()
    df['VOL_ZSCORE'] = (df['Volume'] - df['VOL_SMA']) / df['VOL_STD']
    
    # --- CAMADA 3: FILTRO DE PREÇO (VWAP ou EMA 21) ---
    df['EMA21'] = ta.ema(df['Close'], length=21)
    
    # --- LÓGICA DE SINAIS (MATRIX CONFLUENCE) ---
    # BULLISH: Momentum acelerando + Volume forte (Z-Score > 1) + Preço > EMA21
    df['Signal_Bull'] = (df[col_hist] > df[col_hist].shift(1)) & \
                        (df['VOL_ZSCORE'] > 1.0) & \
                        (df['CLOSE'] > df['EMA21'])
    
    # CASH: Momentum perdendo força + Volume diminuindo (ou Preço < EMA21)
    # Sinaliza saída quando a "energia" do movimento acaba
    df['Signal_Cash'] = (df[col_hist] < df[col_hist].shift(1)) & \
                        (df['CLOSE'] < df['HIGH'].rolling(3).max() * 0.98) # Proteção de Lucro
    
    df.columns = [str(c).upper() for c in df.columns]
    return df

# --- 3. PROCESSAMENTO ---
df = fetch_matrix_data("BTC-USD", "1d", "max")

# --- 4. GRÁFICO (REACTIVE VIEW) ---
fig = go.Figure()

# Candlesticks Institucionais (Aqua/Blue)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="Price", opacity=0.9
))

# SINAL BULLISH (Diamante Aqua - Momentum + Volume Fusion)
bull_pts = df[df['SIGNAL_BULL']]
fig.add_trace(go.Scatter(
    x=bull_pts.index, y=bull_pts['LOW'] * 0.97,
    mode='markers',
    marker=dict(symbol='diamond', size=12, color='#00FBFF', line=dict(width=1, color='white')),
    name="Institutional Entry"
))

# SINAL CASH (Ícone de Moeda/Círculo Blue - Exaustão)
cash_pts = df[df['SIGNAL_CASH'] & df['SIGNAL_BULL'].shift(3).rolling(10).max()] # Apenas após um sinal bull
fig.add_trace(go.Scatter(
    x=cash_pts.index, y=cash_pts['HIGH'] * 1.03,
    mode='markers+text', text="Cash", textposition="top center",
    marker=dict(symbol='circle', size=8, color='#0051FF', line=dict(width=1, color='white')),
    name="Exit / Profit Take"
))

# --- 5. LAYOUT E ZOOM ---
visible_bars = 180 # Janela de visualização institucional
y_min = df['LOW'].iloc[-visible_bars:].min() * 0.95
y_max = df['HIGH'].iloc[-visible_bars:].max() * 1.05

fig.update_layout(
    template="plotly_dark", xaxis_rangeslider_visible=False, height=800,
    margin=dict(l=0, r=0, t=20, b=0),
    paper_bgcolor="#0B0E11", plot_bgcolor="#0
