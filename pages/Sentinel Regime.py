import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# --- 1. SETUP TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | Volume-Momentum", layout="wide")

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

# --- 2. ENGINE DE DADOS (AVM SYSTEM) ---
@st.cache_data(ttl=60)
def fetch_avm_data(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # MOMENTUM: Squeeze Histogram (LazyBear logic)
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    
    # VOLUME: Volume SMA Filter
    df['VOL_SMA'] = ta.sma(df['Volume'], length=20)
    df['HIGH_VOL'] = df['Volume'] > (df['VOL_SMA'] * 1.2) # 20% acima da média
    
    # TREND: ADX para força de direção
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    
    df = pd.concat([df, sqz, adx], axis=1)
    df.columns = [str(c).upper() for c in df.columns]
    return df

# --- 3. PROCESSAMENTO ---
df = fetch_avm_data("BTC-USD", "1d", "max")

# Identificar colunas dinâmicas
col_sqz_hist = [c for c in df.columns if 'SQZ_2' in c][0]
col_adx = [c for c in df.columns if 'ADX' in c][0]

# GATILHO COMBINADO (AVM SIGNAL)
# Condição: Momentum a subir (Hist > Hist anterior) + Volume Institucional (High Vol)
df['AVM_Signal'] = (df[col_sqz_hist] > df[col_sqz_hist].shift(1)) & (df['HIGH_VOL'] == True)

last_price = float(df['CLOSE'].iloc[-1])

# --- 4. GRÁFICO (REACTIVE VIEW) ---
fig = go.Figure()

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="Price", opacity=0.8
))

# SINAL AVM (O Diamante Institucional)
# Este sinal aparece quando VOLUME e MOMENTUM concordam
avm_pts = df[df['AVM_Signal']]
fig.add_trace(go.Scatter(
    x=avm_pts.index, y=avm_pts['LOW'] * 0.97,
    mode='markers',
    marker=dict(symbol='diamond', size=10, color='#00FBFF', line=dict(width=1, color='white')),
    name="AVM Confirmation"
))

# ROCKET (Explosão Final)
# Quando o AVM é confirmado por um ADX forte (> 20)
rockets = df[df['AVM_Signal'] & (df[col_adx] > 20)]
fig.add_trace(go.Scatter(
    x=rockets.index, y=rockets['LOW'] * 0.94,
    mode='markers+text', text="🚀", textposition="bottom center",
    name="Institutional Breakout"
))

# Layout e Zoom
visible_bars = 150
y_min = df['LOW'].iloc[-visible_bars:].min() * 0.92
y_max = df['HIGH'].iloc[-visible_bars:].max() * 1.08

fig.update_layout(
    template="plotly_dark", xaxis_rangeslider_visible=False, height=750,
    margin=dict(l=0, r=0, t=20, b=0),
    paper_bgcolor="#0B0E11", plot_bgcolor="#0B0E11",
    yaxis=dict(type="log", side="right", range=[__import__('math').log10(y_min), __import__('math').log10(y_max)]),
    xaxis=dict(range=[df.index[-visible_bars], df.index[-1]]),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- 5. DIAGNÓSTICO ---
st.markdown(f"""
    <div class="status-box">
        <h4 style="margin:0; color:#00FBFF;">AVM System Analysis:</h4>
        <p style="margin:5px 0 0 0; color:white;">
            O sistema <b>AVM (Alpha Volume-Momentum)</b> está a filtrar ruído. <br>
            • <b>Diamantes (♦):</b> Indicam entrada de volume institucional com momentum positivo (Early Signal). <br>
            • <b>Foguetes (🚀):</b> Indicam que o volume confirmou e a tendência (ADX) já está em fase de expansão.
        </p>
    </div>
    """, unsafe_allow_html=True)
