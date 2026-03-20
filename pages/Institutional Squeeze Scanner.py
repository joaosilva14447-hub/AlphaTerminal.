import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO DE ESTILO ---
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

# --- 2. ENGINE DE DADOS (HEDGE FUND LOGIC) ---
@st.cache_data(ttl=60)
def fetch_and_calculate(symbol="BTC-USD"):
    # Download 7 dias de dados 1h
    df = yf.download(symbol, period="7d", interval="1h")
    
    # IMPORTANTE: Corrigir MultiIndex das versões novas do yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Cálculo ADX
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    # Cálculo Squeeze Momentum (LazyBear)
    sqz_df = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz_df], axis=1)
    
    # Limpeza de nomes de colunas para garantir strings simples
    df.columns = [str(c) for c in df.columns]
    return df

# --- 3. PROCESSAMENTO ---
try:
    df = fetch_and_calculate()
    
    # Identificação dinâmica de colunas (Anti-KeyError)
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    col_sqz_off = [c for c in df.columns if 'SQZ_OFF' in c][0]
    
    last_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Close'].iloc[-2])
    last_adx = float(df[col_adx].iloc[-1])
    is_squeeze = int(df[col_sqz_on].iloc[-1]) == 1
    
except Exception as e:
    st.error(f"Erro na extração de dados: {e}")
    st.stop()

# --- 4. CABEÇALHO E MÉTRICAS ---
col_h1, col_h2, col_h3, col_h4 = st.columns([2,1,1,1])

with col_h1:
    st.title("⚖️ BTC Institutional Scanner")
    st.caption(f"Asset: BTC/USD | Terminal Time: {datetime.now().strftime('%H:%M:%S')}")

with col_h2:
    st.metric("PRICE", f"${last_price:,.2f}", f"{((last_price/prev_price)-1)*100:.2f}%")

with col_h3:
    st.metric("ADX (14)", f"{last_adx:.2f}", "Strong" if last_adx > 25 else "Weak")

with col_h4:
    vol_status = "SQUEEZE" if is_squeeze else "RELEASE"
    st.metric("VOLATILITY", vol_status, delta_color="normal" if is_squeeze else "inverse")

st.divider()

# --- 5. GRÁFICO INTERATIVO (ALPHA PALETTE) ---
fig = go.Figure()

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="BTC/USD"
))

# Sinais Visuais de Squeeze no Gráfico
sqz_on_pts = df[df[col_sqz_on] == 1]
sqz_off_pts = df[df[col_sqz_off] == 1]

# Pontos Vermelhos: Compressão (Squeeze ON)
fig.add_trace(go.Scatter(
    x=sqz_on_pts.index, y=sqz_on_pts['High'] * 1.01,
    mode='markers', marker=dict(color='#FF5252', size=5), name="Squeeze ON"
))

# Triângulos Aqua: Expansão (Squeeze Release)
fig.add_trace(go.Scatter(
    x=sqz_off_pts.index, y=sqz_off_pts['High'] * 1.015,
    mode='markers', marker=dict(color='#00FBFF', size=10, symbol='triangle-up'), 
    name="Momentum Release"
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=0, r=10, t=0, b=0),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- 6. ANÁLISE INFERIOR ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("⚡ Momentum Diagnostic")
    if is_squeeze:
        st.warning("⚠️ **Market in Compression:** Institucionais estão a acumular posições. Aguarda o sinal de 'Triangle Up' no gráfico para confirmação de breakout.")
    elif last_adx > 25:
        st.info("🚀 **Trend Active:** O ADX indica uma tendência forte. O momentum está a favor da volatilidade atual.")
    else:
        st.write("😴 **Low Activity:** Mercado lateralizado sem força direcional clara.")
    
    st.write(f"ADX Trend Strength: {last_adx:.1f}%")
    st.progress(min(last_adx/100, 1.0))

with c2:
    status_color = "#00FBFF" if not is_squeeze else "#FF5252"
    st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; color:gray; font-size:12px;">SIGNAL STATUS</p>
        <h3 style="margin:0; color:white;">{'READY TO TRADE' if not is_squeeze and last_adx > 20 else 'MONITORING'}</h3>
        <p style="margin:0; color:{status_color}; font-size:14px;">
            {'Volatility Expansion Active' if not is_squeeze else 'Compression Phase'}
        </p>
    </div>
    """, unsafe_allow_html=True)

st.divider()
