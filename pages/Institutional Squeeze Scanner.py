import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- PADRÕES VISUAIS INSTITUCIONAIS ---
COLOR_AQUA = "#00FFFF"
COLOR_BLUE = "#0000FF"

def calculate_squeeze(df):
    """Cálculo robusto com tratamento de NaNs e alinhamento de índices"""
    if df is None or len(df) < 40:
        return None
    try:
        # Bollinger Bands (20, 2)
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        # Keltner Channels (20, 1.5)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        if bb is None or kc is None: return None
        
        # Squeeze Logic: BB dentro das KC
        # Usamos .iloc para garantir a captura da coluna correta independentemente do nome
        df['sqz_on'] = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
        
        # Momentum: Regressão Linear da diferença do fechamento pela média
        df['momentum'] = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        return df
    except Exception:
        return None

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Alpha Terminal")
st.title("🛡️ Institutional Squeeze Scanner")

ticker_input = st.text_input("Ativo", "BTC-USD").upper()
tfs = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}

cols = st.columns(len(tfs))

for i, (name, interval) in enumerate(tfs.items()):
    with cols[i]:
        # Download com auto_adjust para evitar colunas extras
        data = yf.download(ticker_input, period="60d", interval=interval, progress=False, auto_adjust=True)
        
        if not data.empty:
            # LIMPEZA DE MULTI-INDEX (A causa raiz do erro)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Garantir que temos as colunas necessárias
            data = data[['Open', 'High', 'Low', 'Close']]
            
            df = calculate_squeeze(data)
            
            if df is not None:
                # EXTRAÇÃO DE SCALARS: Convertendo Series para valores puros Python
                # Isso impede o TypeError no st.markdown
                current_sqz = bool(df['sqz_on'].iloc[-1])
                current_mom = float(df['momentum'].iloc[-1])
                
                # Definição de Cores e Labels
                if current_sqz:
                    bg_color = "white"
                    status_text = "SQUEEZE ON"
                    trend = "NEUTRAL / COMPRESS"
                else:
                    bg_color = COLOR_AQUA if current_mom > 0 else COLOR_BLUE
                    status_text = "RELEASE (FIRED)"
                    trend = "BULLISH" if current_mom > 0 else "BEARISH"
                
                st.metric(f"Timeframe: {name}", status_text)
                
                # Renderização do Card com valores sanitizados
                st.markdown(f"""
                    <div style="background-color:{bg_color}; padding:25px; border-radius:12px; text-align:center; border: 2px solid #262730;">
                        <h2 style="color:black; margin:0; font-size:24px;">{trend}</h2>
                        <p style="color:black; margin:5px 0 0 0; font-weight:bold;">Mom: {current_mom:.5f}</p>
                    </div>
                """, unsafe_html=True)
            else:
                st.error(f"Erro nos indicadores: {name}")
        else:
            st.warning(f"Dados insuficientes: {name}")
