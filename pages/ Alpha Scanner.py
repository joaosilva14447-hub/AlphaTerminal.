import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
import numpy as np

st.title("🛡️ Alpha Momentum Matrix (Elite)")
st.markdown("Monitorização Avançada de Compressão e Aceleração Institucional")

def get_data_elite(ticker, tf):
    try:
        df = yf.download(ticker, period="100d", interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 30: 
            return None
        return df
    except:
        return None

def calc_elite_signals(df):
    try:
        # Bandas e Canais base
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        if bb is None or kc is None: return None

        # Squeeze Logic
        sqz_on = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
        df['sqz_on'] = sqz_on
        
        # Squeeze Duration (Conta os períodos consecutivos de compressão)
        df['sqz_duration'] = df['sqz_on'].groupby((~df['sqz_on']).cumsum()).cumsum()
        
        # Momentum e Aceleração (Derivada)
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        mom_acc = mom.diff()
        
        # Volume Health (Confirmação simples)
        vol_sma = ta.sma(df['Volume'], 20)
        vol_trend = df['Volume'] > vol_sma
        
        last = -1
        return {
            "Ativo": "TEMP", # Preenchido depois
            "Preço": float(df['Close'].iloc[last]),
            "Squeeze": "🔴 ON" if sqz_on.iloc[last] else "🟢 OFF",
            "Dias Squeeze": int(df['sqz_duration'].iloc[last]),
            "Mom. Status": "BULL" if mom.iloc[last] > 0 else "BEAR",
            "Aceleração": round(float(mom_acc.iloc[last]), 2),
            "Volume Forte": "SIM" if vol_trend.iloc[last] else "NÃO"
        }
    except:
        return None

# --- UI CONTROLS ---
with st.sidebar:
    st.header("Parâmetros do Radar")
    tickers_list = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, AAPL").split(",")
    tf_choice = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
    btn = st.button("ANALISAR MERCADO")

if btn:
    st.write("A processar métricas de alta precisão...")
    results = []
    
    for t in tickers_list:
        symbol = t.strip()
        df_raw = get_data_elite(symbol, tf_choice)
        
        if df_raw is not None:
            sigs = calc_elite_signals(df_raw)
            if sigs:
                sigs["Ativo"] = symbol
                results.append(sigs)
    
    if results:
        res_df = pd.DataFrame(results)
        
        # Formatação Visual Avançada (Pandas Styler com a nossa Paleta)
        def highlight_squeeze(val):
            return 'color: #0055FF; font-weight: bold' if val == "🔴 ON" else 'color: #00FFAA'
            
        def highlight_mom(val):
            return 'color: #00FFAA; font-weight: bold' if val == "BULL" else 'color: #0055FF'
            
        def color_acceleration(val):
            color = '#00FFAA' if val > 0 else '#0055FF'
            return f'color: {color}'

        styled_df = (res_df.style
                     .map(highlight_squeeze, subset=['Squeeze'])
                     .map(highlight_mom, subset=['Mom. Status'])
                     .map(color_acceleration, subset=['Aceleração'])
                     .background_gradient(subset=['Dias Squeeze'], cmap='Blues')
                     .format({'Preço': "{:.2f}", 'Aceleração': "{:+.2f}"}))

        st.dataframe(styled_df, use_container_width=True, height=400)
        
    else:
        st.warning("Sem dados limpos para apresentar.")
