import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. Título e Configuração
st.title("🛡️ Alpha Institutional Scanner")

# --- CSS SEGURO (Sem F-Strings para evitar o erro de sintaxe) ---
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

def get_data_v3(ticker_symbol, timeframe):
    try:
        # Ticker object é mais estável que o download direto
        t = yf.Ticker(ticker_symbol)
        
        # Mapeamento de timeframe para o yfinance
        period_map = {"1h": "60d", "4h": "60d", "1d": "200d"}
        p = period_map.get(timeframe, "60d")
        
        df = t.history(period=p, interval=timeframe)
        
        if df.empty or len(df) < 35:
            return None
            
        # Limpeza de colunas
        df.columns = [c.capitalize() for c in df.columns]
        return df
    except Exception as e:
        st.sidebar.error(f"Erro no download {ticker_symbol}: {e}")
        return None

def get_signals_v3(df):
    try:
        # Cálculo manual/direto para evitar bugs do pandas_ta em novas versões do Python
        # Bollinger Bands
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        # Keltner Channels
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        # Momentum (Linear Regression)
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        
        if bb is None or kc is None or mom is None:
            return None

        # Squeeze Logic (BB dentro do KC)
        # Usamos .iloc[:, X] para garantir a posição da coluna
        lower_bb = bb.iloc[:, 0]
        upper_bb = bb.iloc[:, 2]
        lower_kc = kc.iloc[:, 0]
        upper_kc = kc.iloc[:, 2]
        
        is_sqz = (lower_bb.iloc[-1] > lower_kc.iloc[-1]) and (upper_bb.iloc[-1] < upper_kc.iloc[-1])
        
        return {
            "price": float(df['Close'].iloc[-1]),
            "sqz": "🔴 ON" if is_sqz else "🟢 RELEASE",
            "mom": "BULLISH" if mom.iloc[-1] > 0 else "BEARISH"
        }
    except Exception as e:
        st.sidebar.warning(f"Erro nos cálculos: {e}")
        return None

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Terminal Config")
    assets_input = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F")
    tf_choice = st.selectbox("Intervalo", ["1h", "4h", "1d"], index=0)
    run_btn = st.button("RUN SCANNER")

# --- EXECUÇÃO ---
if run_btn:
    tickers = [x.strip() for x in assets_input.split(",")]
    final_results = []
    
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers):
        with st.status(f"A analisar {t}...", expanded=False):
            data = get_data_v3(t, tf_choice)
            if data is not None:
                sigs = get_signals_v3(data)
                if sigs:
                    final_results.append({
                        "Ticker": t,
                        "Price": sigs['price'],
                        "Squeeze": sigs['sqz'],
                        "Momentum": sigs['mom']
                    })
        progress_bar.progress((i + 1) / len(tickers))

    if final_results:
        res_df = pd.DataFrame(final_results)
        
        # Grid de Métricas
        m1, m2 = st.columns(2)
        m1.metric("Assets Analyzed", len(res_df))
        m2.metric("Squeezes Detected", len(res_df[res_df['SQUEEZE'] == "🔴 ON"]))
        
        st.divider()
        
        # Estilização da Tabela
        def style_logic(val):
            if val in ["BULLISH", "🟢 RELEASE"]: return 'color: #00FFAA; font-weight: bold'
            if val in ["BEARISH", "🔴 ON"]: return 'color: #0055FF; font-weight: bold'
            return ''

        st.dataframe(
            res_df.style.map(style_logic, subset=["SQUEEZE", "MOMENTUM"]),
            use_container_width=True
        )
    else:
        st.error("Não foram encontrados dados. Tenta trocar o Timeframe ou a lista de ativos.")
