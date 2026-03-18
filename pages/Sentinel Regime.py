import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# 1. Configuração de Estética Alpha
st.set_page_config(page_title="Alpha Sentinel Terminal", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    .stMetric { background-color: #0e1117; padding: 15px; border-radius: 10px; border: 1px solid #3D5AFE; }
    </style>
    """, unsafe_allow_html=True)

class AlphaEngine:
    @staticmethod
    def get_data(ticker):
        data = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        return data

    @staticmethod
    def calculate_alpha_matrix(df):
        if len(df) < 35: return None
        close, vol = df['Close'], df['Volume']
        
        # Lógica Alpha Matrix
        roc = close.pct_change(14)
        vol_weight = np.clip(vol / vol.rolling(20).mean(), 0.35, 2.5)
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        matrix_series = 100 - (100 / (1 + rs))
        
        # Bull Score Logic (Simplificada para Python)
        score = 0
        if matrix_series.iloc[-1] < 30: score += 1
        if close.iloc[-1] > close.rolling(50).mean().iloc[-1]: score += 1
        if vol.iloc[-1] > vol.rolling(20).mean().iloc[-1]: score += 1
        if matrix_series.iloc[-1] > matrix_series.iloc[-2]: score += 1
        
        return matrix_series, score

def create_chart(series, ticker):
    fig = go.Figure()
    # Adicionar a Onda de Momentum
    fig.add_trace(go.Scatter(y=series, mode='lines', line=dict(color='#09DBB5', width=3), fill='tozeroy', fillcolor='rgba(9, 219, 181, 0.1)'))
    # Linhas de Limite
    fig.add_hline(y=70, line_dash="dash", line_color="#FF0000", opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFAA", opacity=0.5)
    
    fig.update_layout(
        height=250, margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(range=[0, 100], showgrid=False, color="gray"),
        xaxis=dict(showgrid=False, showticklabels=False),
        title=f"𝓜𝓸𝓶𝓮𝓷𝓽𝓾𝓶: {ticker}", title_font_color="#3D5AFE"
    )
    return fig

# --- UI EXECUTION ---
st.title("✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓣𝓮𝓻𝓶𝓲𝓷𝓪𝓵 𝓿2.0 ✦")

tickers = ["GEV", "MU", "BTC-USD", "NVDA", "GC=F"]
tabs = st.tabs([f"   {t}   " for t in tickers])

for i, ticker in enumerate(tickers):
    with tabs[i]:
        df = AlphaEngine.get_data(ticker)
        matrix_series, bull_score = AlphaEngine.calculate_alpha_matrix(df)
        
        if matrix_series is not None:
            col1, col2 = st.columns([1, 3])
            
            with col1:
                curr_val = round(matrix_series.iloc[-1], 1)
                st.metric("𝓜𝓪𝓽𝓻𝓲𝔁 𝓥𝓪𝓵𝓾𝓮", curr_val, delta=f"{bull_score}/4 Bull Score")
                
                # Status de Execução
                if curr_val < 30 and matrix_series.iloc[-1] > matrix_series.iloc[-2]:
                    st.success("🎯 𝓢𝓽𝓻𝓸𝓷𝓰 𝓑𝓾𝔂")
                elif curr_val > 70:
                    st.error("⚠️ 𝓣𝓪𝓴𝓮 𝓟𝓻𝓸𝓯𝓲𝓽")
                else:
                    st.info("⌛ 𝓢𝓽𝓪𝓷𝓭𝓫𝔂")
                
                st.write(f"Volume: {'Institucional' if df['Volume'].iloc[-1] > df['Volume'].rolling(20).mean().iloc[-1] else 'Retail'}")

            with col2:
                st.plotly_chart(create_chart(matrix_series, ticker), use_container_width=True)
        else:
            st.warning("Carregando fluxo de dados...")
