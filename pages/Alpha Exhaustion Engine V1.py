import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
st.set_page_config(page_title="Alpha Exhaustion Engine V1.1", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid="stExpander"] {
        background-color: #161616;
        border: 1px solid #2A2A2A;
    }
    /* Primary Sidebar Button Styling (Tactical Orange for Reversion) */
    button[kind="primary"] {
        background-color: #FF9F43 !important; 
        color: #0F0F0F !important;
        font-weight: 800 !important;
        border: none !important;
        letter-spacing: 1px;
    }
    button[kind="primary"]:hover {
        background-color: #E68A00 !important;
    }
</style>
""", unsafe_allow_html=True)

TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- 2. DATA PIPELINE ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _resample_ohlcv(df, rule):
    df.index = pd.to_datetime(df.index).tz_localize(None)
    agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    return df.resample(rule).agg(agg_dict).dropna()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if not df.empty:
        return _flatten_columns(df)
    return pd.DataFrame()

# --- 3. CORE MATHEMATICS (EXHAUSTION ENGINE V1 - UNTOUCHED) ---
def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std().replace(0, np.nan)

def calculate_reversion_signals(df, timeframe, full_history=False):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    # 1. Rolling VWAP
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    vol_mean_20 = data['Volume'].rolling(20).sum().replace(0, np.nan)
    rolling_vwap = (typical_price * data['Volume']).rolling(20).sum() / vol_mean_20
    
    # VWAP Distance Z-Score
    dist_vwap = (data['Close'] - rolling_vwap) / rolling_vwap
    dist_z = _rolling_zscore(dist_vwap, z_win)
    
    # 2. Statistical RSI
    delta = data['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs.fillna(0)))
    rsi_z = _rolling_zscore(rsi, z_win)
    
    # 3. Bollinger Stretch (3rd Std Dev)
    basis = data['Close'].rolling(20).mean()
    dev = data['Close'].rolling( dev=data['Close'].rolling(20).std() )
    upper_3 = basis + 3 * dev
    lower_3 = basis - 3 * dev
    
    # 4. Rubber Band Tension Score (0 to 100)
    # Combining Distance Z (Gravity), RSI Z (Momentum Exhaustion), and BB Stretch
    bb_stretch_f = np.where(data['Close'] > upper_3, (data['Close'] - upper_3)/dev.replace(0,np.nan),
                    np.where(data['Close'] < lower_3, (data['Close'] - lower_3)/dev.replace(0,np.nan), 0))
    
    raw_tension = abs(dist_z.fillna(0)) * 0.4 + abs(rsi_z.fillna(0)) * 0.4 + abs(bb_stretch_f) * 0.2
    tension_score = 100 * np.tanh(raw_tension / 2.5) # Squash to 0-100 curve
    
    # Reversion Bias
    bias = np.where(dist_z > 0, "SHORT", "LONG")
    
    data['Tension'] = tension_score.fillna(0)
    data['Bias'] = bias
    data['VWAP'] = rolling_vwap
    data['DistZ'] = dist_z.fillna(0)
    data['RSIZ'] = rsi_z.fillna(0)
    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    
    if full_history:
        return data.dropna()
    else:
        return data.iloc[-1:]

# --- 4. VISUAL ENGINE ---
def build_exhaustion_radar(res_df):
    fig = go.Figure()
    # Exhaustion Zones
    fig.add_shape(type="rect", x0=1.5, y0=1.5, x1=4, y1=4, fillcolor="rgba(255, 92, 92, 0.08)", line_width=0) # Overbought SHORT
    fig.add_shape(type="rect", x0=-4, y0=-4, x1=-1.5, y1=-1.5, fillcolor="rgba(0, 255, 170, 0.08)", line_width=0) # Oversold LONG

    # Marker colors based on Bias
    colors = np.where(res_df['Target Bias'] == "SHORT", "#FF5C5C", "#00FFAA")

    fig.add_trace(go.Scatter(
        x=res_df['VWAP Dist Z'], y=res_df['RSI Z'],
        mode='markers+text', text=res_df['Asset'], textposition="top center",
        # DIAMOND marker to differentiate from Momentum Matrix Circles
        marker=dict(size=res_df['Tension_Val'].clip(30, 100) / 4, color=colors, line=dict(width=1, color='white'), symbol='diamond'),
        hovertemplate="<b>%{text}</b><br>VWAP Dist Z: %{x:.2f}<br>RSI Z: %{y:.2f}<br>Tension: %{customdata:.1f}%<extra></extra>",
        customdata=res_df['Tension_Val']
    ))
    
    fig.update_layout(
        title="Exhaustion Radar (Mean Reversion Zones)",
        xaxis=dict(title="Distance from VWAP (Z-Score)", range=[-4, 4], gridcolor="#222", zerolinecolor="white"),
        yaxis=dict(title="RSI Extremes (Z-Score)", range=[-4, 4], gridcolor="#222", zerolinecolor="white"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=500, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- 5. MAIN DASHBOARD ---
st.title("⚡ Alpha Exhaustion Engine V1.1")
st.caption("Institutional Mean Reversion Quantitative Model | English Edition")

# --- TERMINAL CONFIG (TACTICAL ORANGE) ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #FF9F43; letter-spacing: 2px;'>⚙️ REVERSION CENTER</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    
    watchlist_raw = st.text_area("📡 ACTIVE WATCHLIST (CSV)", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA, AMZN", height=90)
    tf = st.selectbox("⏱️ TIMEFRAME RESOLUTION", ["1h", "4h", "1d"], index=2)
    
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    btn = st.button("EXECUTE EXHAUSTION SCAN", type="primary", use_container_width=True)

if 'rev_results' not in st.session_state: st.session_state['rev_results'] = pd.DataFrame()

if btn:
    results = []
    watchlist = [s.strip().upper() for s in watchlist_raw.split(",") if s.strip()]
    
    with st.spinner("Calculating High-Impact Mean Reversion..."):
        for symbol in watchlist:
            try:
                period = "720d" if tf != '1d' else "10y"
                interval = "60m" if tf != "1d" else "1d"
                hist = fetch_market_data(symbol, period, interval)
                
                if tf == "4h" and not hist.empty:
                    hist = _resample_ohlcv(hist, '4h')
                
                if len(hist) > TF_LOOKBACKS.get(tf, 126) + 20:
                    last_row = calculate_reversion_signals(hist, tf, full_history=False)
                    results.append({
                        "Asset": symbol, "Price": last_row['Close'].values[0],
                        "Tension_Val": last_row['Tension'].values[0], # For plotting
                        "Target Bias": last_row['Bias'].values[0],
                        "VWAP Dist Z": last_row['DistZ'].values[0],
                        "RSI Z": last_row['RSIZ'].values[0]
                    })
            except Exception as e:
                continue

    if results:
        res_df = pd.DataFrame(results).sort_values("Tension_Val", ascending=False)
        st.session_state['rev_results'] = res_df
    else:
        st.warning("Insufficient data.")

if not st.session_state['rev_results'].empty:
    res_df = st.session_state['rev_results']
    
    # --- HTML CARDS (HIGH-IMPACT UI) ---
    top_target = res_df.iloc[0]
    is_short = top_target['Target Bias'] == "SHORT"
    target_color = "#FF5C5C" if is_short else "#00FFAA"
    market_tension = res_df['Tension_Val'].mean()
    
    st.markdown(f"""
    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px;">
        <div style="flex: 1; background-color: #111; padding: 20px; border-radius: 8px; border: 1px solid {target_color}; border-bottom: 4px solid {target_color}; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Top Reversion Target</p>
            <h2 style="color: #EAF2FF; margin: 5px 0 0 0; font-size: 28px;">{top_target['Asset']} <span style="font-size: 16px; color:{target_color}">({top_target['Tension_Val']:.1f}%)</span></h2>
        </div>
        <div style="flex: 1; background-color: #161616; padding: 20px; border-radius: 8px; border: 1px solid #2A2A2A; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Action Required</p>
            <h2 style="color: {target_color}; margin: 5px 0 0 0; font-size: 28px; letter-spacing: 2px;">PREPARE TO {top_target['Target Bias']}</h2>
        </div>
        <div style="flex: 1; background-color: #161616; padding: 20px; border-radius: 8px; border: 1px solid #2A2A2A; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Market Tension Level</p>
            <h2 style="color: #FF9F43; margin: 5px 0 0 0; font-size: 28px;">{market_tension:.1f}% <span style="font-size: 14px; color: #888;">AVG</span></h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- PRO MATRIX DATAFRAME (INSTITUTIONAL STYLE) ---
    st.subheader("Rubber Band Tension Matrix (Exhaustion Scanning)")
    
    # Display dataframe with professional formatting (Progress Bars)
    st.dataframe(
        res_df,
        use_container_width=True,
        height=320,
        column_config={
            "Asset": st.column_config.TextColumn("Asset", width="small"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
            "Tension_Val": st.column_config.ProgressColumn(
                "Rubber Tension",
                format="%.1f%%",
                min_value=0,
                max_value=100,
                width="medium"
                # The progress bar naturally uses the theme color. To create the gradient feel,
                # we sort by Tension_Val, putting the most intense targets at the top.
            ),
            "Target Bias": st.column_config.TextColumn("Target Bias", width="small"),
            "VWAP Dist Z": st.column_config.NumberColumn("VWAP Dist Z", format="%+2.f", width="small"),
            "RSI Z": st.column_config.NumberColumn("RSI Z", format="%+2.f", width="small")
        },
        hide_index=True
    )
    
    st.divider()
    
    # --- SNAPBACK RADAR LEGEND ---
    st.markdown("""
    <div style="padding: 12px 20px; background-color: #161616; border-left: 4px solid #FF9F43; border-radius: 4px; margin-bottom: -15px;">
        <span style="color: #EAF2FF; font-weight: bold; font-size: 16px;">🎯 SNAPBACK RADAR:</span>
        <span style="color: #A0AEC0; font-size: 14px;"> <b>Top Right (Red Diamonds):</b> Overbought SHORT &nbsp;|&nbsp; <b>Bottom Left (Green Diamonds):</b> Oversold LONG &nbsp;|&nbsp; <b>Diamond Size:</b> Market Tension %</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(build_exhaustion_radar(res_df), use_container_width=True, config={'displayModeBar': False})
