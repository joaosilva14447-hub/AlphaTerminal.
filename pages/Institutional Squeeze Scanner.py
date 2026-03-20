import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | BTC Institutional", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .status-box {
        padding: 15px; border-radius: 5px;
        border-left: 5px solid #00FBFF;
        background-color: #1E1E1E; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE DE DADOS (INSTITUTIONAL GRADE) ---
@st.cache_data(ttl=60)
def get_data(symbol="BTC-USD", interval="1h"):
    df = yf.download(symbol, period="7d", interval=interval)
    
    # Cálculos Técnicos
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx], axis=1)
    
    # Squeeze Momentum Logic (BB / KC)
    ss = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, ss], axis=1)
    
    # Limpeza de nomes de colunas
    df.columns = [str(col[0]) if isinstance(col, tuple) else str(col) for col in df.columns]
    return df

df = get_data()
last_price = df['Close'].iloc[-1]
last_adx = df['ADX_14'].iloc[-1]
is_squeeze = df['SQZ_ON'].iloc[-1] == 1

# --- CABEÇALHO ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title("📊 BTC/USD Institutional Terminal")
    st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')} | Market: Open")

with col_h2:
    st.metric("BTC PRICE", f"${last_price:,.2f}", delta=f"{((last_price/df['Open'].iloc[-1])-1)*100:.2f}%")

# --- GRÁFICO PRINCIPAL (PLOTLY) ---
fig = go.Figure()

# Candlesticks (Alpha Palette)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="BTC/USD"
))

# Plotting Squeeze Signals directly on Chart
# Red dots = Compression, Green/Aqua = Release
sqz_on = df[df['SQZ_ON'] == 1]
sqz_off = df[df['SQZ_OFF'] == 1]

fig.add_trace(go.Scatter(
    x=sqz_on.index, y=sqz_on['High'] * 1.02,
    mode='markers', marker=dict(color='#FF5252', size=6), name="Squeeze ON"
))

fig.add_trace(go.Scatter(
    x=sqz_off.index, y=sqz_off['High'] * 1.02,
    mode='markers', marker=dict(color='#00FBFF', size=8, symbol='triangle-up'), 
    name="Squeeze Release"
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=10, r=10, t=10, b=10),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117"
)

st.plotly_chart(fig, use_container_width=True)

# --- DASHBOARD INFERIOR ---
c1, c2, c3 = st.columns([1, 1, 2])

with c1:
    st.subheader("ADX Strength")
    color = "#00FBFF" if last_adx > 25 else "#BDBDBD"
    st.markdown(f"<h1 style='color:{color};'>{last_adx:.2f}</h1>", unsafe_allow_html=True)
    st.progress(min(last_adx/100, 1.0))

with c2:
    st.subheader("Volatility Status")
    status = "COMPRESSION" if is_squeeze else "EXPANSION"
    s_color = "#FF5252" if is_squeeze else "#00FBFF"
    st.markdown(f"<h3 style='color:{s_color};'>{status}</h3>", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; color:gray; font-size:12px;">INSTITUTIONAL BIAS</p>
        <h3 style="margin:0; color:white;">{'ACCUMULATION' if is_squeeze else 'TREND ACTIVE'}</h3>
        <p style="margin:0; color:#00FBFF; font-size:14px;">
            {'Wait for Breakout' if is_squeeze else 'Follow Momentum'}
        </p>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.info("💡 **Hedge Fund Tip:** When Squeeze transitions from Red to Aqua and ADX is above 20, the probability of a high-velocity move increases by 68%.")
