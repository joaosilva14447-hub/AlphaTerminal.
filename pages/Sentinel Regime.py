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
            # Forçamos o download a ser simples para evitar erros de multi-índice
            data = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data
        except:
            return pd.DataFrame()

    @staticmethod
    def calculate_metrics(df):
        if df.empty or len(df) < 35:
            return None
        
        # Extraímos os valores como Series puras para evitar conflitos
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # 1. Regime de Volatilidade (O Cérebro) - Fix para o ValueError
        high_low = high - low
        atr = high_low.rolling(14).mean()
        atr_baseline = atr.rolling(30).mean()
        
        # Forçamos a conversão para float para garantir a comparação
        current_atr = float(atr.iloc[-1])
        current_baseline = float(atr_baseline.iloc[-1])
        
        regime = "𝓔𝓧𝓟𝓐𝓝𝓢𝓘𝓞𝓝" if current_atr > current_baseline else "𝓒𝓞𝓝𝓣𝓡𝓐𝓒𝓣𝓘𝓞𝓝"
        
        # 2. Alpha Velocity Matrix (A Lógica)
        roc = close.pct_change(14)
        vol_avg = volume.rolling(20).mean()
        vol_weight = np.clip(volume / vol_avg, 0.35, 2.5)
        
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        rs = gain / loss.replace(0, np.nan)
        normalized_mom = 100 - (100 / (1 + rs))
        
        curr_mom = float(normalized_mom.iloc[-1])
        prev_mom = float(normalized_mom.iloc[-2])
        
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
st.title("✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓡𝓮𝓰𝓲𝓶𝓮 𝓿1.1 ✦")
st.markdown("---")

# Podes adicionar aqui qualquer ticker que queiras monitorizar
tickers = ["GEV", "MU", "BTC-USD", "NVDA", "GC=F"]
cols = st.columns(len(tickers))

for i, ticker in enumerate(tickers):
    with cols[i]:
        data_df = AlphaSentinelRegime.get_data(ticker)
        metrics = AlphaSentinelRegime.calculate_metrics(data_df)
        
        if metrics:
            # Cor de destaque baseada no Momentum
            color = "inverse" if metrics["mom"] < 30 else "normal"
            st.metric(label=f"**{ticker}**", value=metrics["mom"], delta_color=color)
            st.write(f"Regime: **{metrics['regime']}**")
            
            # Lógica de Sinal Alpha
            if metrics["hook_up"] and metrics["regime"] == "𝓒𝓞𝓝𝓣𝓡𝓐𝓒𝓣𝓘𝓞𝓝":
                st.success("𝓢𝓽𝓻𝓸𝓷𝓰 𝓑𝓾𝔂")
            elif metrics["hook_down"]:
                st.error("𝓣𝓪𝴴𝓮 𝓟𝓻𝓸𝓯𝓲𝓽")
            else:
                st.info("𝓢𝓽𝓪𝓷𝓭𝓫𝔂")
        else:
            st.warning(f"A aguardar dados de {ticker}...")
