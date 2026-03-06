import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Master Configuration
st.set_page_config(page_title="Alpha Verdict Dashboard", layout="wide")

# Colors
AQUA = "#00FBFF"
BLUE = "#3D5AFE"
WHITE = "#FFFFFF"

st.markdown(f"""
<style>
    .main {{ background-color: #0F0F0F; }}
    div[data-testid='stMetric'] {{ 
        background-color: #161616; padding: 25px; border-radius: 10px; border: 1px solid #333; 
    }}
    .verdict-card {{
        background-color: #161616; padding: 20px; border-radius: 10px; border-left: 5px solid {BLUE}; margin-bottom: 10px;
    }}
    h1, h2, h3 {{ font-family: serif; color: {WHITE}; }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def get_market_verdict():
    try:
        # Fetch Data
        df = yf.download(["BTC-USD", "USDT-USD"], period="max", interval="1d", progress=False)
        btc = df['Close']['BTC-USD']
        vol_btc = df['Volume']['BTC-USD']
        vol_usdt = df['Volume']['USDT-USD']
        
        data = pd.DataFrame({'price': btc, 'vol': vol_btc, 'usdt': vol_usdt}).dropna()
        
        # --- CALCULATION ENGINES (Last Z-Scores) ---
        results = {}
        
        # 1. ACD (350d)
        log_p = np.log(data['price'])
        acd_z = (log_p.rolling(350).mean() - log_p) / log_p.rolling(350).std()
        results['ACD'] = acd_z.iloc[-1]
        
        # 2. MVRV (365d)
        mvrv_log = np.log(data['price'] / data['price'].rolling(365).mean())
        mvrv_z = (mvrv_log.rolling(350).mean() - mvrv_log) / mvrv_log.rolling(350).std()
        results['MVRV'] = mvrv_z.iloc[-1]
        
        # 3. NUPL (180d)
        nupl_raw = (data['price'] - data['price'].rolling(180).mean()) / data['price']
        nupl_z = (nupl_raw.rolling(350).mean() - nupl_raw) / nupl_raw.rolling(350).std()
        results['NUPL'] = nupl_z.iloc[-1]
        
        # 4. SSR (Liquidity)
        ssr_raw = np.log(data['price'] / data['usdt'].rolling(20).mean())
        ssr_z = (ssr_raw.rolling(350).mean() - ssr_raw) / ssr_raw.rolling(350).std()
        results['SSR'] = ssr_z.iloc[-1]
        
        # 5. SOPR (90d VWRP)
        pv = data['price'] * data['vol']
        vwrp = pv.rolling(90).sum() / data['vol'].rolling(90).sum()
        sopr_z = (np.log(data['price']/vwrp).rolling(350).mean() - np.log(data['price']/vwrp)) / np.log(data['price']/vwrp).rolling(350).std()
        results['SOPR'] = sopr_z.iloc[-1]
        
        # 6. Puell Multiple (365d)
        vol_30 = data['price'].pct_change().rolling(30).std()
        issuance = 3.125 * 144 * data['price'] / (1 + vol_30)
        puell_raw = np.log(issuance / issuance.rolling(365).mean())
        puell_z = (puell_raw.rolling(350).mean() - puell_raw) / puell_raw.rolling(350).std()
        results['PUELL'] = puell_z.iloc[-1]
        
        return results, data['price'].iloc[-1]
    except:
        return {}, 0

# --- UI RENDER ---
results, live_price = get_market_verdict()

if results:
    # Calculate Alpha Score (0-100)
    # Each Z-Score >= 2.0 adds to the score. Neutral = 0.
    bullish_signals = sum(1 for z in results.values() if z >= 1.0)
    alpha_score = (bullish_signals / len(results)) * 100
    
    st.markdown("<h1 style='text-align: center; font-size: 50px;'>✦ ALPHA VERDICT ✦</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: {AQUA if alpha_score > 50 else BLUE};'>Current Market Alpha Score: {alpha_score:.1f}%</h3>", unsafe_allow_html=True)
    
    st.divider()

    # Main Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("BTC PRICE", f"${live_price:,.2f}")
    
    # Verdict Sentiment
    verdict_text = "NEUTRAL / ACCUMULATE"
    v_color = WHITE
    if alpha_score >= 80: verdict_text, v_color = "STRONG BUY / GENERATIONAL BOTTOM", AQUA
    elif alpha_score <= 20: verdict_text, v_color = "STRONG SELL / CYCLE TOP", BLUE
    
    c2.metric("CONFLUENCE LEVEL", f"{bullish_signals}/6 Indicators")
    c3.markdown(f"<h2 style='text-align: center; color: {v_color};'>{verdict_text}</h2>", unsafe_allow_html=True)

    st.markdown("### ✦ Indicator Matrix Breakdown")
    
    # Create 2 rows of 3 columns for indicators
    cols = st.columns(3)
    idx = 0
    for name, z in results.items():
        with cols[idx % 3]:
            # Determine Indicator Sentiment
            status = "NEUTRAL"
            color = WHITE
            if z >= 2.0: status, color = "💎 BULLISH (OVERSOLD)", AQUA
            elif z <= -2.0: status, color = "🔴 BEARISH (OVERBOUGHT)", BLUE
            elif 1.0 <= z < 2.0: status, color = "🔹 MILD BULLISH", AQUA
            elif -2.0 < z <= -1.0: status, color = "🔸 MILD BEARISH", BLUE
            
            st.markdown(f"""
                <div class="verdict-card" style="border-left: 5px solid {color};">
                    <p style="color: #888; margin-bottom: 0;">{name} SIGNAL</p>
                    <h3 style="margin-top: 5px; color: {color};">{status}</h3>
                    <p style="font-size: 12px; color: #555;">Z-Score: {z:.2f} SD</p>
                </div>
            """, unsafe_allow_html=True)
        idx += 1

    # --- ALPHA SCORE GAUGE (Simulated) ---
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = alpha_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Market Health Index", 'font': {'size': 24, 'color': WHITE}},
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': WHITE},
            'bar': {'color': AQUA if alpha_score > 50 else BLUE},
            'bgcolor': "#161616",
            'borderwidth': 2,
            'bordercolor': "#333",
            'steps': [
                {'range': [0, 20], 'color': 'rgba(61, 90, 254, 0.3)'},
                {'range': [80, 100], 'color': 'rgba(0, 251, 255, 0.3)'}
            ],
        }
    ))
    fig.update_layout(paper_bgcolor="#0F0F0F", font={'color': WHITE, 'family': "Serif"}, height=400)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Engine failure. Please check data source connection.")
