import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | Logarithmic View", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00FBFF !important; }
    .status-box {
        padding: 20px; border-radius: 8px;
        border-left: 5px solid #00FBFF;
        background-color: #1E1E1E; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SELETOR DE TIMEFRAME ---
with st.sidebar:
    st.header("🎛️ Terminal Settings")
    tf_choice = st.selectbox(
        "Select Analysis Timeframe:",
        options=["1 Hour", "4 Hours", "1 Day", "1 Week"],
        index=2  # Default para 1 Day para melhor proveito do Log Chart
    )
    
    tf_map = {
        "1 Hour": {"interval": "1h", "period": "7d", "zoom": 100},
        "4 Hours": {"interval": "4h", "period": "60d", "zoom": 150},
        "1 Day": {"interval": "1d", "period": "max", "zoom": 500},
        "1 Week": {"interval": "1wk", "period": "max", "zoom": 150}
    }
    current_tf = tf_map[tf_choice]

# --- 3. ENGINE DE DADOS ---
@st.cache_data(ttl=60)
def fetch_and_calculate(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ADX & Squeeze
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    sqz_df = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz_df], axis=1)
    
    df.columns = [str(c) for c in df.columns]
    return df

# --- 4. PROCESSAMENTO ---
try:
    df = fetch_and_calculate("BTC-USD", current_tf["interval"], current_tf["period"])
    
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    last_adx = float(df[col_adx].iloc[-1])
    is_squeeze = int(df[col_sqz_on].iloc[-1]) == 1
    
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 5. CABEÇALHO ---
c_h1, c_h2, c_h3, c_h4 = st.columns([2,1,1,1])
with c_h1:
    st.title("⚖️ BTC Institutional Scanner")
    st.caption(f"BTC/USD | {tf_choice} | Logarithmic Scale Active")
with c_h2:
    st.metric("PRICE", f"${last_price:,.2f}", f"{((last_price/prev_price)-1)*100:.2f}%")
with c_h3:
    st.metric(f"ADX (Trend)", f"{last_adx:.2f}")
with c_h4:
    st.metric("VOLATILITY", "SQUEEZE" if is_squeeze else "RELEASE")

st.divider()

# --- 6. GRÁFICO PRINCIPAL (LOGARITHMIC) ---
fig = go.Figure()

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="Price"
))

# Squeeze Dots
sqz_on_pts = df[df[col_sqz_on] == 1]
fig.add_trace(go.Scatter(
    x=sqz_on_pts.index, y=sqz_on_pts['High'] * 1.05, # Ajuste de offset para Log
    mode='markers', marker=dict(color='#FF5252', size=3, opacity=0.4), 
    name="Squeeze"
))

# Signal Trigger (Rocket)
valid_triggers = df[df['Sqz_Release'] & (df[col_adx] > 20)]
fig.add_trace(go.Scatter(
    x=valid_triggers.index, y=valid_triggers['Low'] * 0.92, # Ajuste de offset para Log
    mode='markers+text',
    text="🚀", textposition="bottom center",
    marker=dict(color='#00FBFF', size=12, symbol='triangle-up', line=dict(width=1, color='white')), 
    name="Breakout"
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=750,
    margin=dict(l=0, r=10, t=0, b=0),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117",
    # --- ATIVAÇÃO DA ESCALA LOGARÍTMICA ---
    yaxis=dict(
        type="log",
        autorange=True,
        title="Price (Log Scale)",
        gridcolor="#2D2D2D"
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Ajuste do Zoom
fig.update_xaxes(range=[df.index[-current_tf["zoom"]], df.index[-1]], gridcolor="#2D2D2D")

st.plotly_chart(fig, use_container_width=True)

# --- 7. DIAGNÓSTICO ---
st.markdown(f"""
    <div class="status-box">
        <h4 style="margin:0; color:#00FBFF;">Macro Log Analysis:</h4>
        <p style="margin:0; color:white;">
            The logarithmic scale is now active. This view is optimal for identifying long-term institutional trend structures 
            and expansion phases. Current trend strength (ADX) is <b>{last_adx:.2f}</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
