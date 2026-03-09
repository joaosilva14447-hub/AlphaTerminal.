import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Configuração Alpha
st.set_page_config(page_title="Alpha Terminal | Puell Multiple", layout="wide")

AQUA = "#00FBFF"
BLUE = "#3D5AFE"

st.markdown(f"""
<style>
    .main {{ background-color: #0F0F0F; }}
    h1 {{ font-family: 'Inter', sans-serif; letter-spacing: -1px; }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_puell_final_engine():
    try:
        t = yf.Ticker("BTC-USD")
        df = t.history(period="max")
        if df.empty: return None

        data = pd.DataFrame(index=df.index)
        data['price'] = df['Close'].astype(float)
        
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            if d < pd.Timestamp('2016-07-09'): return 25.0
            if d < pd.Timestamp('2020-05-11'): return 12.5
            if d < pd.Timestamp('2024-04-20'): return 6.25
            return 3.125
            
        data['issuance'] = [get_reward(d) * 144 for d in data.index]
        data['revenue'] = data['issuance'] * data['price']
        
        data['ma365'] = data['revenue'].rolling(window=365, min_periods=100).mean()
        data['puell'] = data['revenue'] / data['ma365']
        
        data['log_p'] = np.log(data['puell'].replace(0, np.nan)).ffill()
        data['z_mean'] = data['log_p'].rolling(window=350, min_periods=100).mean()
        data['z_std'] = data['log_p'].rolling(window=350, min_periods=100).std()
        
        # Z-Score (Invertido: Capitulação no Topo)
        data['z'] = ((data['z_mean'] - data['log_p']) / data['z_std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['price', 'z'])
    except:
        return None

# --- UI EXECUTION ---
data = fetch_puell_final_engine()

if data is not None:
    last_z = data['z'].iloc[-1]
    
    # Matriz de Decisão Dinâmica (Cores Fixas para o Sinal)
    if last_z >= 2.0:
        status, s_color = "💎 CAPITULATION (BUY)", AQUA
    elif 1.0 <= last_z < 2.0:
        status, s_color = "🔹 REVENUE STRESS", "#99f9ff"
    elif last_z <= -2.0:
        status, s_color = "🔴 EUPHORIA (SELL)", BLUE
    elif -2.0 < last_z <= -1.0:
        status, s_color = "🔸 REVENUE EXPANSION", "#7c8efc"
    else:
        status, s_color = "⚡ NEUTRAL", "#FFFFFF"

    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")
    
    # Injeção de HTML Limpa (Sem erro de renderização)
    c3.markdown(f"""
        <div style="text-align: right; padding-top: 15px;">
            <span style="color: {s_color}; font-size: 28px; font-weight: bold; text-shadow: 0px 0px 10px {s_color}44;">
                {status}
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Gráfico Alpha
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.4])

    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Zonas de Shading Profissionais (hrect)
    # Capitulação (BUY - Aqua)
    fig.add_hrect(y0=2.0, y1=3.5, fillcolor=AQUA, opacity=0.15, line_width=0, row=2, col=1)
    fig.add_hline(y=2.0, line=dict(color=AQUA, width=1, dash="dash"), row=2, col=1)

    # Euforia (SELL - Blue)
    fig.add_hrect(y0=-3.5, y1=-2.0, fillcolor=BLUE, opacity=0.15, line_width=0, row=2, col=1)
    fig.add_hline(y=-2.0, line=dict(color=BLUE, width=1, dash="dash"), row=2, col=1)

    fig.update_layout(template="plotly_dark", height=850, margin=dict(l=50, r=50, t=30, b=50), showlegend=False, paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F")
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, autorange="reversed", range=[-3.5, 3.5], showgrid=False)

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Engine Synchronization Failed. Check Logs.")
