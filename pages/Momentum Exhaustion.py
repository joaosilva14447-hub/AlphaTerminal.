import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. Título simples
st.title("🛡️ Alpha Scanner (Debug Mode)")

def get_data_safe(ticker, tf):
    try:
        # Download simples
        df = yf.download(ticker, period="60d", interval=tf, progress=False)
        
        # Correção obrigatória para MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 30:
            return None
        return df
    except:
        return None

def calc_signals_safe(df):
    try:
        # Bollinger Bands
        bb = ta.bbands(df['Close'], length=20)
        # Keltner Channels
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20)
        # Momentum
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        
        if bb is None or kc is None or mom is None:
            return None

        # Squeeze Logic (Acesso direto por índice de coluna para evitar erro de nomes)
        # 0 = Lower, 2 = Upper
        is_sqz = (bb.iloc[-1, 0] > kc.iloc[-1, 0]) and (bb.iloc[-1, 2] < kc.iloc[-1, 2])
        
        return {
            "price": float(df['Close'].iloc[-1]),
            "sqz": "🔴 ON" if is_sqz else "🟢 RELEASE",
            "mom": "BULLISH" if mom.iloc[-1] > 0 else "BEARISH"
        }
    except:
        return None

# --- UI SEM CSS (PARA EVITAR O TYPEERROR) ---
with st.sidebar:
    st.header("Settings")
    tickers_list = st.text_area("Assets", "BTC-USD, ETH-USD, SOL-USD, GC=F").split(",")
    tf_choice = st.selectbox("Timeframe", ["1h", "4h", "1d"])
    btn = st.button("RUN SCAN")

if btn:
    st.write("### 🔍 Processando ativos...")
    results = []
    
    for t in tickers_list:
        symbol = t.strip()
        df_raw = get_data_safe(symbol, tf_choice)
        
        if df_raw is not None:
            sigs = calc_signals_safe(df_raw)
            if sigs:
                results.append({
                    "Ativo": symbol,
                    "Preço": sigs['price'],
                    "Squeeze": sigs['sqz'],
                    "Momentum": sigs['mom']
                })
    
    if results:
        # Usamos st.table que é o componente mais estável do Streamlit
        st.write("### Institutional Matrix")
        st.table(pd.DataFrame(results))
    else:
        st.warning("Nenhum dado encontrado. Verifica os tickers ou o timeframe.")
