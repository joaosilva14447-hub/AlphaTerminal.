import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
import numpy as np

# --- CONFIGURAÇÃO DE CORES ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"

def calculate_squeeze(df):
    """Calcula o Squeeze Pro com protecção contra dados vazios"""
    if df is None or len(df) < 30:
        return None
    
    try:
        # 1. Bollinger Bands (20, 2)
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        # 2. Keltner Channels (20, 1.5)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        if bb is None or kc is None: return None
        
        # Selecção segura de colunas por posição (iloc) para evitar erros de nomes
        lower_bb = bb.iloc[:, 0]
        upper_bb = bb.iloc[:, 2]
        lower_kc = kc.iloc[:, 0]
        upper_kc = kc.iloc[:, 2]
        
        # Lógica do Squeeze
        df['sqz_on'] = (lower_bb > lower_kc) & (upper_bb < upper_kc)
        
        # Momentum (Regressão Linear do oscilador)
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        df['momentum'] = mom
        
        return df
    except Exception as e:
        return None

# --- UI STREAMLIT ---
st.set_page_config(layout="wide", page_title="Hedge Fund Scanner")
st.title("🛡️ Institutional Squeeze Scanner")

ticker_input = st.text_input("Ativo (ex: BTC-USD, AAPL, EURUSD=X)", "BTC-USD").upper()
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # Download com limpeza imediata de MultiIndex
        data = yf.download(ticker_input, period="60d", interval=interval, progress=False)
        
        if not data.empty:
            # Garante que as colunas são simples (Close, High, Low...)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            df_result = calculate_squeeze(data)
            
            if df_result is not None:
                # EXTRAÇÃO SEGURA: Garantimos que o valor é um número (scalar)
                last_sqz = bool(df_result['sqz_on'].iloc[-1])
                # Usamos float() e .item() para garantir que não é uma série/lista
                try:
                    last_mom = float(df_result['momentum'].iloc[-1])
                except:
                    last_mom = 0.0
                
                # Definição de Cores e Status
                if last_sqz:
                    bg_color = "white"
                    status = "SQUEEZE ON"
                    trend = "COMPRESSÃO"
                else:
                    bg_color = COLOR_AQUA if last_mom > 0 else COLOR_BLUE
                    status = "RELEASE (FIRED)"
                    trend = "BULLISH" if last_mom > 0 else "BEARISH"
                
                # Exibição
                st.metric(label=f"Timeframe: {name}", value=status)
                
                # HTML com tratamento de erro para strings
                html_card = f"""
                <div style="background-color:{bg_color}; padding:30px; border-radius:15px; text-align:center; border: 2px solid #333;">
                    <h2 style="color:black; margin:0; font-weight:bold;">{trend}</h2>
                    <p style="color:black; margin:5px 0 0 0; opacity:0.8;">Mom: {last_mom:.4f}</p>
                </div>
                """
                st.markdown(html_card, unsafe_html=True)
            else:
                st.error(f"Erro no cálculo: {name}")
        else:
            st.warning(f"Sem dados para {name}")
