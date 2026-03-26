import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# 1. Configuração de página (Se este for um ficheiro dentro da pasta /pages/, 
# podes comentar a linha abaixo se o teu main.py já a tiver)
try:
    st.set_page_config(page_title="Alpha Institutional", layout="wide")
except:
    pass

# --- ESTILO CSS SEGURO ---
st.markdown("""
    <style>
    .stMetric {
        background-color: #161B22 !important;
        padding: 15px !important;
        border-radius: 10px !important;
        border-left: 5px solid #00FFAA !important;
    }
    </style>
    """, unsafe_html=True)

def get_clean_data(ticker, timeframe):
    try:
        df = yf.download(ticker, period="60d", interval=timeframe, progress=False)
        
        # CORREÇÃO CRÍTICA: Remove o MultiIndex que causa o erro
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty or len(df) < 30:
            return None
        return df
    except:
        return None

def calculate_indicators(df):
    try:
        # Cálculo dos indicadores
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        # Se algum falhar, retornamos None para evitar o TypeError das imagens
        if bb is None or kc is None:
            return None
            
        # Lógica de Squeeze usando posições fixas (mais seguro)
        # bb.iloc[:, 0] = Lower, iloc[:, 2] = Upper
        sqz_on = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
        
        # Momentum
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        
        return {
            "sqz": sqz_on.iloc[-1],
            "mom": mom.iloc[-1],
            "price": df['Close'].iloc[-1]
        }
    except:
        return None

# --- UI PRINCIPAL ---
st.title("🛡️ Alpha Institutional Scanner")

with st.sidebar:
    st.header("Painel de Controlo")
    tickers_input = st.text_area("Lista de Ativos", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F")
    tf = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
    btn_scan = st.button("EXECUTAR SCANNER")

if btn_scan:
    tickers = [t.strip() for t in tickers_input.split(",")]
    final_data = []

    with st.spinner("A extrair dados institucionais..."):
        for t in tickers:
            df = get_clean_data(t, tf)
            if df is not None:
                stats = calculate_indicators(df)
                if stats:
                    final_data.append({
                        "Ticker": t,
                        "Preço": round(stats['price'], 2),
                        "Squeeze": "🔴 ON" if stats['sqz'] else "🟢 RELEASE",
                        "Momentum": "BULLISH" if stats['mom'] > 0 else "BEARISH",
                        "Valor Mom": stats['mom']
                    })

    if final_data:
        res_df = pd.DataFrame(final_data)
        
        # Métricas de topo
        c1, c2 = st.columns(2)
        c1.metric("Ativos em Squeeze", len(res_df[res_df['SQUEEZE'] == "🔴 ON"]))
        c2.metric("Momentum Alta", len(res_df[res_df['MOMENTUM'] == "BULLISH"]))

        # Tabela com cores dinâmicas
        def apply_color(val):
            color = "#00FFAA" if val in ["BULLISH", "🟢 RELEASE"] else "#0055FF"
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            res_df.style.map(apply_color, subset=["SQUEEZE", "MOMENTUM"]),
            use_container_width=True
        )
    else:
        st.error("Erro: Não foi possível calcular indicadores. Verifica os tickers.")
