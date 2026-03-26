import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. Configuração inicial (Deve ser a primeira coisa)
try:
    st.set_page_config(page_title="Alpha Institutional", layout="wide")
except:
    pass

# --- CSS SEGURO (Sem F-Strings para evitar o erro de TypeError) ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #161B22 !important;
        padding: 15px !important;
        border-radius: 10px !important;
        border-left: 5px solid #00FFAA !important;
    }
    </style>
    """, unsafe_html=True)

def get_institutional_data(tickers, interval="1h"):
    scanner_results = []
    
    for ticker in tickers:
        try:
            # Download e limpeza imediata do MultiIndex
            df = yf.download(ticker, period="60d", interval=interval, progress=False)
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 30:
                continue
            
            # Cálculo dos indicadores
            bb = ta.bbands(df['Close'], length=20, std=2.0)
            kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
            
            if bb is None or kc is None:
                continue

            # LÓGICA DE SQUEEZE (Usando iloc para ignorar nomes de colunas)
            # bb.iloc[:, 0] é a banda inferior, bb.iloc[:, 2] é a superior
            sqz_on = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
            
            # Momentum
            mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
            
            # Volume Health
            vol_sma = ta.sma(df['Volume'], 20)
            vol_weak = (df['Close'] > df['Close'].shift(1)) & (df['Volume'] < vol_sma)
            
            last_idx = -1
            scanner_results.append({
                "TICKER": ticker,
                "PREÇO": round(float(df['Close'].iloc[last_idx]), 2),
                "SQUEEZE": "🔴 ON" if sqz_on.iloc[last_idx] else "🟢 RELEASE",
                "MOMENTUM": "BULLISH" if mom.iloc[last_idx] > 0 else "BEARISH",
                "VOL HEALTH": "⚠️ WEAK" if vol_weak.iloc[last_idx] else "✅ HEALTHY"
            })
        except Exception as e:
            print(f"Erro em {ticker}: {e}")
            continue
            
    return pd.DataFrame(scanner_results)

# --- INTERFACE ---
st.title("🛡️ Alpha Institutional Scanner")

with st.sidebar:
    st.header("Configurações")
    assets = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, AAPL, GC=F")
    tf = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
    run_btn = st.button("ATUALIZAR")

tickers_list = [t.strip() for t in assets.split(",")]

# Execução
if run_btn:
    with st.spinner("A analisar..."):
        df_final = get_institutional_data(tickers_list, tf)
        
        if not df_final.empty:
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("Em Squeeze", len(df_final[df_final['SQUEEZE'] == "🔴 ON"]))
            c2.metric("Momentum Bull", len(df_final[df_final['MOMENTUM'] == "BULLISH"]))
            c3.metric("Volume OK", len(df_final[df_final['VOL HEALTH'] == "✅ HEALTHY"]))
            
            st.divider()

            # Tabela Estilizada (Usando map em vez de applymap para compatibilidade)
            def color_logic(val):
                if val in ["BULLISH", "✅ HEALTHY", "🟢 RELEASE"]: return "color: #00FFAA"
                return "color: #0055FF"

            st.dataframe(
                df_final.style.map(color_logic, subset=["SQUEEZE", "MOMENTUM", "VOL HEALTH"]),
                use_container_width=True
            )
        else:
            st.warning("Sem dados disponíveis.")
