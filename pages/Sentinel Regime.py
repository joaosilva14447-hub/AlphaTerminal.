import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

# Configuração da Página
st.set_page_config(page_title="Alpha Sentinel Regime", layout="wide")

class AlphaSentinelRegime:
    @staticmethod
    def get_data(ticker):
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            return data
        except:
            return pd.DataFrame()

    @staticmethod
    def calculate_metrics(df):
        if df.empty or len(df) < 30:
            return None
        
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        
        # 1. Regime de Volatilidade (O Cérebro)
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean()
        regime = "𝓔𝓧𝓟𝓐𝓝𝓢𝓘𝓞𝓝" if atr.iloc[-1] > atr.rolling(30).mean().iloc[-1] else "𝓒𝓞𝓝𝓣𝓡𝓐𝓒𝓣𝓘𝓞𝓝"
        
        # 2. Alpha Velocity Matrix (A Lógica)
        roc = close.pct_change(14)
        vol_avg = volume.rolling(20).mean()
        vol_weight = np.clip(volume / vol_avg, 0.35, 2.5)
        
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        # Correção da fórmula RSI (Syntax Fixed)
        rs = gain / loss.replace(0, np.nan)
        normalized_mom = 100 - (100 / (1 + rs))
        
        curr_mom = normalized_mom.iloc[-1]
        prev_mom = normalized_mom.iloc[-2]
        
        # The Hook (O Gancho)
        hook_up = curr_mom < 30 and curr_mom > prev_mom
        hook_down = curr_mom > 70 and curr_mom < prev_mom
        
        return {
            "mom": round(curr_mom, 1),
            "regime": regime,
            "hook_up": hook_up,
            "hook_down": hook_down
        }

# UI do Streamlit
st.title("✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓡𝓮𝓰𝓲𝓶𝓮 ✦")
st.markdown("---")

tickers = ["GEV", "MU", "BTC-USD", "NVDA", "TSM", "GC=F"]
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    with cols[i]:
        df = AlphaSentinelRegime.get_data(ticker)
        metrics = AlphaSentinelRegime.calculate_metrics(df)
        
        if metrics:
            st.metric(label=f"**{ticker}**", value=metrics["mom"])
            st.write(f"Regime: {metrics['regime']}")
            
            # Lógica de Sinal Alpha
            if metrics["hook_up"] and metrics["regime"] == "𝓒𝓞𝓝𝓣𝓡𝓐𝓒𝓣𝓘𝓞𝓝":
                st.success("𝓢𝓽𝓻𝓸𝓷𝓰 𝓑𝓾𝔂")
            elif metrics["hook_down"]:
                st.error("𝓣𝓪𝓴𝓮 𝓟𝓻𝓸𝓯𝓲𝓽")
            else:
                st.info("𝓢𝓽𝓪𝓷𝓭𝓫𝔂")
        else:
            st.error("Data Error")
