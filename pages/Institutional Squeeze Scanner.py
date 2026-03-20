import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- PADRÕES VISUAIS ---
COLOR_AQUA = "#00FFFF" # Bullish Strength
COLOR_BLUE = "#0000FF" # Bearish Strength

def calculate_trend(df):
    """Calcula a força da tendência usando ADX e DI"""
    if df is None or len(df) < 30:
        return None
    try:
        # Cálculo do ADX (Padrão 14 períodos)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx_df is None: return None
        
        # Unimos ao dataframe original
        df = pd.concat([df, adx_df], axis=1)
        return df
    except:
        return None

# --- UI INTERFACE ---
st.set_page_config(layout="wide")
st.title("⚖️ Institutional Trend Scanner (ADX)")

ticker = st.text_input("Ativo", "BTC-USD").upper()
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # Download direto e simplificado
        data = yf.download(ticker, period="60d", interval=interval, progress=False)
        
        if not data.empty:
            # Achatamento preventivo de colunas
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            df = calculate_trend(data)
            
            if df is not None:
                # Extração de valores puros (Scalars)
                # ADX_14 (Força), DMP_14 (+DI), DMN_14 (-DI)
                current_adx = float(df.iloc[-1]['ADX_14'])
                current_plus = float(df.iloc[-1]['DMP_14'])
                current_minus = float(df.iloc[-1]['DMN_14'])
                
                # Lógica de Mercado
                is_trending = current_adx > 25
                is_bullish = current_plus > current_minus
                
                # Definição visual
                bg_color = COLOR_AQUA if is_bullish else COLOR_BLUE
                status = "TRENDING" if is_trending else "RANGING"
                direction = "BULLISH" if is_bullish else "BEARISH"
                
                st.metric(f"TF: {name}", status)
                
                # Card de Informação com proteção de erro
                st.write(f"**Direção:** {direction}")
                st.write(f"**Força (ADX):** {current_adx:.2f}")
                
                # Barra visual de força
                st.progress(min(current_adx / 100, 1.0))
                
              st.markdown(f"""
<div style="padding:10px; border-left: 5px solid {bg_color}; background-color: #1E1E1E;">
    <span style="color:white;">Sinal Institucional Ativo</span>
</div>
""", unsafe_allow_html=True)
            else:
                st.error("Erro de cálculo.")
        else:
            st.warning("Sem dados.")
