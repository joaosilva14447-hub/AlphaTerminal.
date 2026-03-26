import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Alpha Institutional Terminal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PALETA DE CORES INSTITUCIONAL ---
COLOR_AQUA = "#00FFAA"
COLOR_BLUE = "#0055FF"
COLOR_BG = "#0E1117"
COLOR_CARD = "#161B22"

# --- ESTILIZAÇÃO CUSTOMIZADA (CSS) ---
st.markdown(f"""
    <style>
    .main {{ background-color: {COLOR_BG}; }}
    .stMetric {{ background-color: {COLOR_CARD}; padding: 15px; border-radius: 10px; border-left: 5px solid {COLOR_AQUA}; }}
    div[data-testid="stExpander"] {{ border: 1px solid {COLOR_BLUE}; background-color: {COLOR_CARD}; }}
    </style>
    """, unsafe_html=True)

# --- ENGINE DE CÁLCULO (HEDGE FUND STANDARD) ---
def get_institutional_data(tickers, interval="1h"):
    scanner_results = []
    
    for ticker in tickers:
        try:
            # Download de dados
            df = yf.download(ticker, period="60d", interval=interval, progress=False)
            
            # Correção para MultiIndex do yfinance
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 30:
                continue
            
            # 1. Bollinger Bands (Acesso por posição para evitar erros de nome)
            bb = ta.bbands(df['Close'], length=20, std=2.0)
            
            # 2. Keltner Channels
            kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
            
            if bb is None or kc is None:
                continue

            # 3. Lógica de Squeeze: BB dentro do KC
            # bb.iloc[:, 0] = Lower Band | bb.iloc[:, 2] = Upper Band
            # kc.iloc[:, 0] = Lower KC   | kc.iloc[:, 2] = Upper KC
            df['sqz_on'] = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
            
            # 4. Institutional Momentum (Linear Regression)
            df['mom'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
            
            # 5. Volume Health (Divergência de Exaustão)
            vol_sma = ta.sma(df['Volume'], 20)
            df['vol_weak'] = (df['Close'] > df['Close'].shift(1)) & (df['Volume'] < vol_sma)
            
            last = df.iloc[-1]
            
            scanner_results.append({
                "TICKER": ticker,
                "PREÇO": round(float(last['Close']), 2),
                "SQUEEZE": "🔴 ON" if last['sqz_on'] else "🟢 RELEASE",
                "MOMENTUM": "BULLISH" if last['mom'] > 0 else "BEARISH",
                "VOL HEALTH": "⚠️ WEAK" if last['vol_weak'] else "✅ HEALTHY",
                "MOM_VAL": round(last['mom'], 4)
            })
        except Exception as e:
            st.error(f"Erro ao processar {ticker}: {e}")
            
    return pd.DataFrame(scanner_results)

# --- INTERFACE DO UTILIZADOR ---
def main():
    st.title("🛡️ Alpha Institutional Scanner")
    st.subheader("Market Intelligence & Momentum Matrix")

    # SIDEBAR: Controlos
    with st.sidebar:
        st.header("Configurações")
        assets = st.text_area("Watchlist (Separado por vírgulas)", 
                             "BTC-USD, ETH-USD, SOL-USD, AAPL, TSLA, GC=F, NQ=F")
        tf = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)
        run_btn = st.button("ATUALIZAR SCANNER")

    tickers_list = [t.strip() for t in assets.split(",")]

    if run_btn or 'results_df' not in st.session_state:
        with st.spinner("A analisar fluxo institucional..."):
            df_final = get_institutional_data(tickers_list, tf)
            st.session_state.results_df = df_final

    # DISPLAY: Grid de Resultados
    if not st.session_state.results_df.empty:
        results = st.session_state.results_df
        
        # Métricas de Resumo
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Ativos em Squeeze", len(results[results['SQUEEZE'] == "🔴 ON"]))
        with c2:
            st.metric("Momentum Bullish", len(results[results['MOMENTUM'] == "BULLISH"]))
        with c3:
            st.metric("Volume Saudável", len(results[results['VOL HEALTH'] == "✅ HEALTHY"]))

        st.divider()

        # Tabela Principal Estilizada
        def color_status(val):
            if val in ["BULLISH", "✅ HEALTHY", "🟢 RELEASE"]: return f'color: {COLOR_AQUA}'
            if val in ["BEARISH", "⚠️ WEAK", "🔴 ON"]: return f'color: {COLOR_BLUE}'
            return ''

        st.dataframe(
            results.style.applymap(color_status, subset=["SQUEEZE", "MOMENTUM", "VOL HEALTH"]),
            use_container_width=True,
            height=400
        )
    else:
        st.warning("Nenhum dado encontrado para os tickers fornecidos.")

if __name__ == "__main__":
    main()
