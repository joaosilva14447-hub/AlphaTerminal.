import streamlit as st
import pandas as pd

# Configuração de Estilo "Alpha Terminal"
st.set_page_config(page_title="Alpha Terminal | Institutional Scanner", layout="wide")

# CSS para Dark Mode Profissional e Tabela Limpa
st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00E676; }
    .status-box {
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #00E676;
        background-color: #1E1E1E;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO ---
st.title("⚖️ Institutional Trend Scanner (ADX + Squeeze)")
st.caption("Market Analysis Engine v2.0 | High-Frequency Data")

# --- LÓGICA DE DADOS (Simulação de Multi-Timeframe) ---
# Em produção, aqui entrariam as chamadas de API para cada TF
data_mtf = {
    "Timeframe": ["5m", "15m", "1h", "4h", "1D"],
    "Trend": ["Bearish 🔴", "Ranging ⚪", "Bullish 🟢", "Bullish 🟢", "Strong Bullish 🟢"],
    "ADX Value": [32.1, 13.72, 21.5, 28.9, 41.2],
    "Squeeze Status": ["Release 🟢", "Squeeze ON 🔴", "Squeeze ON 🔴", "Release 🟢", "Release 🟢"]
}
df_mtf = pd.DataFrame(data_mtf)

# --- DASHBOARD SUPERIOR (Métricas Principais) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Current ADX (15m)", value="13.72", delta="-2.1", delta_color="inverse")
with col2:
    st.metric(label="Market Volatility", value="Low", delta="Squeeze Active")
with col3:
    st.metric(label="Directional Bias", value="BULLISH", delta="Strong")
with col4:
    st.metric(label="Institutional Volume", value="High", delta="Accumulation")

st.divider()

# --- PONTO 1: MATRIZ MULTI-TIMEFRAME (MTF) ---
st.subheader("🌐 Multi-Timeframe Trend Matrix")
st.write("Análise de confluência para evitar 'falsos breakouts' em tempos menores.")

# Estilização da Tabela via Pandas Styler
def highlight_trend(val):
    if 'Bullish' in str(val): return 'color: #00E676'
    if 'Bearish' in str(val): return 'color: #FF5252'
    return 'color: #BDBDBD'

st.table(df_mtf.style.applymap(highlight_trend, subset=['Trend']))

# --- PONTO 2: SQUEEZE MOMENTUM & ADX ANALYSIS ---
st.subheader("⚡ Momentum & Volatility Analysis")

c1, c2 = st.columns([2, 1])

with c1:
    # Lógica de Diagnóstico
    st.info("**Hedge Fund Insight:** O ADX atual (13.72) indica uma zona de compressão (Ranging). O Squeeze está ativo (ON), o que sugere que uma expansão de volatilidade é iminente.")
    
    # Barra de força visual
    st.write("ADX Trend Strength")
    st.progress(0.137) # Representa 13.72/100

with c2:
    # Alerta de Sinal Institucional Customizado
    bg_color = "#00E676" # Verde se Bullish
    st.markdown(f"""
    <div class="status-box">
        <p style="margin:0; color:gray; font-size:12px;">SIGNAL STATUS</p>
        <h3 style="margin:0; color:white;">WAITING FOR BREAKOUT</h3>
        <p style="margin:0; color:{bg_color}; font-size:14px;">Directional Bias: LONG</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption("Alpha Terminal - Powered by PineScript Logic v6")
