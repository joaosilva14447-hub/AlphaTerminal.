import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- CONFIGURAÇÃO DA PALETA HEDGE FUND ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"

def calculate_squeeze(df, bb_len=20, bb_mult=2.0, kc_len=20, kc_mult=1.5):
    # Garantir que temos dados suficientes
    if len(df) < 40:
        return None

    # 1. Bollinger Bands
    bb = ta.bbands(df['Close'], length=bb_len, std=bb_mult)
    if bb is None: return None
    
    # Usamos .iloc para pegar as colunas pela posição, evitando erros de nomes com 2.0/2
    lower_bb = bb.iloc[:, 0] # BBL
    upper_bb = bb.iloc[:, 2] # BBU

    # 2. Keltner Channels
    kc = ta.kc(df['High'], df['Low'], df['Close'], length=kc_len, scalar=kc_mult)
    if kc is None: return None
    
    lower_kc = kc.iloc[:, 0] # KCL
    upper_kc = kc.iloc[:, 2] # KCU

    # 3. Squeeze Logic
    df['sqz_on'] = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    
    # 4. Momentum (Linear Regression)
    # Calculamos o momentum sobre o fecho
    df['momentum'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
    
    return df

# --- INTERFACE STREAMLIT ---
st.set_page_config(layout="wide")
st.title("🛡️ Institutional Squeeze Scanner")

ticker = st.text_input("Ativo (ex: BTC-USD, AAPL, EURUSD=X)", "BTC-USD")
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # Baixar dados
        data = yf.download(ticker, period="60d", interval=interval, progress=False)
        
        # FIX: Resolver o problema do cabeçalho duplo do yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        if not data.empty and len(data) > 20:
            df = calculate_squeeze(data)
            
            if df is not None:
                last_row = df.iloc[-1]
                is_sqz = last_row['sqz_on']
                mom = last_row['momentum']
                
                bg_color = "white" if is_sqz else (COLOR_AQUA if mom > 0 else COLOR_BLUE)
                status = "SQUEEZE ON" if is_sqz else "RELEASE (FIRED)"
                
                st.metric(label=f"TF: {name}", value=status)
                st.markdown(
                    f"""
                    <div style="background-color:{bg_color}; padding:20px; border-radius:10px; text-align:center; border: 1px solid #333;">
                        <h3 style="color:black;">{'BULLISH' if mom > 0 else 'BEARISH'}</h3>
                    </div>
                    """, unsafe_html=True
                )
            else:
                st.warning(f"Dados insuficientes para {name}")
