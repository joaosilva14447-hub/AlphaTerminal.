import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. ESTA DEVE SER A PRIMEIRA LINHA ABSOLUTA DO SCRIPT
st.set_page_config(page_title="Alpha Terminal", layout="wide")

# --- DEFINIÇÕES TÉCNICAS ---
COLOR_AQUA = "#00FFAA"
COLOR_BLUE = "#0055FF"

# --- CSS SEGURO (Sem F-Strings complexas para evitar o TypeError) ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #161B22;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00FFAA;
    }
    </style>
    """, unsafe_html=True)

def get_data(tickers, tf="1h"):
    results = []
    for t in tickers:
        try:
            df = yf.download(t, period="60d", interval=tf, progress=False)
            
            # Limpeza de colunas (Correção para erro de MultiIndex do yfinance)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 30: continue

            # Cálculos robustos
            bb = ta.bbands(df['Close'], length=20)
            kc = ta.kc(df['High'], df['Low'], df['Close'], length=20)
            
            # Squeeze: BB dentro do KC (Usando iloc para evitar erros de nomes de colunas)
            sqz = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
            mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
            
            last_sqz = sqz.iloc[-1]
            last_mom = mom.iloc[-1]
            
            results.append({
                "TICKER": t,
                "PREÇO": round(df['Close'].iloc[-1], 2),
                "SQUEEZE": "🔴 ON" if last_sqz else "🟢 RELEASE",
                "MOMENTUM": "BULLISH" if last_mom > 0 else "BEARISH"
            })
        except:
            continue
    return pd.DataFrame(results)

# --- UI ---
st.title("🛡️ Alpha Institutional Scanner")

# Sidebar para inputs
with st.sidebar:
    input_tickers = st.text_area("Tickers (separados por vírgula)", "BTC-USD, ETH-USD, AAPL, GC=F")
    tf_choice = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    btn = st.button("SCAN")

tickers_list = [x.strip() for x in input_tickers.split(",")]

# Lógica de Execução
if btn:
    with st.spinner("A processar..."):
        df_results = get_data(tickers_list, tf_choice)
        
        if not df_results.empty:
            # Métricas rápidas
            c1, c2 = st.columns(2)
            c1.metric("Em Squeeze", len(df_results[df_results['SQUEEZE'] == "🔴 ON"]))
            c2.metric("Trend Bullish", len(df_results[df_results['MOMENTUM'] == "BULLISH"]))
            
            # Tabela Estilizada
            st.divider()
            
            def style_df(val):
                color = COLOR_AQUA if val in ["BULLISH", "🟢 RELEASE"] else COLOR_BLUE
                return f'color: {color}'

            st.dataframe(
                df_results.style.map(style_df, subset=["SQUEEZE", "MOMENTUM"]),
                use_container_width=True
            )
        else:
            st.error("Não foi possível obter dados. Verifica os tickers.")
