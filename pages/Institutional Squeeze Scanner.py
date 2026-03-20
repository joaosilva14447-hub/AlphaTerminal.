import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | BTC Engine", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #00FBFF !important; }
    .status-box {
        padding: 20px; border-radius: 8px;
        border-left: 5px solid #00FBFF;
        background-color: #1E1E1E; margin-bottom: 20px;
    }
    .stProgress > div > div > div > div { background-color: #00FBFF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ENGINE DE DADOS ---
@st.cache_data(ttl=60)
def fetch_and_calculate(symbol="BTC-USD"):
    df = yf.download(symbol, period="7d", interval="1h")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ADX para Força de Tendência
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    # Squeeze Momentum (BB vs KC)
    sqz_df = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz_df], axis=1)
    
    df.columns = [str(c) for c in df.columns]
    return df

# --- 3. PROCESSAMENTO DE SINAIS ---
try:
    df = fetch_and_calculate()
    
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    
    # LÓGICA DE GATILHO (Trigger Only): O momento exato em que o Squeeze DESLIGA
    # Queremos saber quando o valor anterior era 1 (Squeeze ON) e o atual é 0 (Release)
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    last_adx = float(df[col_adx].iloc[-1])
    is_squeeze = int(df[col_sqz_on].iloc[-1]) == 1
    
except Exception as e:
    st.error(f"Erro no processamento: {e}")
    st.stop()

# --- 4. CABEÇALHO ---
c_h1, c_h2, c_h3, c_h4 = st.columns([2,1,1,1])
with c_h1:
    st.title("⚖️ BTC Institutional Scanner")
    st.caption(f"Asset: BTC/USD | Terminal v2.1 | {datetime.now().strftime('%H:%M:%S')}")
with c_h2:
    st.metric("PRICE", f"${last_price:,.2f}", f"{((last_price/prev_price)-1)*100:.2f}%")
with c_h3:
    st.metric("ADX (14)", f"{last_adx:.2f}", "Strong" if last_adx > 25 else "Weak")
with c_h4:
    st.metric("VOLATILITY", "COMPRESSION" if is_squeeze else "EXPANSION")

st.divider()

# --- 5. GRÁFICO INTERATIVO (LIMPO) ---
fig = go.Figure()

# Candlesticks (Alpha Palette)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="BTC/USD"
))

# SINAIS DE COMPRESSÃO (Pontos pequenos e discretos)
sqz_on_pts = df[df[col_sqz_on] == 1]
fig.add_trace(go.Scatter(
    x=sqz_on_pts.index, y=sqz_on_pts['High'] * 1.005,
    mode='markers', marker=dict(color='#FF5252', size=3, opacity=0.4), 
    name="Accumulation (Squeeze)"
))

# SINAL DE GATILHO (Aparece apenas na PRIMEIRA vela de saída)
# Filtro Extra: Só mostramos se o ADX for minimamente relevante (>20)
valid_triggers = df[df['Sqz_Release'] & (df[col_adx] > 20)]

fig.add_trace(go.Scatter(
    x=valid_triggers.index, y=valid_triggers['Low'] * 0.98,
    mode='markers+text',
    text="🚀 RELEASE", textposition="bottom center",
    marker=dict(color='#00FBFF', size=12, symbol='triangle-up', 
                line=dict(width=1, color='white')), 
    name="Momentum Trigger"
))

fig.update_layout(
    template="plotly_dark", xaxis_rangeslider_visible=False, height=600,
    margin=dict(l=0, r=10, t=0, b=0), paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
    legend=dict(orientation="h", y=1.02, x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- 6. ANÁLISE DE MOMENTUM ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("⚡ Institutional Insight")
    if is_squeeze:
        st.warning("⚠️ **Low Volatility State:** O preço está em compressão. Evita trades de rompimento agora. Aguarda o triângulo Aqua para sinalizar a expansão.")
    elif df['Sqz_Release'].iloc[-1]:
        st.success("🚀 **Breakout Detected!** A volatilidade acabou de expandir. Se o ADX continuar a subir, o movimento terá continuidade.")
    else:
        st.info("🔄 **Trend in Progress:** O mercado já saiu do squeeze e está a seguir a tendência atual.")

with c2:
    st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; color:gray; font-size:12px;">SIGNAL STATUS</p>
        <h3 style="margin:0; color:white;">{'MONITORING' if is_squeeze else 'VOLATILITY ACTIVE'}</h3>
        <p style="margin:0; color:#00FBFF; font-size:14px;">ADX Power: {last_adx:.1f}</p>
    </div>
    """, unsafe_allow_html=True)
