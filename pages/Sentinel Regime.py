import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. Configuração de Estética e Layout
st.set_page_config(page_title="Alpha Sentinel Terminal v2.1", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #05070a; }
    .stMetric { 
        background-color: #0e1117; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stExpander"] { border: none !important; }
    .sector-box {
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        margin-top: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

class AlphaTerminalEngine:
    @staticmethod
    def get_clean_data(ticker, days=60):
        try:
            data = yf.download(ticker, period=f"{days}d", interval="1d", progress=False, auto_adjust=True)
            if data.empty: return None
            # Fix para MultiIndex do yfinance 2026
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data
        except Exception:
            return None

    @staticmethod
    def calculate_metrics(df, sector_df):
        if df is None or len(df) < 35: return None
        
        close = df['Close']
        vol = df['Volume']
        
        # --- Alpha Matrix Core ---
        roc = close.pct_change(14)
        vol_avg = vol.rolling(20).mean()
        vol_weight = np.clip(vol / vol_avg, 0.35, 2.5)
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        matrix_series = 100 - (100 / (1 + rs))
        
        # --- Sector Edge (Relative Strength) ---
        asset_perf = (close.iloc[-1] / close.iloc[-5]) - 1
        sector_perf = (sector_df['Close'].iloc[-1] / sector_df['Close'].iloc[-5]) - 1
        relative_strength = (asset_perf - sector_perf) * 100
        
        # --- Bull Score 0/4 ---
        score = 0
        curr_mom = float(matrix_series.iloc[-1])
        prev_mom = float(matrix_series.iloc[-2])
        
        if curr_mom < 30: score += 1 # Oversold
        if curr_mom > prev_mom: score += 1 # Hook Up
        if float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1]): score += 1 # Trend
        if float(vol.iloc[-1]) > float(vol_avg.iloc[-1]): score += 1 # Vol Confirmation
        
        return {
            "series": matrix_series,
            "current_mom": round(curr_mom, 1),
            "score": score,
            "relative_strength": round(relative_strength, 2),
            "is_hook_up": curr_mom < 35 and curr_mom > prev_mom,
            "is_hook_down": curr_mom > 65 and curr_mom < prev_mom
        }

def draw_alpha_chart(series, ticker):
    fig = go.Figure()
    # Gradient Fill Style
    fig.add_trace(go.Scatter(
        y=series, mode='lines', 
        line=dict(color='#00f2ff', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 242, 255, 0.05)',
        name="Momentum"
    ))
    # Thresholds
    fig.add_hline(y=70, line_dash="dot", line_color="#ff4b4b", opacity=0.3)
    fig.add_hline(y=30, line_dash="dot", line_color="#00ffaa", opacity=0.3)
    
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(range=[0, 100], color="#64748b", gridcolor="#1e293b"),
        xaxis=dict(showgrid=False, showticklabels=False),
        title=dict(text=f"𝓥𝓮𝓵𝓸𝓬𝓲𝓽𝔂 𝓒𝓱𝓪𝓻𝓽: {ticker}", font=dict(size=16, color="#e2e8f0"))
    )
    return fig

# --- Dashboad Start ---
st.title("✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓣𝓮𝓻𝓶𝓲𝓷𝓪𝓵 𝓿2.1 ✦")
st.markdown("---")

# Mapeamento de Ativos e Seus Setores (Benchmarks)
# GEV -> XLU (Utilities), MU/NVDA -> SOXX (Semis), BTC -> QQQ (Nasdaq)
portfolio = {
    "GEV": "XLU",
    "MU": "SOXX",
    "NVDA": "SOXX",
    "BTC-USD": "QQQ",
    "GC=F": "UUP" # Ouro vs Dólar
}

tabs = st.tabs([f"   {t}   " for t in portfolio.keys()])

for i, (ticker, sector) in enumerate(portfolio.items()):
    with tabs[i]:
        # Ingestão de Dados
        asset_data = AlphaTerminalEngine.get_clean_data(ticker)
        sector_data = AlphaTerminalEngine.get_clean_data(sector)
        
        metrics = AlphaTerminalEngine.calculate_metrics(asset_data, sector_data)
        
        if metrics:
            col_info, col_chart = st.columns([1, 2.5])
            
            with col_info:
                # 1. Card Principal
                st.metric(
                    label="𝓜𝓪𝓽𝓻𝓲𝔁 𝓥𝓪𝓵𝓾𝓮", 
                    value=metrics["current_mom"], 
                    delta=f"{metrics['score']}/4 Bull Score"
                )
                
                # 2. Sector Edge Display
                rsc = metrics["relative_strength"]
                rsc_color = "#00ffaa" if rsc > 0 else "#ff4b4b"
                st.markdown(f"""
                    <div class="sector-box" style="border: 1px solid {rsc_color}; color: {rsc_color};">
                        𝓢𝓮𝓬𝓽𝓸𝓻 𝓔𝓭𝓰𝓮: {rsc}% vs {sector}
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # 3. Veredito Alpha
                if metrics["is_hook_up"] and rsc > -1:
                    st.success("🎯 𝓢𝓣𝓡𝓞𝓝𝓖 𝓑𝓤𝓨 (𝓒𝓸𝓷𝓯𝓲𝓻𝓶𝓮𝓭)")
                elif metrics["is_hook_down"]:
                    st.error("⚠️ 𝓣𝓐𝓚𝓔 𝓟𝓡𝓞𝓕𝓘𝓣")
                else:
                    st.info("⌛ 𝓢𝓣𝓐𝓝𝓓𝓑𝓨 (𝓝𝓸 𝓢𝓲𝓰𝓷𝓪𝓵)")
                
                # Detalhes extra de Alpha
                with st.expander("Ver Detalhes Quantitativos"):
                    st.write(f"Trend: {'Bullish' if metrics['score'] >= 2 else 'Bearish'}")
                    st.write(f"Volume vs Avg: {round(float(asset_data['Volume'].iloc[-1]/asset_data['Volume'].rolling(20).mean().iloc[-1]), 2)}x")

            with col_chart:
                st.plotly_chart(draw_alpha_chart(metrics["series"], ticker), use_container_width=True)
        else:
            st.error(f"Erro ao sincronizar dados para {ticker}. Verifica a ligação à API.")

st.markdown("---")
st.caption("Alpha Sentinel Terminal | v2.1 Quantitative Engine | Developed for High-Frequency Analysis")
