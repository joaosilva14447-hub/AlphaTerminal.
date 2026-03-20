import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | Full Frame", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0B0E11; }
    [data-testid="stMetricValue"] { font-size: 26px; color: #00FBFF !important; }
    .status-box {
        padding: 15px; border-radius: 4px;
        border-left: 4px solid #00FBFF;
        background-color: #161A1E; margin-bottom: 20px;
    }
    iframe { border: none; }
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
        "1 Hour": {"interval": "1h", "period": "7d", "zoom": 100},
        "4 Hours": {"interval": "4h", "period": "60d", "zoom": 150},
        "1 Day": {"interval": "1d", "period": "max", "zoom": 365}, # 1 Ano visível
        "1 Week": {"interval": "1wk", "period": "max", "zoom": 100}
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
    df.columns = [str(c).upper() for c in df.columns]
    return df.dropna(subset=['CLOSE'])

# --- 4. PROCESSAMENTO ---
try:
    df = fetch_and_calculate("BTC-USD", current_tf["interval"], current_tf["period"])
    
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_row = df.iloc[-1]
    last_price = float(last_row['CLOSE'])
    last_adx = float(last_row[col_adx])
    is_squeeze = int(last_row[col_sqz_on]) == 1
    
    # CÁLCULO DE RANGE PARA O ZOOM (O segredo para o Full Frame)
    visible_df = df.iloc[-current_tf["zoom"]:]
    y_min = visible_df['LOW'].min() * 0.98
    y_max = visible_df['HIGH'].max() * 1.02

except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 5. CABEÇALHO ---
c1, c2, c3, c4 = st.columns([2,1,1,1])
with c1:
    st.title("⚖️ BTC Institutional Scanner")
    st.caption(f"BTC/USD | {tf_choice} | Institutional Scale")
with c2:
    st.metric("PRICE", f"${last_price:,.2f}")
with c3:
    st.metric("ADX", f"{last_adx:.2f}")
with c4:
    st.metric("VOLATILITY", "SQUEEZE" if is_squeeze else "RELEASE")

# --- 6. GRÁFICO PRINCIPAL ---
fig = go.Figure()

# Candlesticks (Professional Styling)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['OPEN'], high=df['HIGH'], low=df['LOW'], close=df['CLOSE'],
    increasing_line_color='#00FBFF', increasing_fillcolor='#00FBFF',
    decreasing_line_color='#0051FF', decreasing_fillcolor='#0051FF',
    name="BTC Price"
))

# Squeeze Release Signals (Rockets)
signals = df[df['Sqz_Release'] & (df[col_adx] > 20)]
fig.add_trace(go.Scatter(
    x=signals.index, y=signals['LOW'],
    mode='markers+text',
    text="🚀", textposition="bottom center",
    marker=dict(size=12, color='#00FBFF'),
    name="Breakout"
))

# Configuração de Layout para Ocupar Espaço Total
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=800, # Aumentado para maior visibilidade
    margin=dict(l=0, r=0, t=10, b=0),
    paper_bgcolor="#0B0E11",
    plot_bgcolor="#0B0E11",
    yaxis=dict(
        type="log",
        side="right",
        gridcolor="#1E222D",
        range=[pd.Series(y_min).apply(lambda x: pd.np.log10(x)).iloc[0] if hasattr(pd, 'np') else pd.Series(y_min).map(lambda x: __import__('math').log10(x)).iloc[0], 
               pd.Series(y_max).apply(lambda x: pd.np.log10(x)).iloc[0] if hasattr(pd, 'np') else pd.Series(y_max).map(lambda x: __import__('math').log10(x)).iloc[0]],
        fixedrange=False # Permite que o utilizador mova o gráfico
    ),
    xaxis=dict(
        gridcolor="#1E222D",
        range=[df.index[-current_tf["zoom"]], df.index[-1]]
    ),
    legend=dict(visible=False)
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

# --- 7. STATUS ---
st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; color:white; font-size:14px;">
            <b>Institutional Note:</b> Dynamic Y-Axis scale is optimized for current volatility. 
            The chart now focuses exclusively on the price action relative to the selected window.
        </p>
    </div>
    """, unsafe_allow_html=True)
