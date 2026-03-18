import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# 1. Configuração de Estética Institutional
st.set_page_config(page_title="Alpha Sentinel Terminal v2.2", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #05070a; }
    div[data-testid="stMetric"] {
        background-color: #0e1117;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #1e293b;
    }
    .status-box {
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-top: 10px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

class AlphaTerminalEngine:
    @staticmethod
    def get_clean_data(ticker, days=100):
        try:
            data = yf.download(ticker, period=f"{days}d", interval="1d", progress=False, auto_adjust=True)
            if data.empty: return None
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return data
        except Exception:
            return None

    @staticmethod
    def calculate_alpha_matrix(df):
        if df is None or len(df) < 35: return None
        
        close = df['Close']
        vol = df['Volume']
        
        # --- Alpha Matrix Core (Price + Volume Flow) ---
        roc = close.pct_change(14)
        vol_avg = vol.rolling(20).mean()
        # O segredo: Multiplicador de força baseado em anomalias de volume
        vol_weight = np.clip(vol / vol_avg, 0.5, 3.0) 
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        matrix_series = 100 - (100 / (1 + rs))
        
        # --- Bull Score 0/4 (Internal Rules) ---
        score = 0
        curr_mom = float(matrix_series.iloc[-1])
        prev_mom = float(matrix_series.iloc[-2])
        curr_vol_ratio = float(vol.iloc[-1] / vol_avg.iloc[-1])
        
        if curr_mom < 30: score += 1 # Oversold Condition
        if curr_mom > prev_mom: score += 1 # Momentum Recovery (Hook)
        if float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1]): score += 1 # Trend Confirmation
        if curr_vol_ratio > 1.0: score += 1 # Volume Inflow Confirmation
        
        return {
            "series": matrix_series,
            "current_mom": round(curr_mom, 1),
            "score": score,
            "vol_ratio": round(curr_vol_ratio, 2),
            "is_hook_up": curr_mom < 40 and curr_mom > prev_mom,
            "is_hook_down": curr_mom > 60 and curr_mom < prev_mom
        }

def draw_velocity_chart(series, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=series, mode='lines', 
        line=dict(color='#00f2ff', width=3),
        fill='tozeroy', fillcolor='rgba(0, 242, 255, 0.05)',
        name="Velocity"
    ))
    # Threshold Lines
    fig.add_hline(y=70, line_dash="dot", line_color="#ff4b4b", opacity=0.3)
    fig.add_hline(y=30, line_dash="dot", line_color="#00ffaa", opacity=0.3)
    
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(range=[0, 100], color="#64748b", gridcolor="#1e293b", showgrid=True),
        xaxis=dict(showgrid=False, showticklabels=False),
        title=dict(text=f"𝓥𝓮𝓵𝓸𝓬𝓲𝓽𝔂 𝓥𝓮𝓬𝓽𝓸𝓻: {ticker}", font=dict(size=16, color="#e2e8f0"))
    )
    return fig

# --- Interface Principale ---
st.title("✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓣𝓮𝓻𝓶𝓲𝓷𝓪𝓵 𝓿2.2 ✦")

# Portfolio limpo, sem benchmarks externos
portfolio = ["BTC-USD", "NVDA", "MU", "GEV", "GC=F"]
tabs = st.tabs([f"    {t}    " for t in portfolio])

for i, ticker in enumerate(portfolio):
    with tabs[i]:
        data = AlphaTerminalEngine.get_clean_data(ticker)
        metrics = AlphaTerminalEngine.calculate_alpha_matrix(data)
        
        if metrics:
            col_metrics, col_chart = st.columns([1, 2.2])
            
            with col_metrics:
                st.metric(
                    label="𝓜𝓪𝓽𝓻𝓲𝔁 𝓥𝓪𝓵𝓾𝓮", 
                    value=f"{metrics['current_mom']} pts", 
                    delta=f"Bull Score: {metrics['score']}/4"
                )
                
                # Volume Force Display (Substitui o Sector Edge)
                v_ratio = metrics['vol_ratio']
                v_color = "#00ffaa" if v_ratio > 1 else "#64748b"
                st.markdown(f"""
                    <div class="status-box" style="border: 1px solid {v_color}; color: {v_color};">
                        𝓥𝓸𝓵𝓾𝓶𝓮 𝓕𝓸𝓻𝓬𝓮: {v_ratio}x Avg
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Alpha Decision Engine
                if metrics["score"] >= 3 and metrics["is_hook_up"]:
                    st.success("🎯 𝓢𝓣𝓡𝓞𝓝𝓖 𝓑𝓤𝓨 (𝓒𝓸𝓷𝓯𝓲𝓻𝓶𝓮𝓭)")
                elif metrics["is_hook_down"] and metrics["current_mom"] > 65:
                    st.error("⚠️ 𝓣𝓐𝓚𝓔 𝓟𝓡𝓞𝓕𝓘𝓣")
                else:
                    st.info("⌛ 𝓢𝓣𝓐𝓝𝓓𝓑𝓨 (𝓝𝓸 𝓢𝓲𝓰𝓷𝓪𝓵)")
                
                with st.expander("Quant Details"):
                    st.write(f"Trend Status: {'Bullish' if metrics['score'] >= 2 else 'Bearish'}")
                    st.write(f"Relative Velocity: {metrics['current_mom']}%")

            with col_chart:
                st.plotly_chart(draw_velocity_chart(metrics["series"], ticker), use_container_width=True)

st.markdown("---")
st.caption("Alpha Sentinel Terminal | v2.2 Internal Matrix Engine | Institutional Grade Analytics")
