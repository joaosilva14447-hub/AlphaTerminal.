import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="Alpha Momentum Matrix V5", layout="wide")

# Custom CSS for a clean Institutional Dark Theme
st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }
</style>
""", unsafe_allow_html=True)

# Lookback Configuration
TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- MATH CORE ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

# --- ENGINE V5 ---
def calculate_signals_v5(df, timeframe):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    ema20 = data['Close'].ewm(span=20, adjust=False).mean()
    ema200 = data['Close'].ewm(span=200, adjust=False).mean()
    
    # ATR & Squeeze
    tr = pd.concat([(data['High'] - data['Low']), 
                    (data['High'] - data['Close'].shift(1)).abs(), 
                    (data['Low'] - data['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr20 = tr.ewm(alpha=1/20, adjust=False).mean()
    
    sqz_on = (data['Close'].rolling(20).std() * 2.0 < 1.5 * atr20)
    
    # Decay Logic (The Edge)
    fired_counter = (~sqz_on).groupby(sqz_on.cumsum()).cumsum()
    sqz_decay = np.where((~sqz_on) & (fired_counter <= 5), (6 - fired_counter) / 5, 0)
    
    # Momentum & Acceleration
    mom_raw = (data['Close'] - ema20) / atr20.replace(0, np.nan)
    mom_z = _rolling_zscore(mom_raw.ewm(span=5).mean(), z_win)
    acc_z = _rolling_zscore(mom_z.diff(), z_win)
    
    # Volume
    rvol = data['Volume'] / data['Volume'].rolling(20).mean()
    rvol_z = _rolling_zscore(np.log(rvol.replace(0, np.nan)), z_win)

    # Scoring Weights
    w_mom, w_acc, w_vol = (0.45, 0.40, 0.15) if timeframe != '1d' else (0.55, 0.30, 0.15)
    
    raw = (w_mom * mom_z.clip(-3, 3) + w_acc * acc_z.clip(-3, 3) + w_vol * rvol_z.clip(-3, 3) * np.sign(mom_z.fillna(0)))
    bias = np.where(sqz_decay > 0, np.sign(mom_z.fillna(0)) * 0.25 * sqz_decay, 0)
    regime = np.where((data['Close'] > ema200) & (ema200.diff() > 0), 0.3, 
                      np.where((data['Close'] < ema200) & (ema200.diff() < 0), -0.3, 0))
    
    score = 50.0 + 40.0 * np.tanh((raw + bias + regime) / 2.0)
    
    data['Score'] = score.fillna(50.0)
    data['MomZ'] = mom_z.fillna(0)
    data['AccZ'] = acc_z.fillna(0)
    data['RVOL'] = rvol.fillna(1.0)
    data['Squeeze'] = sqz_on
    return data.iloc[-1:]

# --- UI STYLING (No Matplotlib dependency) ---
def style_v5(res_df):
    def score_color(val):
        # Green for Bullish (>55), Red for Bearish (<45)
        alpha = min(abs(val - 50) / 40, 0.6)
        color = f"rgba(0, 255, 170, {alpha})" if val > 50 else f"rgba(255, 92, 92, {alpha})"
        return f'background-color: {color}; color: white; font-weight: bold;'

    return res_df.style.map(score_color, subset=['Score']).format({
        'Score': '{:.1f}', 'Price': '{:.2f}', 'MomZ': '{:+.2f}', 'AccZ': '{:+.2f}', 'RVOL': '{:.2f}x'
    })

# --- MAIN APP ---
st.title("🛡️ Alpha Momentum Matrix V5")

with st.sidebar:
    st.header("Radar Controls")
    watchlist = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA").split(",")
    tf = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
    btn = st.button("EXECUTE QUANT SCAN")

if btn:
    results = []
    with st.spinner("Analyzing Market Structure..."):
        for symbol in [s.strip().upper() for s in watchlist if s.strip()]:
            try:
                # Optimized Download
                hist = yf.download(symbol, period="2y", interval="1d" if tf == "1d" else "60m", progress=False)
                hist = _flatten_columns(hist)
                if len(hist) > 150:
                    last_row = calculate_signals_v5(hist, tf)
                    results.append({
                        "Asset": symbol,
                        "Price": last_row['Close'].values[0],
                        "Score": last_row['Score'].values[0],
                        "MomZ": last_row['MomZ'].values[0],
                        "AccZ": last_row['AccZ'].values[0],
                        "RVOL": last_row['RVOL'].values[0],
                        "Squeeze": "🔴 ON" if last_row['Squeeze'].values[0] else "🟢 OFF"
                    })
            except Exception as e:
                st.error(f"Error {symbol}: {e}")

    if results:
        res_df = pd.DataFrame(results).sort_values("Score", ascending=False)
        
        # High-Value Metrics
        c1, c2 = st.columns(2)
        top_asset = res_df.iloc[0]
        c1.metric("Top Alpha Pick", top_asset['Asset'], f"{top_asset['Score']:.1f} Score")
        c2.metric("Market Sentiment", "BULLISH" if res_df['Score'].mean() > 50 else "BEARISH")
        
        st.dataframe(style_v5(res_df), use_container_width=True)
    else:
        st.warning("No data found. Check tickers.")
