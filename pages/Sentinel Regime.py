import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# --- 1. SETUP ---
st.set_page_config(page_title="Alpha Terminal | Lifecycle Scanner", layout="wide")

# --- 2. ENGINE DE DADOS (LIFECYCLE LOGIC) ---
@st.cache_data(ttl=60)
def fetch_lifecycle_data(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # MOMENTUM: Squeeze Histogram (Reatividade)
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    
    # VOLUME: SMA 20 + Rate of Change
    df['VOL_SMA'] = ta.sma(df['Volume'], length=20)
    
    # TREND: EMA 21 (Filtro de Tendência Institucional)
    df['EMA21'] = ta.ema(df['Close'], length=21)
    
    df = pd.concat([df, sqz], axis=1)
    df.columns = [str(c).upper() for c in df.columns]
    return df

# --- 3. PROCESSAMENTO DE SINAIS ---
df = fetch_lifecycle_data("BTC-USD", "1d", "max")
col_sqz_hist = [c for c in df.columns if 'SQZ_2' in c][0]

# LÓGICA DE ENTRADA (BULLISH)
# Momentum a crescer + Volume acima da média + Preço acima da EMA21
df['BULL_ENTRY'] = (df[col_sqz_hist] > df[col_sqz_hist].shift(1)) & \
                   (df['VOLUME'] > df['VOL_SMA']) & \
                   (df['CLOSE'] > df['EMA21'])

# LÓGICA DE SAÍDA/AVISO (CASH/EXHAUST)
# Momentum a cair + Volume a decrescer (Sinal de fraqueza no topo)
df['CASH_WARNING'] = (df[col_sqz_hist] < df[col_sqz_hist].shift(1)) & \
                     (df['VOLUME'] < df['VOLUME'].shift(1)) & \
                     (df['CLOSE'] > df['EMA21']) # Ainda em tendência, mas perdendo força

# --- 4. VISUALIZAÇÃO ---
fig = go.Figure()

# Preço
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF', name="Price"
))

# PLOT: BULLISH ENTRY (Diamante Aqua)
bull_pts = df[df['BULL_ENTRY'] & (df['BULL_ENTRY'].shift(1) == False)]
fig.add_trace(go.Scatter(
    x=bull_pts.index, y=bull_pts['LOW'] * 0.97,
    mode='markers', marker=dict(symbol='diamond', size=10, color='#00FBFF', line=dict(width=1, color='white')),
    name="Bullish Ignition"
))

# PLOT: CASH WARNING (Aviso de Liquidez - X Amarelo ou Círculo Laranja)
cash_pts = df[df['CASH_WARNING'] & (df['CASH_WARNING'].shift(1) == False)]
fig.add_trace(go.Scatter(
    x=cash_pts.index, y=cash_pts['HIGH'] * 1.03,
    mode='markers', marker=dict(symbol='x', size=8, color='#FFA500'),
    name="Cash/Exhaustion Warning"
))

# Configuração Full Frame (Zoom nos últimos 120 dias)
visible_bars = 120
y_min = df['LOW'].iloc[-visible_bars:].min() * 0.95
y_max = df['HIGH'].iloc[-visible_bars:].max() * 1.05

fig.update_layout(
    template="plotly_dark", height=750, margin=dict(l=0, r=0, t=10, b=0),
    xaxis_rangeslider_visible=False, paper_bgcolor="#0B0E11", plot_bgcolor="#0B0E11",
    yaxis=dict(type="log", side="right", range=[__import__('math').log10(y_min), __import__('math').log10(y_max)]),
    xaxis=dict(range=[df.index[-visible_bars], df.index[-1]]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- 5. DASHBOARD DE STATUS ---
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
        <div style="border-left: 4px solid #00FBFF; padding:10px; background:#161A1E;">
            <h5 style="color:#00FBFF; margin:0;">BULLISH IGNITION ♦</h5>
            <p style="font-size:13px; color:white; margin:0;">Volume confirmado + Momentum em aceleração. Entrada de capital institucional.</p>
        </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div style="border-left: 4px solid #FFA500; padding:10px; background:#161A1E;">
            <h5 style="color:#FFA500; margin:0;">CASH WARNING ✖</h5>
            <p style="font-size:13px; color:white; margin:0;">Divergência de Volume + Perda de Momentum. Risco de exaustão e proteção de capital.</p>
        </div>
    """, unsafe_allow_html=True)
