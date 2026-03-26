import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. Configuração mínima (Sem st.set_page_config se for um sub-página)
st.title("🛡️ Alpha Institutional Scanner")

def get_data(ticker, timeframe):
    try:
        # Download com reparação imediata de colunas
        df = yf.download(ticker, period="60d", interval=timeframe, progress=False)
        
        if df.empty:
            return None
            
        # Limpeza obrigatória para o pandas_ta (MultiIndex Fix)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except:
        return None

def calc_signals(df):
    try:
        # Usamos os métodos mais simples do pandas_ta
        # Bollinger Bands
        bb = df.ta.bbands(length=20, std=2.0)
        # Keltner Channels
        kc = df.ta.kc(length=20, scalar=1.5)
        # Momentum
        mom = df.ta.linreg(close=df['Close'] - df['Close'].rolling(20).mean(), length=20)

        if bb is None or kc is None or mom is None:
            return None

        # Squeeze Logic (Acesso seguro por posição)
        # bb.iloc[:, 0] é a Lower Band, bb.iloc[:, 2] é a Upper Band
        # kc.iloc[:, 0] é o Lower KC, kc.iloc[:, 2] é o Upper KC
        is_sqz = (bb.iloc[:, 0] > kc.iloc[:, 0]) and (bb.iloc[:, 2] < kc.iloc[:, 2])
        
        return {
            "price": float(df['Close'].iloc[-1]),
            "sqz": "ON" if is_sqz else "RELEASE",
            "mom": "BULL" if mom.iloc[-1] > 0 else "BEAR"
        }
    except:
        return None

# --- UI ---
with st.sidebar:
    assets = st.text_area("Tickers", "BTC-USD, ETH-USD, SOL-USD")
    tf = st.selectbox("TF", ["1h", "4h", "1d"])
    btn = st.button("RUN SCAN")

if btn:
    tickers = [t.strip() for t in assets.split(",")]
    results = []

    for t in tickers:
        data = get_data(t, tf)
        if data is not None:
            sig = calc_signals(data)
            if sig:
                results.append({
                    "SYMBOL": t,
                    "PRICE": sig['price'],
                    "SQUEEZE": sig['sqz'],
                    "MOMENTUM": sig['mom']
                })

    if results:
        final_df = pd.DataFrame(results)
        
        # Mostramos os resultados de forma bruta primeiro para garantir que funciona
        st.write("### Market Matrix")
        
        # Métricas simples (Sem formatação complexa para evitar o TypeError)
        c1, c2 = st.columns(2)
        c1.metric("Total Assets", len(final_df))
        c2.metric("Squeeze Count", len(final_df[final_df["SQUEEZE"] == "ON"]))

        st.table(final_df)
    else:
        st.error("Sem dados. Verifica a ligação ou os tickers.")
