import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | BTC Macro 2020", layout="wide")

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

# --- 2. ENGINE DE DADOS (HISTÓRICO LONGO) ---
@st.cache_data(ttl=3600) # Cache de 1 hora para dados históricos
def fetch_macro_data(symbol="BTC-USD"):
    # Download desde 2020 no timeframe Diário (1D)
    df = yf.download(symbol, start="2020-01-01", interval="1d")
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ADX (Tendência Macro)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    # Squeeze Momentum (Acumulação Macro)
    sqz_df = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz_df], axis=1)
    
    df.columns = [str(c) for c in df.columns]
    return df

# --- 3. PROCESSAMENTO ---
try:
    df = fetch_macro_data()
    
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    
    # Gatilho de saída (Sqz_Release)
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_price = float(df['Close'].iloc[-1])
    price_2020 = float(df['Close'].iloc[0])
    last_adx = float(df[col_adx].iloc[-1])
    is_squeeze = int(df[col_sqz_on].iloc[-1]) == 1
    
except Exception as e:
    st.error(f"Erro no processamento: {e}")
    st.stop()

# --- 4. CABEÇALHO MACRO ---
c_h1, c_h2, c_h3, c_h4 = st.columns([2,1,1,1])
with c_h1:
    st.title("⚖️ BTC Macro Historical Scanner")
    st.caption(f"Historical View since 2020 | Interval: 1 Day")
with c_h2:
    st.metric("CURRENT PRICE", f"${last_price:,.2f}")
with c_h3:
    perf = ((last_price/price_2020)-1)*100
    st.metric("PERF. SINCE 2020", f"{perf:,.0f}%", delta=f"{perf:,.2f}%")
with c_h4:
    st.metric("MACRO TREND (ADX)", f"{last_adx:.1f}")

st.divider()

# --- 5. GRÁFICO DIÁRIO (DESDE 2020) ---
fig = go.Figure()

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="BTC/USD"
))

# Sinais de Squeeze (Pontos de acumulação diária)
sqz_on_pts = df[df[col_sqz_on] == 1]
fig.add_trace(go.Scatter(
    x=sqz_on_pts.index, y=sqz_on_pts['High'] * 1.02,
    mode='markers', marker=dict(color='#FF5252', size=2, opacity=0.3), 
    name="Macro Compression"
))

# Gatilhos de Explosão Macro (Filtro ADX > 20 para evitar ruído diário)
valid_triggers = df[df['Sqz_Release'] & (df[col_adx] > 20)]

fig.add_trace(go.Scatter(
    x=valid_triggers.index, y=valid_triggers['Low'] * 0.95,
    mode='markers',
    marker=dict(color='#00FBFF', size=8, symbol='triangle-up', 
                line=dict(width=1, color='white')), 
    name="Volatility Breakout"
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=True, # Slider essencial para navegar anos de dados
    height=700,
    margin=dict(l=0, r=10, t=0, b=0),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117"
)

# Configurar o zoom inicial para os últimos 6 meses, mas com tudo carregado
fig.update_xaxes(range=[df.index[-180], df.index[-1]])

st.plotly_chart(fig, use_container_width=True)

# --- 6. INSIGHT INSTITUCIONAL ---
st.info("💡 **Hedge Fund Note:** Em gráficos diários, o sinal 'Release' (Aqua) seguido de um ADX crescente acima de 25 marca historicamente o início de 'Bull Runs' de vários meses.")
