import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st

# --- PAGE SETUP ---
try:
    st.set_page_config(page_title="Alpha Momentum Matrix", layout="wide")
except:
    pass

st.title("🛡️ Alpha Institutional Terminal")
st.markdown("Advanced Compression & Institutional Acceleration Matrix")

# --- DATA ENGINE ---
def get_institutional_data(ticker, tf):
    try:
        df = yf.download(ticker, period="100d", interval=tf, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty or len(df) < 30: 
            return None
        return df
    except:
        return None

def calc_alpha_signals(df):
    try:
        # Bands & Channels
        bb = ta.bbands(df['Close'], length=20, std=2.0)
        kc = ta.kc(df['High'], df['Low'], df['Close'], length=20, scalar=1.5)
        
        if bb is None or kc is None: return None

        # Squeeze Logic
        sqz_on = (bb.iloc[:, 0] > kc.iloc[:, 0]) & (bb.iloc[:, 2] < kc.iloc[:, 2])
        df['sqz_on'] = sqz_on
        df['sqz_duration'] = df['sqz_on'].groupby((~df['sqz_on']).cumsum()).cumsum()
        
        # Momentum & Acceleration
        mom = ta.linreg(df['Close'] - df['Close'].rolling(20).mean(), length=20)
        mom_acc = mom.diff()
        
        # Relative Volume (RVOL) - Institutional Core Metric
        vol_sma = ta.sma(df['Volume'], 20)
        rvol = df['Volume'] / vol_sma
        
        last = -1
        return {
            "Ticker": "TEMP",
            "Price": float(df['Close'].iloc[last]),
            "Squeeze": "🔴 ON" if sqz_on.iloc[last] else "🟢 FIRE",
            "Squeeze Days": int(df['sqz_duration'].iloc[last]),
            "Momentum": "BULL" if mom.iloc[last] > 0 else "BEAR",
            "Acceleration": round(float(mom_acc.iloc[last]), 2),
            "RVOL": round(float(rvol.iloc[last]), 2)
        }
    except:
        return None

# --- UI & DASHBOARD ---
with st.sidebar:
    st.header("Radar Parameters")
    tickers_list = st.text_area("Watchlist (Comma separated)", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, AAPL, TSLA, NVDA").split(",")
    tf_choice = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
    btn = st.button("RUN MARKET SCAN")

if btn:
    st.write("Processing high-precision metrics...")
    results = []
    
    for t in tickers_list:
        symbol = t.strip()
        if not symbol: continue
            
        df_raw = get_institutional_data(symbol, tf_choice)
        
        if df_raw is not None:
            sigs = calc_alpha_signals(df_raw)
            if sigs:
                sigs["Ticker"] = symbol
                results.append(sigs)
    
    if results:
        res_df = pd.DataFrame(results)
        
        # --- TOP METRICS ---
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Assets in Squeeze", len(res_df[res_df['Squeeze'] == "🔴 ON"]))
        col2.metric("Bullish Momentum", len(res_df[res_df['Momentum'] == "BULL"]))
        
        # Count assets with high institutional volume (RVOL > 1.2)
        high_vol = len(res_df[res_df['RVOL'] > 1.2])
        col3.metric("High RVOL Detects (>1.2)", high_vol)
        st.divider()
        
        # --- VISUAL COMPONENTS ---
        viz_col1, viz_col2 = st.columns([2, 1])

        with viz_col1:
            st.subheader("Market Confluence Matrix")
            # Custom Styling
            def highlight_squeeze(val):
                return 'color: #0055FF; font-weight: bold' if val == "🔴 ON" else 'color: #00FFAA'
                
            def highlight_mom(val):
                return 'color: #00FFAA; font-weight: bold' if val == "BULL" else 'color: #0055FF'
                
            def color_accel_rvol(val):
                try:
                    color = '#00FFAA' if float(val) > 0 else '#0055FF'
                    if float(val) > 1.5: return 'color: #00FFAA; font-weight: bold' # High RVOL highlight
                    return f'color: {color}'
                except:
                    return ''

            def heatmap_squeeze(val):
                try:
                    if pd.isna(val) or val == 0: return ''
                    alpha = min(float(val) / 15.0, 0.8) 
                    return f'background-color: rgba(0, 85, 255, {alpha}); color: white; font-weight: bold;'
                except:
                    return ''

            styled_df = (res_df.style
                         .map(highlight_squeeze, subset=['Squeeze'])
                         .map(highlight_mom, subset=['Momentum'])
                         .map(color_accel_rvol, subset=['Acceleration', 'RVOL'])
                         .map(heatmap_squeeze, subset=['Squeeze Days'])
                         .format({'Price': "${:.2f}", 'Acceleration': "{:+.2f}", 'RVOL': "{:.2f}x"}))

            st.dataframe(styled_df, use_container_width=True, height=400)
            
        with viz_col2:
            st.subheader("Alpha Rotation Radar")
            st.caption("X: Acceleration | Y: Squeeze Days")
            # Using native Streamlit scatter chart mapped to our core metrics
            plot_df = res_df.set_index("Ticker")[["Acceleration", "Squeeze Days"]]
            st.scatter_chart(plot_df, x="Acceleration", y="Squeeze Days", color="#00FFAA", height=350)
            
    else:
        st.warning("No clean data found. Please check your connection or asset list.")
