import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
st.set_page_config(page_title="Alpha Momentum Matrix V5.1", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid="stExpander"] {
        background-color: #161616;
        border: 1px solid #2A2A2A;
    }
    /* Primary Sidebar Button Styling */
    button[kind="primary"] {
        background-color: #00FFAA !important;
        color: #0F0F0F !important;
        font-weight: 800 !important;
        border: none !important;
        letter-spacing: 1px;
    }
    button[kind="primary"]:hover {
        background-color: #00CC88 !important;
    }
</style>
""", unsafe_allow_html=True)

TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- 2. DATA PIPELINE & CACHING (ANTI-BAN) ---
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

# --- 3. CORE MATHEMATICS (V5.1 CONTINUOUS ENGINE) ---
def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

def calculate_signals_v5_1(df, timeframe, full_history=False):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    ema20 = data['Close'].ewm(span=20, adjust=False).mean()
    ema200 = data['Close'].ewm(span=200, adjust=False).mean()
    
    tr = pd.concat([(data['High'] - data['Low']), 
                    (data['High'] - data['Close'].shift(1)).abs(), 
                    (data['Low'] - data['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr20 = tr.ewm(alpha=1/20, adjust=False).mean()
    
    sqz_on = (data['Close'].rolling(20).std() * 2.0 < 1.5 * atr20)
    
    fired_counter = (~sqz_on).groupby(sqz_on.cumsum()).cumsum()
    sqz_decay = np.where((~sqz_on) & (fired_counter <= 5), (6 - fired_counter) / 5, 0)
    
    mom_raw = (data['Close'] - ema20) / atr20.replace(0, np.nan)
    mom_smooth = mom_raw.ewm(span=5).mean()
    mom_z = _rolling_zscore(mom_smooth, z_win)
    
    acc_raw = mom_z.diff().ewm(span=3, adjust=False).mean()
    acc_z = _rolling_zscore(acc_raw, z_win)
    
    vol_mean = data['Volume'].rolling(20).mean().replace(0, np.nan)
    rvol = (data['Volume'] / vol_mean).replace([np.inf, -np.inf, 0], np.nan)
    rvol_z = _rolling_zscore(np.log(rvol), z_win)

    w_mom, w_acc, w_vol = (0.45, 0.40, 0.15) if timeframe != '1d' else (0.55, 0.30, 0.15)
    
    raw = (w_mom * mom_z.clip(-3, 3) + w_acc * acc_z.clip(-3, 3) + w_vol * rvol_z.clip(-3, 3) * np.sign(mom_z.fillna(0)))
    bias = np.where(sqz_decay > 0, np.sign(mom_z.fillna(0)) * 0.25 * sqz_decay, 0)
    
    slope_z = _rolling_zscore(ema200.diff(), z_win)
    regime_bias = 0.3 * np.tanh(slope_z.fillna(0) / 2.0)
    
    score = 50.0 + 40.0 * np.tanh((raw + bias + regime_bias) / 2.0)
    
    data['Score'] = score.fillna(50.0)
    data['MomZ'] = mom_z.fillna(0)
    data['AccZ'] = acc_z.fillna(0)
    data['RVOL'] = rvol.fillna(1.0)
    data['Squeeze'] = sqz_on
    data['EMA20'] = ema20
    data['EMA200'] = ema200
    
    if full_history:
        return data.dropna()
    else:
        return data.iloc[-1:]

# --- 4. VISUAL ENGINE ---
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
    fig.add_shape(type="rect", x0=0, y0=0, x1=3.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0)
    fig.add_shape(type="rect", x0=-3.5, y0=-3.5, x1=0, y1=0, fillcolor="rgba(255, 92, 92, 0.05)", line_width=0)

    fig.add_trace(go.Scatter(
        x=res_df['MomZ'], y=res_df['AccZ'],
        mode='markers+text', text=res_df['Asset'], textposition="top center",
        marker=dict(size=res_df['RVOL'].clip(1, 3) * 12, color=res_df['Score'],
                    colorscale=[[0, '#FF5C5C'], [0.5, '#444'], [1, '#00FFAA']],
                    line=dict(width=1, color='white'), showscale=True),
        hovertemplate="<b>%{text}</b><br>MomZ: %{x:.2f}<br>AccZ: %{y:.2f}<extra></extra>"
    ))
    fig.update_layout(
        title="Alpha Rotation Radar (Continuous Matrix)",
        xaxis=dict(title="Momentum Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        yaxis=dict(title="Smoothed Accel Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=500, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def build_deep_inspection_chart(symbol, df):
    df_plot = df.tail(200)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])

    # Plot 1: Institutional Candlesticks & EMAs
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'],
        name="Price", increasing_line_color="#00FFAA", decreasing_line_color="#FF5C5C",
        increasing_fillcolor="rgba(0, 255, 170, 0.2)", decreasing_fillcolor="rgba(255, 92, 92, 0.2)"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name="EMA20", line=dict(color="#00FFAA", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA200'], name="EMA200", line=dict(color="#0055FF", width=1.5)), row=1, col=1)

    # Squeeze Background Zones
    sqz_starts = df_plot[df_plot['Squeeze'] & ~df_plot['Squeeze'].shift(1).fillna(False)].index
    sqz_ends = df_plot[~df_plot['Squeeze'] & df_plot['Squeeze'].shift(1).fillna(False)].index
    
    for start in sqz_starts:
        end = sqz_ends[sqz_ends > start]
        end_time = end[0] if len(end) > 0 else df_plot.index[-1]
        for r in [1, 2, 3]:
            fig.add_vrect(x0=start, x1=end_time, fillcolor="rgba(0, 85, 255, 0.1)", line_width=0, row=r, col=1)

    # Plot 2: Momentum & Acceleration
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MomZ'], name="MomZ", line=dict(color="#00FFAA", width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['AccZ'], name="AccZ", line=dict(color="#0055FF", width=1.5, dash='dot')), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1), row=2, col=1)

    # Plot 3: RVOL
    close_delta = df_plot['Close'].diff()
    colors = np.where((df_plot['RVOL'] > 1.2) & (close_delta > 0), "#00FFAA", 
                      np.where((df_plot['RVOL'] > 1.2) & (close_delta < 0), "#FF5C5C", "#444"))
    
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['RVOL'], name="RVOL", marker_color=colors), row=3, col=1)
    fig.add_hline(y=1, line=dict(color="rgba(255,255,255,0.3)", width=1), row=3, col=1)

    fig.update_layout(
        title=f"🛡️ Deep Inspection: {symbol}", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F",
        height=700, showlegend=False, margin=dict(l=20, r=20, t=60, b=20),
        xaxis_rangeslider_visible=False
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

# --- 5. MAIN DASHBOARD (REFINED UI) ---
st.title("🛡️ Alpha Momentum Matrix")
st.caption("Quantitative Engine V5.1 Active | Hedged against Data Leakage & Overfitting")

# --- COMMAND CENTER ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #00FFAA; letter-spacing: 2px;'>⚙️ COMMAND CENTER</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    
    watchlist_raw = st.text_area("📡 ACTIVE WATCHLIST (CSV)", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA, AMZN", height=90)
    tf = st.selectbox("⏱️ TIMEFRAME RESOLUTION", ["1h", "4h", "1d"], index=2)
    
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    btn = st.button("EXECUTE QUANT SCAN", type="primary", use_container_width=True)

if 'results_df' not in st.session_state: st.session_state['results_df'] = pd.DataFrame()

if btn:
    results = []
    watchlist = [s.strip().upper() for s in watchlist_raw.split(",") if s.strip()]
    
    with st.spinner("Processing High-Frequency Matrix..."):
        for symbol in watchlist:
            try:
                period = "720d" if tf != '1d' else "10y"
                interval = "60m" if tf != "1d" else "1d"
                
                hist = fetch_market_data(symbol, period, interval)
                
                if tf == "4h" and not hist.empty:
                    hist = _resample_ohlcv(hist, '4h')
                
                if len(hist) > TF_LOOKBACKS.get(tf, 126) + 20:
                    last_row = calculate_signals_v5_1(hist, tf, full_history=False)
                    results.append({
                        "Asset": symbol, "Price": last_row['Close'].values[0],
                        "Score": last_row['Score'].values[0], "MomZ": last_row['MomZ'].values[0],
                        "AccZ": last_row['AccZ'].values[0], "RVOL": last_row['RVOL'].values[0],
                        "Squeeze": "🔴 ON" if last_row['Squeeze'].values[0] else "🟢 OFF"
                    })
            except Exception as e:
                continue

    if results:
        st.session_state['results_df'] = pd.DataFrame(results).sort_values("Score", ascending=False)
    else:
        st.warning("Insufficient clean data retrieved.")

if not st.session_state['results_df'].empty:
    res_df = st.session_state['results_df']
    
    # --- HIGH-IMPACT MARKET SENTIMENT ---
    top_asset = res_df.iloc[0]
    sentiment_is_bull = res_df['Score'].mean() > 50
    sentiment_text = "BULLISH 🟢" if sentiment_is_bull else "BEARISH 🔴"
    sentiment_color = "#00FFAA" if sentiment_is_bull else "#FF5C5C"
    sqz_count = len(res_df[res_df['Squeeze'] == "🔴 ON"])

    st.markdown(f"""
    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px;">
        <div style="flex: 1; background-color: #161616; padding: 20px; border-radius: 8px; border: 1px solid #2A2A2A; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Top Alpha Pick</p>
            <h2 style="color: #EAF2FF; margin: 5px 0 0 0; font-size: 28px;">{top_asset['Asset']} <span style="color: #00FFAA; font-size: 18px;">({top_asset['Score']:.1f})</span></h2>
        </div>
        <div style="flex: 1; background-color: #111; padding: 20px; border-radius: 8px; border: 1px solid {sentiment_color}; text-align: center; border-bottom: 4px solid {sentiment_color}; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Market Sentiment</p>
            <h2 style="color: {sentiment_color}; margin: 5px 0 0 0; font-size: 28px; letter-spacing: 2px;">{sentiment_text}</h2>
        </div>
        <div style="flex: 1; background-color: #161616; padding: 20px; border-radius: 8px; border: 1px solid #2A2A2A; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Squeeze Alerts</p>
            <h2 style="color: #0055FF; margin: 5px 0 0 0; font-size: 28px;">{sqz_count} <span style="font-size: 14px; color: #888;">ASSETS</span></h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Institutional Confluence Matrix")
    st.dataframe(style_matrix(res_df), use_container_width=True, height=300)
    
    st.divider()
    
    # --- TACTICAL RADAR LEGEND ---
    st.markdown("""
    <div style="padding: 12px 20px; background-color: #161616; border-left: 4px solid #00FFAA; border-radius: 4px; margin-bottom: -15px;">
        <span style="color: #EAF2FF; font-weight: bold; font-size: 16px;">🎯 EDGE RADAR:</span>
        <span style="color: #A0AEC0; font-size: 14px;"> <b>Top Right:</b> Institutional Expansion (Long) &nbsp;|&nbsp; <b>Bottom Left:</b> Capitulation (Short)</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(build_rotation_radar(res_df), use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    
    st.subheader("Asset Deep Inspection")
    target = st.selectbox("Select precise asset to inspect:", res_df['Asset'].tolist())
    
    if target:
        period = "720d" if tf != '1d' else "5y"
        interval = "60m" if tf != "1d" else "1d"
        target_hist = fetch_market_data(target, period, interval)
        
        if tf == "4h" and not target_hist.empty:
            target_hist = _resample_ohlcv(target_hist, '4h')
            
        if len(target_hist) > 200:
            full_sigs = calculate_signals_v5_1(target_hist, tf, full_history=True)
            
            # --- INSTITUTIONAL X-RAY LEGEND ---
            st.markdown("""
            <div style="padding: 12px 20px; background-color: #161616; border-left: 4px solid #0055FF; border-radius: 4px; margin-bottom: -15px;">
                <span style="color: #EAF2FF; font-weight: bold; font-size: 16px;">🔬 INSTITUTIONAL X-RAY:</span>
                <span style="color: #A0AEC0; font-size: 14px;"> <b>Blue Zones:</b> Active Squeeze &nbsp;|&nbsp; <b>Volume Bars (Green/Red):</b> Institutional Injection (>1.2x)</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.plotly_chart(build_deep_inspection_chart(target, full_sigs), use_container_width=True, config={'displayModeBar': False})
