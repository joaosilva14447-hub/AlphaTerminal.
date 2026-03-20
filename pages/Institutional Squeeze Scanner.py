import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- CORES ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"

def calculate_squeeze(df):
    if df is None or len(df) < 40:
        return None
    try:
        # Cálculo dos indicadores via pandas_ta
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        if bb is None or kc is None: return None
        
        # sqz_on: Bandas de Bollinger dentro dos Canais de Keltner
        df['sqz_on'] = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
        
        # Momentum (Regressão Linear)
        df['momentum'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        return df
    except:
        return None

# --- UI ---
st.set_page_config(layout="wide")
st.title("🛡️ Institutional Squeeze Scanner")

ticker = st.text_input("Ativo", "BTC-USD").upper()
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # 1. Download dos dados
        data = yf.download(ticker, period="60d", interval=interval, progress=False)
        
        if not data.empty:
            # 2. CORREÇÃO CRUCIAL: Remover o MultiIndex do yfinance
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # 3. Garantir que os dados são Series simples (Achatamento)
            data = data.copy()
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in data.columns:
                    data[col] = data[col].astype(float)

            df = calculate_squeeze(data)
            
            if df is not None:
                # 4. Extração de valores simples (scalars) para evitar o TypeError
                is_sqz = bool(df['sqz_on'].iloc[-1])
                mom_val = float(df['momentum'].iloc[-1])
                
                # Lógica de Cores
                bg_color = "white" if is_sqz else (COLOR_AQUA if mom_val > 0 else COLOR_BLUE)
                trend_text = "BULLISH" if mom_val > 0 else "BEARISH"
                
                st.metric(f"TF: {name}", "SQUEEZE" if is_sqz else "RELEASE")
                
                # O HTML agora recebe apenas valores convertidos (float/string)
                st.markdown(f"""
                    <div style="background-color:{bg_color}; padding:20px; border-radius:10px; text-align:center; border: 2px solid #333;">
                        <h3 style="color:black; margin:0;">{trend_text}</h3>
                        <p style="color:black; margin:0; font-size:12px;">Mom: {mom_val:.4f}</p>
                    </div>
                """, unsafe_html=True)
