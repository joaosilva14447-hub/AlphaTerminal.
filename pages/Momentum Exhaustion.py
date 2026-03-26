import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# Institutional Palette
COLOR_AQUA = "#00FFAA"
COLOR_BLUE = "#0055FF"
COLOR_BG = "#0E1117"

def get_institutional_data(tickers, interval="1h"):
    scanner_results = []
    for ticker in tickers:
        df = yf.download(ticker, period="60d", interval=interval, progress=False)
        if df.empty: continue
        
        # Squeeze Logic
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        df['sqz_on'] = (bb['BBL_20_2.0'] > kc['KCLe_20_1.5']) & (bb['BBU_20_2.0'] < kc['KCUe_20_1.5'])
        
        # Momentum & Volume Health
        df['mom'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        df['vol_sma'] = ta.sma(df['Volume'], 20)
        df['vol_health'] = (df['Close'] > df['Close'].shift(1)) & (df['Volume'] < df['vol_sma'])
        
        last = df.iloc[-1]
        scanner_results.append({
            "Ticker": ticker,
            "Squeeze": "🔴 ON" if last['sqz_on'] else "🟢 RELEASE",
            "Momentum": "UP" if last['mom'] > 0 else "DOWN",
            "Vol Health": "WEAK" if last['vol_health'] else "HEALTHY",
            "Score": 1 if (not last['vol_health'] and last['mom'] > 0) else 0
        })
    return pd.DataFrame(scanner_results)

# UI Layer
st.set_page_config(page_title="Institutional Dashboard", layout="wide")
st.title("🛡️ Alpha Institutional Scanner")

watch_list = ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F", "NQ=F"]
results = get_institutional_data(watch_list)

st.dataframe(results.style.map(lambda x: f'color: {COLOR_AQUA}' if x in ["HEALTHY", "UP", "🟢 RELEASE"] else f'color: {COLOR_BLUE}', 
                              subset=["Squeeze", "Momentum", "Vol Health"]))
