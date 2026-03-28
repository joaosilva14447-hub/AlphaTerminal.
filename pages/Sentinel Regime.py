import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

# --- CORE SETTINGS & THEME ---
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

# Dynamic Lookback Mapping for Statistical Consistency
TF_LOOKBACKS = {
    "1h": 240,  # ~2 weeks of intraday data
    "4h": 180,  # ~1 month of data
    "1d": 126   # ~6 months of trading days
}

# --- MATHEMATICAL UTILS ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _ema(series, length):
    return series.ewm(span=length, adjust=False, min_periods=length).mean()

def _rolling_zscore(series, window):
    rolling_mean = series.rolling(window=window, min_periods=window//2).mean()
    rolling_std = series.rolling(window=window, min_periods=window//2).std()
    return (series - rolling_mean) / rolling_std.replace(0, np.nan)

# --- SIGNAL CALCULATOR (V5 HARDCORE) ---
def calculate_signals_v5(df, timeframe):
    data = df.copy()
    z_window = TF_LOOKBACKS.get(timeframe, 126)
    
    # 1. Volatility Basis
    ema20 = _ema(data['Close'], 20)
    ema200 = _ema(data['Close'], 200)
    
    # ATR for normalization
    prev_close = data['Close'].shift(1)
    tr = pd.concat([(data['High'] - data['Low']), 
                    (data['High'] - prev_close).abs(), 
                    (data['Low'] - prev_close).abs()], axis=1).max(axis=1)
    atr20 = tr.ewm(alpha=1/20, adjust=False).mean()

    # 2. Squeeze Dynamics & Exponential Decay
    bb_std = data['Close'].rolling(20).std()
    sqz_on = (bb_std * 2.0 < 1.5 * atr20) 
    
    # Squeeze Duration & Decay Factor
    # Decay ensures that a 'Fire' signal loses relevance over 5 bars
    sqz_group = (~sqz_on).cumsum()
    sqz_duration = sqz_on.groupby(sqz_group).cumsum()
    sqz_fired = (~sqz_on) & (sqz_on.shift(1))
    
    # Decay Calculation: 1.0 (at fire) down to 0.0 (after 5 bars)
    fired_counter = (~sqz_on).groupby(sqz_on.cumsum()).cumsum()
    sqz_decay = np.where(fired_counter <= 5, (6 - fired_counter) / 5, 0)
    sqz_decay = np.where(sqz_on, 0, sqz_decay)

    # 3. Momentum & Acceleration (Z-Score Calibrated)
    mom_raw = (data['Close'] - ema20) / atr20.replace(0, np.nan)
    mom_z = _rolling_zscore(_ema(mom_raw, 5), z_window)
    accel_z = _rolling_zscore(mom_z.diff(), z_window)
    
    # 4. Relative Volume (RVOL)
    rvol = data['Volume'] / data['Volume'].rolling(20).mean()
    rvol_z = _rolling_zscore(np.log(rvol.replace(0, np.nan)), z_window)

    # 5. Adaptive Setup Score (Weight Re-distribution)
    # Weights shifted towards Acceleration for Intraday accuracy
    w_mom, w_acc, w_vol = (0.45, 0.40, 0.15) if timeframe != '1d' else (0.55, 0.30, 0.15)
    
    raw_score = (w_mom * mom_z.clip(-3, 3) + 
                 w_acc * accel_z.clip(-3, 3) + 
                 w_vol * rvol_z.clip(-3, 3) * np.sign(mom_z))
    
    # Add Squeeze Release Bias with Decay
    release_bias = np.where(sqz_decay > 0, np.sign(mom_z) * 0.25 * sqz_decay, 0)
    regime_bias = np.where((data['Close'] > ema200) & (ema200.diff() > 0), 0.3, 
                           np.where((data['Close'] < ema200) & (ema200.diff() < 0), -0.3, 0))
    
    final_score = 50.0 + 40.0 * np.tanh((raw_score + release_bias + regime_bias) / 2.0)

    # Output Enrichment
    data['Score'] = final_score.clip(0, 100)
    data['MomZ'] = mom_z
    data['AccZ'] = accel_z
    data['RVOL'] = rvol
    data['SqueezeOn'] = sqz_on
    data['SqueezeDuration'] = sqz_duration
    data['Regime'] = np.where(regime_bias > 0, "Bull", np.where(regime_bias < 0, "Bear", "Range"))
    
    return data.dropna()

# --- VISUALS: PRO RADAR WITH QUADRANTS ---
def build_pro_radar(results):
    fig = go.Figure()
    
    # Add Quadrant Shapes for Visual Probability
    fig.add_vrect(x0=0.5, x1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0) # Momentum Bull
    fig.add_hrect(y0=0.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0) # Acceleration Bull
    
    fig.add_trace(go.Scatter(
        x=results['MomZ'], y=results['AccZ'],
        mode='markers+text',
        text=results['Asset'],
        textposition="top center",
        marker=dict(
            size=results['RVOL'].clip(1, 3) * 10,
            color=results['Score'],
            colorscale=[[0, '#FF5C5C'], [0.5, '#A0AEC0'], [1, '#00FFAA']],
            showscale=True,
            line=dict(width=1, color='white')
        )
    ))

    fig.update_layout(
        title="Institutional Rotation Radar (Probability Zones)",
        xaxis=dict(title="Momentum Z-Score", range=[-3.5, 3.5], gridcolor="#222"),
        yaxis=dict(title="Acceleration Z-Score", range=[-3.5, 3.5], gridcolor="#222"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=600,
        shapes=[
            dict(type="line", x0=0, y0=-3.5, x1=0, y1=3.5, line=dict(color="white", width=1, dash="dash")),
            dict(type="line", x0=-3.5, y0=0, x1=3.5, y1=0, line=dict(color="white", width=1, dash="dash"))
        ]
    )
    return fig

# --- MAIN INTERFACE (Simplified for Logic Focus) ---
st.title("🛡️ Alpha Momentum Matrix V5")
watchlist = st.sidebar.text_area("Watchlist", "BTC-USD, ETH-USD, NVDA, TSLA, GC=F").split(",")
tf = st.sidebar.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)

if st.sidebar.button("Execute Quantitative Scan"):
    all_results = []
    for symbol in watchlist:
        symbol = symbol.strip().upper()
        df = yf.download(symbol, period="100d" if tf != '1d' else "5y", interval="60m" if tf != '1d' else "1d", progress=False)
        df = _flatten_columns(df)
        
        if not df.empty and len(df) > 200:
            processed = calculate_signals_v5(df, tf)
            last = processed.iloc[-1]
            all_results.append({
                "Asset": symbol, "Score": last['Score'], "MomZ": last['MomZ'],
                "AccZ": last['AccZ'], "RVOL": last['RVOL'], "Squeeze": last['SqueezeOn'],
                "Regime": last['Regime']
            })
    
    if all_results:
        res_df = pd.DataFrame(all_results).sort_values("Score", ascending=False)
        
        st.metric("Top Alpha Pick", res_df.iloc[0]['Asset'], f"{res_df.iloc[0]['Score']:.1f} Score")
        st.dataframe(res_df.style.background_gradient(subset=['Score'], cmap='RdYlGn'))
        st.plotly_chart(build_pro_radar(res_df), use_container_width=True)
