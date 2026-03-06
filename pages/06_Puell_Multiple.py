import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# High-Performance Terminal Config
st.set_page_config(page_title="07 Puell Multiple Terminal", layout="wide")

# Institutional Palette
AQUA = "#00FBFF"
BLUE = "#3D5AFE"
WHITE = "#FFFFFF"

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_puell_multiple_engine():
    try:
        # 1. Fetch BTC Price Data
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()

        # Robust Data Extraction
        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        data = pd.DataFrame({'price': price})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # 2. Block Reward Logic (Halving Schedule)
        def get_block_reward(date):
            if date < pd.Timestamp('2012-11-28'): return 50.0
            elif date < pd.Timestamp('2016-07-09'): return 25.0
            elif date < pd.Timestamp('2020-05-11'): return 12.5
            elif date < pd.Timestamp('2024-04-20'): return 6.25
            else: return 3.125 # Current reward in 2026

        # Apply rewards and calculate Daily Issuance (USD)
        data['reward'] = [get_block_reward(d) for d in data.index]
        # Approx 144 blocks per day
        data['daily_issuance_usd'] = data['reward'] * 144 * data['price']

        # 3. Puell Multiple Calculation
        # Ratio = Daily Issuance / 365-day MA of Daily Issuance
        data['ma_issuance'] = data['daily_issuance_usd'].rolling(window=365).mean()
        data['puell_raw'] = data['daily_issuance_usd'] / data['ma_issuance']
        
        # 4. Normalization (Log Z-Score)
        data['log_puell'] = np.log(data['puell_raw'].replace(0, np.nan)).ffill()
        window = 350
        data['mean'] = data['log_puell'].rolling(window=window).mean()
        data['std'] = data['log_puell'].rolling(window=window).std()
        
        # ALPHA PARITY: Aqua (Top/Pain/Buy) | Blue (Bottom/Profit/Sell)
        data['z'] = ((data['mean'] - data['log_puell']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except Exception as e:
        st.error(f"Engine Alert: {str(e)}")
        return pd.DataFrame()

data = fetch_puell_multiple_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # Sentiment Matrix (Consistent with Pentágono do Alpha)
    status, s_color = "NEUTRAL", WHITE
    if last_z >= 2.0: status, s_color = "💎 MINER CAPITULATION (EXTREME BUY)", AQUA
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 MINER REVENUE STRESS", AQUA
    elif last_z <= -2.0: status, s_color = "🔴 MINER EUPHORIA (EXTREME SELL)", BLUE
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 HIGH REVENUE EXPANSION", BLUE

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Construction
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Pane 1: Price
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Pane 2: Z-Score
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Threshold Lines
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Sentiment Fills
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
