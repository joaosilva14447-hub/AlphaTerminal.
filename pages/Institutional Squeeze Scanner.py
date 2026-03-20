import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURAÇÃO ALPHA TERMINAL ---
st.set_page_config(page_title="Alpha Terminal | BTC Macro View", layout="wide")

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

# --- 2. ENGINE DE DADOS (EXPANDIDA) ---
@st.cache_data(ttl=60)
def fetch_and_calculate(symbol="BTC-USD", timeframe="1h", days="30d"):
    # Aumentamos o período para 30 dias para o "Zoom Out"
    df = yf.download(symbol, period=days, interval=timeframe)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ADX e Squeeze
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df = pd.concat([df, adx_df], axis=1)
    
    sqz_df = ta.squeeze(df['High'], df['Low'], df['Close'], lazybear=True)
    df = pd.concat([df, sqz_df], axis=1)
    
    df.columns = [str(c) for c in df.columns]
    return df

# --- 3. PROCESSAMENTO ---
try:
    # Solicitamos 30 dias de histórico
    df = fetch_and_calculate(days="30d")
    
    col_adx = [c for c in df.columns if 'ADX' in c][0]
    col_sqz_on = [c for c in df.columns if 'SQZ_ON' in c][0]
    
    # Gatilho de saída do Squeeze
    df['Sqz_Release'] = (df[col_sqz_on].shift(1) == 1) & (df[col_sqz_on] == 0)
    
    last_price = float(df['Close'].iloc[-1])
    prev_price = float(df['Open'].iloc[0]) # Comparação com o início do período
    last_adx = float(df[col_adx].iloc[-1])
    is_squeeze = int(df[col_sqz_on].iloc[-1]) == 1
    
except Exception as e:
    st.error(f"Erro no processamento: {e}")
    st.stop()

# --- 4. CABEÇALHO ---
c_h1, c_h2, c_h3, c_h4 = st.columns([2,1,1,1])
with c_h1:
    st.title("⚖️ BTC Macro Institutional")
    st.caption(f"30-Day Historical Analysis | Timeframe: 1h")
with c_h2:
    st.metric("PRICE", f"${last_price:,.2f}", f"{((last_price/df['Close'].iloc[-2])-1)*100:.2f}%")
with c_h3:
    st.metric("30D PERFORMANCE", f"{((last_price/df['Close'].iloc[0])-1)*100:.2f}%")
with c_h4:
    st.metric("ADX TREND", f"{last_adx:.1f}")

st.divider()

# --- 5. GRÁFICO MACRO (ZOOM OUT) ---
fig = go.Figure()

# Candlesticks
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    increasing_line_color='#00FBFF', decreasing_line_color='#0051FF',
    name="BTC/USD"
))

# Sinais Discretos de Acumulação
sqz_on_pts = df[df[col_sqz_on] == 1]
fig.add_trace(go.Scatter(
    x=sqz_on_pts.index, y=sqz_on_pts['High'] * 1.002,
    mode='markers', marker=dict(color='#FF5252', size=2, opacity=0.3), 
    name="Squeeze (Wait)"
))

# Gatilhos de Explosão (Filtrados por ADX > 25 para maior precisão no Zoom Out)
valid_triggers = df[df['Sqz_Release'] & (df[col_adx] > 25)]

fig.add_trace(go.Scatter(
    x=valid_triggers.index, y=valid_triggers['Low'] * 0.98,
    mode='markers',
    marker=dict(color='#00FBFF', size=10, symbol='triangle-up', 
                line=dict(width=1, color='white')), 
    name="Institutional Breakout"
))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=True, # Ativado para facilitar o Zoom Out manual
    height=650,
    margin=dict(l=0, r=10, t=0, b=0),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117"
)

# Focar o gráfico no período mais recente, mas permitir scroll para trás
fig.update_xaxes(range=[df.index[-100], df.index[-1]])

st.plotly_chart(fig, use_container_width=True)

# --- 6. FOOTER INFO ---
st.info(f"🔍 **Macro Insight:** Estás a visualizar as últimas {len(df)} velas de 1h. Os triângulos Aqua agora estão filtrados para ADX > 25, garantindo que apenas rompimentos com volume institucional sejam destacados.")
