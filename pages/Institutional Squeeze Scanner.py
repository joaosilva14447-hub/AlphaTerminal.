import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | Institutional Scanner", layout="wide")

# Custom CSS for Professional Dark Theme
st.markdown("""
    <style>
    .main { background-color: #0B0E11; }
    [data-testid="stMetricValue"] { font-size: 26px; color: #00FBFF !important; }
    .status-box {
        padding: 15px; border-radius: 4px;
        border-left: 4px solid #00FBFF;
        background-color: #161A1E; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SELETOR DE TIMEFRAME ---
with st.sidebar:
    st.header("🎛️ Terminal Settings")
    tf_choice = st.selectbox(
        "Analysis Timeframe:",
        options=["1 Hour", "4 Hours", "1 Day", "1 Week"],
        index=2
    )
    
    tf_map = {
        "1 Hour": {"interval": "1h", "period": "7d", "zoom": 72},
        "4 Hours": {"interval": "4h", "period": "60d", "zoom": 100},
        "1 Day": {"interval": "1d", "period": "max", "zoom": 180},
        "1 Week": {"interval": "1wk", "period": "max", "zoom": 52}
    }
    current_tf = tf_map[tf_choice]

# --- 3. ENGINE DE DADOS ---
@st.cache_data(ttl=60)
def fetch_and_calculate(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Technicals
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    sqz = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, adx, sqz], axis=1)
    
    # Clean Column Names
    df.columns = [str(c).upper() for c in df.columns]
    return df

# --- 4. PROCESSAMENTO ---
try:
    df = fetch_and_calculate("BTC-USD", current_tf["interval"], current_tf["period"])
    
    # Identify Columns Dynamically
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    
    # Signals
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    last_price = float(last_row['CLOSE'])
    price_chg = ((last_price / float(prev_row['CLOSE'])) - 1) * 100
    last_adx = float(last_row[col_adx])
    is_squeeze = int(last_row[col_sqz_on]) == 1
    
except Exception as e:
    st.error(f"Data Engine Error: {e}")
    st.stop()

# --- 5. CABEÇALHO ---
c1, c2, c3, c4 = st.columns([2,1,1,1])
with c1:
    st.title("⚖️ BTC Institutional Scanner")
    st.caption(f"ASSET: BTC/USD | TF: {tf_choice} | LOG SCALE")
with c2:
    st.metric("PRICE", f"${last_price:,.2f}", f"{price_chg:.2f}%")
with c3:
    st.metric("ADX (TREND)", f"{last_adx:.2f}")
with c4:
    st.metric("VOLATILITY", "SQUEEZE" if is_squeeze else "EXPANSION")

# --- 6. GRÁFICO PRINCIPAL ---
fig = go.Figure()

# Candlesticks with User Palette
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', increasing_fillcolor='#00FBFF', # Aqua
    decreasing_line_color='#0051FF', decreasing_fillcolor='#0051FF', # Blue
    name="BTC Price", line=dict(width=1)
))

# Squeeze Points (Small Dots)
sqz_on = df[df[col_sqz_on] == 1]
fig.add_trace(go.Scatter(
    x=sqz_on.index, y=sqz_on['HIGH'] * 1.02,
    mode='markers', marker=dict(color='#FF2E63', size=4, opacity=0.6),
    name="Squeeze Phase", showlegend=False
))

# Breakout Signals (Institutional Rocket)
signals = df[df['Sqz_Release'] & (df[col_adx] > 20)]
fig.add_trace(go.Scatter(
    x=signals.index, y=signals['LOW'] * 0.96,
    mode='markers',
    marker=dict(symbol='triangle-up', size=12, color='#00FBFF', line=dict(width=1, color='white')),
    name="Institutional Breakout"
))

# Layout Fixes for Clarity
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=700,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="#0B0E11",
    plot_bgcolor="#0B0E11",
    yaxis=dict(
        type="log",
        side="right",
        gridcolor="#1E222D",
        zeroline=False,
        showline=True,
        linecolor="#2D323E",
        tickformat=",.0f"
    ),
    xaxis=dict(
        gridcolor="#1E222D",
        showline=True,
        linecolor="#2D323E"
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# Apply Zoom Strategy
zoom_start = df.index[-current_tf["zoom"]]
fig.update_xaxes(range=[zoom_start, df.index[-1]])

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- 7. FOOTER ANALYSIS ---
st.markdown(f"""
    <div class="status-box">
        <h4 style="margin:0; color:#00FBFF; font-size:16px;">Institutional Macro Analysis:</h4>
        <p style="margin:5px 0 0 0; color:#E0E0E0; font-size:14px;">
            Logarithmic trendlines confirmed. Trend Strength (ADX) is <b>{last_adx:.2f}</b>. 
            {"High compression (Squeeze) detected - awaiting volatility expansion." if is_squeeze else "Market in expansion phase - institutional momentum active."}
        </p>
    </div>
    """, unsafe_allow_html=True)
