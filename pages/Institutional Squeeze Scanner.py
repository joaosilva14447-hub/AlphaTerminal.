import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- CONFIGURAÇÃO DA PALETA HEDGE FUND ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"
COLOR_ALPHA_BLUE = "rgba(0, 255, 255, 0.2)"
COLOR_ALPHA_RED = "rgba(255, 0, 0, 0.2)"

def calculate_squeeze(df, bb_len=20, bb_mult=2.0, kc_len=20, kc_mult=1.5):
    # 1. Bollinger Bands
    bb = ta.bbands(df['Close'], length=bb_len, std=bb_mult)
    upper_bb = bb[f'BBU_{bb_len}_{bb_mult}']
    lower_bb = bb[f'BBL_{bb_len}_{bb_mult}']

    # 2. Keltner Channels
    kc = ta.kc(df['High'], df['Low'], df['Close'], length=kc_len, scalar=kc_mult)
    upper_kc = kc[f'KCUe_{kc_len}_{kc_mult}']
    lower_kc = kc[f'KCLe_{kc_len}_{kc_mult}']

    # 3. Squeeze Logic
    df['sqz_on'] = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    
    # 4. Momentum (Linear Regression)
    # Usamos o momentum do oscilador para direção
    df['momentum'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
    
    return df

# --- INTERFACE STREAMLIT ---
st.set_page_config(layout="wide")
st.title("🛡️ Institutional Squeeze Scanner")

ticker = st.text_input("Ativo (ex: BTC-USD, AAPL, EURUSD=X)", "BTC-USD")
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"} # Simplificado para o exemplo

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        data = yf.download(ticker, period="60d", interval=interval, progress=False)
        if not data.empty:
            df = calculate_squeeze(data)
            last_row = df.iloc[-1]
            
            is_sqz = last_row['sqz_on']
            mom = last_row['momentum']
            
            # Definição de Cor Baseada na Paleta
            bg_color = "white" if is_sqz else (COLOR_AQUA if mom > 0 else COLOR_BLUE)
            text_color = "black"
            status = "SQUEEZE ON" if is_sqz else "RELEASE (FIRED)"
            
            st.metric(label=f"TF: {name}", value=status)
            st.markdown(
                f"""
                <div style="background-color:{bg_color}; padding:20px; border-radius:10px; text-align:center;">
                    <h3 style="color:{text_color};">{'UP' if mom > 0 else 'DOWN'}</h3>
                </div>
                """, unsafe_html=True
            )
