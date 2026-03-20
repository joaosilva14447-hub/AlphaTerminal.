import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
import numpy as np

# --- CONFIGURAÇÃO DA PALETA HEDGE FUND ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"

def calculate_squeeze(df, bb_len=20, bb_mult=2.0, kc_len=20, kc_mult=1.5):
    if df is None or len(df) < 40:
        return None

    try:
        # 1. Bollinger Bands
        bb = ta.bbands(df['Close'], length=bb_len, std=bb_mult)
        # 2. Keltner Channels
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=kc_len, scalar=kc_mult)
        
        if bb is None or kc is None: return None
        
        # Squeeze Logic (Usando iloc para evitar erros de nomes de colunas)
        lower_bb, upper_bb = bb.iloc[:, 0], bb.iloc[:, 2]
        lower_kc, upper_kc = kc.iloc[:, 0], kc.iloc[:, 2]
        
        df['sqz_on'] = (lower_bb > lower_kc) & (upper_bb < upper_kc)
        df['momentum'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        
        return df
    except Exception:
        return None

# --- INTERFACE STREAMLIT ---
st.set_page_config(layout="wide", page_title="Institutional Scanner")
st.title("🛡️ Institutional Squeeze Scanner")

ticker = st.text_input("Ativo (ex: BTC-USD, AAPL, EURUSD=X)", "BTC-USD").upper()
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # Baixar dados e limpar colunas MultiIndex
        data = yf.download(ticker, period="60d", interval=interval, progress=False)
        
        if not data.empty:
            # Limpeza crucial para as novas versões do yfinance
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            df = calculate_squeeze(data)
            
            if df is not None and 'sqz_on' in df.columns:
                # Extrair valores garantindo que são números puros (float/bool)
                is_sqz = bool(df['sqz_on'].iloc[-1])
                mom_val = float(df['momentum'].iloc[-1])
                
                # Lógica de Cores
                bg_color = "white" if is_sqz else (COLOR_AQUA if mom_val > 0 else COLOR_BLUE)
                label_trend = "BULLISH" if mom_val > 0 else "BEARISH"
                status_text = "SQUEEZE ON" if is_sqz else "RELEASE (FIRED)"
                
                st.metric(label=f"TF: {name}", value=status_text)
                st.markdown(
                    f"""
                    <div style="background-color:{bg_color}; padding:25px; border-radius:15px; text-align:center; border: 2px solid #333;">
                        <h2 style="color:black; margin:0;">{label_trend}</h2>
                        <p style="color:black; opacity:0.7; margin:0;">Momentum: {mom_val:.4f}</p>
                    </div>
                    """, unsafe_html=True
                )
            else:
                st.error(f"Erro no cálculo: {name}")
        else:
            st.warning(f"Sem dados: {name}")
