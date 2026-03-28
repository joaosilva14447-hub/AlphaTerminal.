import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
st.set_page_config(page_title="Alpha Momentum Matrix V5", layout="wide")

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

# Lookback Mapping for Statistical Consistency
TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- 2. CORE MATHEMATICS (ELITE CALIBRATION) ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

def calculate_signals_v5(df, timeframe):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    ema20 = data['Close'].ewm(span=20, adjust=False).mean()
    ema200 = data['Close'].ewm(span=200, adjust=False).mean()
    
    # ATR & Squeeze Logic
    tr = pd.concat([(data['High'] - data['Low']), 
                    (data['High'] - data['Close'].shift(1)).abs(), 
                    (data['Low'] - data['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr20 = tr.ewm(alpha=1/20, adjust=False).mean()
    
    sqz_on = (data['Close'].rolling(20).std() * 2.0 < 1.5 * atr20)
    
    # Squeeze Decay Factor (The Edge)
    fired_counter = (~sqz_on).groupby(sqz_on.cumsum()).cumsum()
    sqz_decay = np.where((~sqz_on) & (fired_counter <= 5), (6 - fired_counter) / 5, 0)
    
    # Normalized Momentum & Acceleration
    mom_raw = (data['Close'] - ema20) / atr20.replace(0, np.nan)
    mom_z = _rolling_zscore(mom_raw.ewm(span=5).mean(), z_win)
    acc_z = _rolling_zscore(mom_z.diff(), z_win)
    
    # RVOL
    rvol = data['Volume'] / data['Volume'].rolling(20).mean()
    rvol_z = _rolling_zscore(np.log(rvol.replace(0, np.nan)), z_win)

    # Adaptive Weighting
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

# --- 3. VISUAL ENGINE (NO MATPLOTLIB DEPENDENCY) ---
def style_matrix(res_df):
    def score_color(val):
        alpha = min(abs(val - 50) / 40, 0.6)
        color = f"rgba(0, 255, 170, {alpha})" if val > 50 else f"rgba(255, 92, 92, {alpha})"
        return f'background-color: {color}; color: white; font-weight: bold;'

    return res_df.style.map(score_color, subset=['Score']).format({
        'Score': '{:.1f}', 'Price': '${:.2f}', 'MomZ': '{:+.2f}', 'AccZ': '{:+.2f}', 'RVOL': '{:.2f}x'
    })

def build_rotation_radar(res_df):
    fig = go.Figure()

    # Probability Quadrants (Visual Guide)
    # Top-Right: Expansion Zone
    fig.add_shape(type="rect", x0=0, y0=0, x1=3.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0)
    # Bottom-Left: Capitulation Zone
    fig.add_shape(type="rect", x0=-3.5, y0=-3.5, x1=0, y1=0, fillcolor="rgba(255, 92, 92, 0.05)", line_width=0)

    # Asset Scatter Trace
    fig.add_trace(go.Scatter(
        x=res_df['MomZ'], y=res_df['AccZ'],
        mode='markers+text',
        text=res_df['Asset'],
        textposition="top center",
        marker=dict(
            size=res_df['RVOL'].clip(1, 3) * 12,
            color=res_df['Score'],
            colorscale=[[0, '#FF5C5C'], [0.5, '#444'], [1, '#00FFAA']],
            line=dict(width=1, color='white'),
            showscale=True
        ),
        hovertemplate="<b>%{text}</b><br>MomZ: %{x:.2f}<br>AccZ: %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title="Alpha Rotation Radar (Expansion vs Compression)",
        xaxis=dict(title="Momentum Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        yaxis=dict(title="Acceleration Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=600,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- 4. MAIN INTERFACE ---
st.title("🛡️ Alpha Momentum Matrix V5")
st.caption("Execution-ready Institutional Dashboard | 05:00 AM Protocol Enabled")

with st.sidebar:
    st.header("Terminal Config")
    watchlist_raw = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA")
    tf = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
    btn = st.button("RUN QUANT SCAN")

if btn:
    results = []
    watchlist = [s.strip().upper() for s in watchlist_raw.split(",") if s.strip()]
    
    with st.spinner("Calculating Statistical Edge..."):
        for symbol in watchlist:
            try:
                # Interval mapping
                interval = "60m" if tf != "1d" else "1d"
                hist = yf.download(symbol, period="2y", interval=interval, progress=False)
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
            except:
                continue

    if results:
        res_df = pd.DataFrame(results).sort_values("Score", ascending=False)
        
        # Matrix Metrics
        col1, col2, col3 = st.columns(3)
        top_asset = res_df.iloc[0]
        col1.metric("Top Pick", top_asset['Asset'], f"{top_asset['Score']:.1f}")
        col2.metric("Market Bias", "BULLISH" if res_df['Score'].mean() > 50 else "BEARISH")
        col3.metric("Squeeze Alerts", len(res_df[res_df['Squeeze'] == "🔴 ON"]))
        
        st.divider()
        
        # Display Matrix
        st.subheader("Institutional Confluence Matrix")
        st.dataframe(style_matrix(res_df), use_container_width=True)
        
        st.divider()
        
        # Display Radar
        st.plotly_chart(build_rotation_radar(res_df), use_container_width=True)
        
    else:
        st.warning("No data found. Ensure tickers are correct.")
