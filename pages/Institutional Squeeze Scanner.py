 import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Alpha Terminal | Early Momentum", layout="wide")

# --- ENGINE DE DADOS (Otimizado para Reatividade) ---
@st.cache_data(ttl=60)
def fetch_early_momentum(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 1. Squeeze Pro (LazyBear + Momentum Histogram)
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    # 2. ADX + Inclinação (Slope)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    # 3. Média Rápida para Gatilho (EMA 9)
    df['EMA9'] = ta.ema(df['Close'], length=9)
    
    df = pd.concat([df, sqz, adx_df], axis=1)
    df.columns = [str(c).upper() for c in df.columns]
    return df

# --- PROCESSAMENTO DE SINAIS PRECOCES ---
symbol = "BTC-USD"
df = fetch_early_momentum(symbol, "1d", "max")

# Identificar colunas (dinâmico por causa do pandas_ta)
col_adx = [c for c in df.columns if 'ADX' in c][0]
col_sqz_hist = [c for c in df.columns if 'SQZ_2' in c][0] # O histograma de momentum

# LÓGICA EARLY BIRD (Menos restritiva)
# Condição: Histograma a subir + ADX a apontar para cima + Preço acima da EMA9
df['ADX_Slope'] = df[col_adx].diff()
df['Early_Signal'] = (df[col_sqz_hist] > df[col_sqz_hist].shift(1)) & \
                     (df['ADX_Slope'] > 0) & \
                     (df['CLOSE'] > df['EMA9'])

# --- VISUALIZAÇÃO ---
fig = go.Figure()

# Preço (Aqua/Blue Palette)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF', name="Price"
))

# Sinais de Momentum Precoce (Círculos Alpha Blue)
early_pts = df[df['Early_Signal']]
fig.add_trace(go.Scatter(
    x=early_pts.index, y=early_pts['LOW'] * 0.98,
    mode='markers', marker=dict(symbol='circle', size=6, color='#00FBFF', opacity=0.5),
    name="Early Momentum Build"
))

# O Gatilho de Explosão (Rocket) - Agora disparando mais cedo
trigger_pts = df[df['Early_Signal'] & (df[col_adx] > 18)] # Reduzido de 20 para 18
fig.add_trace(go.Scatter(
    x=trigger_pts.index, y=trigger_pts['LOW'] * 0.95,
    mode='markers+text', text="🚀", textposition="bottom center",
    name="Institutional Entry"
))

# Layout Full Frame
visible_bars = 120
y_min = df['LOW'].iloc[-visible_bars:].min() * 0.95
y_max = df['HIGH'].iloc[-visible_bars:].max() * 1.05

fig.update_layout(
    template="plotly_dark", xaxis_rangeslider_visible=False, height=750,
    margin=dict(l=0, r=10, t=10, b=0),
    paper_bgcolor="#0B0E11", plot_bgcolor="#0B0E11",
    yaxis=dict(type="log", side="right", range=[__import__('math').log10(y_min), __import__('math').log10(y_max)]),
    xaxis=dict(range=[df.index[-visible_bars], df.index[-1]])
)

st.plotly_chart(fig, use_container_width=True)
