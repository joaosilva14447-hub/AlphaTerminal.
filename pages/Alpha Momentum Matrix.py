import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
st.set_page_config(page_title="Alpha Momentum Matrix", layout="wide")

DISPLAY_ROWS = 10

# Pool for Multiselect (Professional Selection)
TICKER_POOL = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOT-USD", "MATIC-USD",
    "GC=F", "SI=F", "CL=F", "NQ=F", "ES=F", "YM=F",
    "AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "PLTR", "COIN"
]
DEFAULT_WATCHLIST = ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F", "NQ=F", "AAPL"]

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }
    .stDataFrame { background-color: #161616; border-radius: 6px; }

    /* Signal Board HTML/CSS */
    .signal-board {
        margin-top: 12px;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid rgba(76, 125, 255, 0.18);
        background: radial-gradient(circle at top right, rgba(76, 125, 255, 0.16), transparent 28%),
                    linear-gradient(180deg, rgba(19, 24, 33, 0.98), rgba(10, 13, 18, 0.98));
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.28);
    }
    .signal-board-title { color: #EAF2FF; font-size: 1.08rem; font-weight: 700; text-transform: uppercase; }
    .signal-board-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
    .signal-card { padding: 16px 18px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.06); background: linear-gradient(180deg, rgba(24, 29, 38, 0.96), rgba(14, 17, 24, 0.96)); }
    .signal-asset { color: #F7FAFF; font-size: 1.28rem; font-weight: 800; }
    .signal-score-pill { min-width: 70px; padding: 8px 10px; border-radius: 999px; text-align: center; font-weight: 800; color: #F7FAFF; }
    .signal-badge { display: inline-flex; padding: 6px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 700; border: 1px solid transparent; }
    .badge-bull { color: #7CFFD1; background: rgba(0, 255, 170, 0.10); border-color: rgba(0, 255, 170, 0.20); }
    .badge-bear { color: #FFB18B; background: rgba(255, 92, 92, 0.10); border-color: rgba(255, 92, 92, 0.22); }
    .badge-range { color: #C7D0DB; background: rgba(141, 154, 175, 0.12); border-color: rgba(141, 154, 175, 0.22); }
    
    .signal-table { overflow: hidden; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.06); background: rgba(8, 10, 14, 0.65); }
    .signal-table table { width: 100%; border-collapse: collapse; }
    .signal-table thead th { padding: 12px 14px; font-size: 0.74rem; color: #7F8A9E; background: rgba(255, 255, 255, 0.03); text-transform: uppercase; }
    .signal-table td { padding: 14px; color: #EAF2FF; font-size: 0.95rem; }
    .score-shell { position: relative; height: 11px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); }
    .score-fill { height: 100%; border-radius: 999px; }

    /* Sidebar Professional Inputs */
    section[data-testid="stSidebar"] { background: #090D14; }
    section[data-testid="stSidebar"] .radar-shell {
        padding: 20px 18px; border-radius: 22px; border: 1px solid rgba(76, 125, 255, 0.22);
        background: linear-gradient(180deg, rgba(19, 24, 33, 0.98), rgba(10, 13, 18, 0.98));
    }
    span[data-baseweb="tag"] { background-color: rgba(0, 229, 255, 0.12) !important; border: 1px solid rgba(0, 229, 255, 0.3) !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONFIGURATION & UTILS ---
TIMEFRAME_CONFIG = {
    "1h": {"download_interval": "60m", "period": "730d", "resample": None, "z_window": 240, "regime_window": 72, "release_decay_bars": 5, "min_squeeze_bars": 4, "display_bars": 240, "min_history": 320, "weights": {"mom": 0.42, "acc": 0.28, "trend": 0.20, "vol": 0.10}},
    "4h": {"download_interval": "60m", "period": "730d", "resample": "4h", "z_window": 180, "regime_window": 45, "release_decay_bars": 5, "min_squeeze_bars": 3, "display_bars": 220, "min_history": 260, "weights": {"mom": 0.44, "acc": 0.24, "trend": 0.22, "vol": 0.10}},
    "1d": {"download_interval": "1d", "period": "10y", "resample": None, "z_window": 126, "regime_window": 30, "release_decay_bars": 4, "min_squeeze_bars": 3, "display_bars": 240, "min_history": 240, "weights": {"mom": 0.47, "acc": 0.18, "trend": 0.25, "vol": 0.10}},
}

def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _ema(series, length): return series.ewm(span=length, adjust=False, min_periods=length).mean()

def _causal_rolling_zscore(series, window):
    history = series.shift(1)
    mean = history.rolling(window=window).mean()
    std = history.rolling(window=window).std(ddof=0)
    return (series - mean) / std.replace(0.0, np.nan)

def _atr(df, length=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def _resample_ohlcv(df, rule):
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    return df.resample(rule, label="right", closed="right").agg(agg).dropna()

def _score_visuals(score):
    if score >= 70: return "linear-gradient(90deg, #00D68F, #00FFAA)", "rgba(0, 255, 170, 0.18)"
    if score >= 57: return "linear-gradient(90deg, #00B8D9, #00E5FF)", "rgba(0, 229, 255, 0.18)"
    if score <= 30: return "linear-gradient(90deg, #FF6B6B, #FF3B30)", "rgba(255, 92, 92, 0.18)"
    if score <= 43: return "linear-gradient(90deg, #FFB86B, #FF9F43)", "rgba(255, 159, 67, 0.18)"
    return "linear-gradient(90deg, #7A869A, #A0AEC0)", "rgba(160, 174, 192, 0.16)"

def _badge_class(value, col):
    v = str(value).lower()
    if "bull" in v or "long" in v: return "badge-bull"
    if "bear" in v or "short" in v: return "badge-bear"
    return "badge-neutral"

def _setup_label(regime, sqz_on, fired, mom_z, acc_z, rvol, score):
    if sqz_on: return "Compression"
    if regime == "Bull" and score >= 60: return "Bull Expansion"
    if regime == "Bear" and score <= 40: return "Bear Expansion"
    return "Transition"

# --- 3. CORE ANALYTICS ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker, timeframe):
    config = TIMEFRAME_CONFIG[timeframe]
    df = yf.download(ticker, period=config["period"], interval=config["download_interval"], progress=False, auto_adjust=True)
    df = _flatten_columns(df)
    if config["resample"]: df = _resample_ohlcv(df, config["resample"])
    return df.dropna(), None

def calculate_signals(df, timeframe):
    config = TIMEFRAME_CONFIG[timeframe]
    w = config["weights"]
    data = df.copy()
    c, v = data["Close"], data["Volume"].replace(0, np.nan)
    
    ema20, ema50, ema200 = _ema(c, 20), _ema(c, 50), _ema(c, 200)
    atr14, atr20 = _atr(data, 14), _atr(data, 20)
    
    # Squeeze Logic
    bb_std = c.rolling(20).std(ddof=0)
    sqz_on = (c.rolling(20).mean() - 2*bb_std > ema20 - 1.5*atr20) & (c.rolling(20).mean() + 2*bb_std < ema20 + 1.5*atr20)
    sqz_duration = sqz_on.groupby((~sqz_on).cumsum()).cumsum()
    
    # Normalized Momentum
    mom_z = _causal_rolling_zscore(_ema((c - ema20) / atr14, 5), config["z_window"])
    acc_z = _causal_rolling_zscore(_ema(mom_z.diff(), 3), config["z_window"])
    trend_z = _causal_rolling_zscore((ema20 - ema50) / atr20, config["z_window"])
    rvol = v / v.rolling(20).mean()
    rvol_z = _causal_rolling_zscore(np.log(rvol.clip(lower=1e-6)), config["z_window"])
    
    regime = np.where((c > ema200) & (ema50 > ema200), "Bull", np.where((c < ema200) & (ema50 < ema200), "Bear", "Range"))
    
    raw = w["mom"]*mom_z.clip(-3,3) + w["acc"]*acc_z.clip(-3,3) + w["trend"]*trend_z.clip(-3,3) + w["vol"]*rvol_z.clip(-3,3)*np.sign(mom_z.fillna(0))
    score = (50 + 42 * np.tanh(raw / 2.2)).clip(0, 100)
    
    data["SetupScore"], data["MomentumZ"], data["AccelerationZ"], data["TrendZ"] = score, mom_z, acc_z, trend_z
    data["RVOL"], data["Regime"], data["SqueezeOn"], data["SqueezeDuration"] = rvol, regime, sqz_on, sqz_duration
    data["Bias"] = data["SetupScore"].apply(lambda x: "Long" if x > 57 else "Short" if x < 43 else "Neutral")
    data["Setup"] = [_setup_label(r, s, False, mz, az, rv, sc) for r, s, mz, az, rv, sc in zip(data["Regime"], data["SqueezeOn"], data["MomentumZ"], data["AccelerationZ"], data["RVOL"], data["SetupScore"])]
    return data

# --- 4. VISUAL BOARD COMPONENTS ---
def render_signal_board(df):
    records = df.to_dict(orient="records")
    top_cards = []
    for rank, row in enumerate(records[:3], 1):
        fill, glow = _score_visuals(row["Setup Score"])
        top_cards.append(f'<div class="signal-card" style="box-shadow: inset 0 0 0 1px {glow};"><div class="signal-card-top"><div><div class="signal-rank">Top {rank}</div><div class="signal-asset">{row["Asset"]}</div></div><div class="signal-score-pill" style="background:{fill};">{row["Setup Score"]:.1f}</div></div><div class="signal-card-setup">{row["Setup"]}</div><div class="signal-card-meta"><span class="signal-badge {_badge_class(row["Regime"], "Regime")}">{row["Regime"]}</span><span class="signal-badge {_badge_class(row["Bias"], "Bias")}">{row["Bias"]}</span></div></div>')
    
    rows = []
    for rank, row in enumerate(records, 1):
        fill, _ = _score_visuals(row["Setup Score"])
        rows.append(f'<tr><td>{rank:02d}</td><td style="font-weight:800;">{row["Asset"]}</td><td><span class="signal-badge {_badge_class(row["Setup"], "Setup")}">{row["Setup"]}</span></td><td>{row["Regime"]}</td><td style="width:200px;"><div class="score-shell"><div class="score-fill" style="width:{row["Setup Score"]:.1f}%; background:{fill};"></div></div></td><td>{row["Momentum Z"]:+.2f}</td><td>{row["RVOL"]:.2f}x</td></tr>')

    st.markdown(f'<div class="signal-board"><div class="signal-board-grid">{"".join(top_cards)}</div><div class="signal-table"><table><thead><tr><th>#</th><th>Asset</th><th>Setup</th><th>Regime</th><th>Score</th><th>Mom Z</th><th>RVOL</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></div>', unsafe_allow_html=True)

def build_overview_chart(symbol, df):
    df_plot = df.tail(200)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])
    
    # Price Candlesticks
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Price", increasing_line_color="#00FFAA", decreasing_line_color="#FF5C5C"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=_ema(df_plot['Close'], 20), name="EMA20", line=dict(color="#00FFAA", width=1.5)), row=1, col=1)
    
    # Momentum Z
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MomentumZ'], name="Mom Z", line=dict(color="#00FFAA", width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['AccelerationZ'], name="Acc Z", line=dict(color="#4C7DFF", width=1.5, dash='dot')), row=2, col=1)
    
    # RVOL Bars
    colors = np.where(df_plot['RVOL'] > 1.2, "#00FFAA", "#444")
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['RVOL'], name="RVOL", marker_color=colors), row=3, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=800, xaxis_rangeslider_visible=False)
    return fig

# --- 5. MAIN LOGIC & SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="radar-shell"><div class="radar-title">Command Center</div></div>', unsafe_allow_html=True)
    with st.form("alpha_controls"):
        watchlist = st.multiselect("Active Watchlist", options=TICKER_POOL, default=DEFAULT_WATCHLIST)
        custom = st.text_input("Add Custom Ticker").upper().strip()
        if custom and custom not in watchlist: watchlist.append(custom)
        tf = st.radio("Timeframe", ["1h", "4h", "1d"], index=2, horizontal=True)
        btn = st.form_submit_button("RUN QUANT SCAN")

if btn:
    results = []
    with st.spinner("Analyzing Market..."):
        for symbol in watchlist:
            hist, _ = fetch_price_history(symbol, tf)
            if not hist.empty and len(hist) > 200:
                data = calculate_signals(hist, tf).iloc[-1]
                results.append({"Asset": symbol, "Setup Score": data["SetupScore"], "Regime": data["Regime"], "Bias": data["Bias"], "Setup": data["Setup"], "Momentum Z": data["MomentumZ"], "Acceleration Z": data["AccelerationZ"], "RVOL": data["RVOL"], "Squeeze": "ON" if data["SqueezeOn"] else "OFF", "Squeeze Bars": data["SqueezeDuration"]})
    
    if results:
        res_df = pd.DataFrame(results).sort_values("Setup Score", ascending=False)
        st.session_state["results_df"] = res_df
        st.session_state["watchlist"] = watchlist

if "results_df" in st.session_state:
    res_df = st.session_state["results_df"]
    
    # Display Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Top Alpha", res_df.iloc[0]["Asset"], f"{res_df.iloc[0]['Setup Score']:.1f}")
    c2.metric("Market Sentiment", "BULLISH" if res_df["Setup Score"].mean() > 50 else "BEARISH")
    c3.metric("Squeeze Alerts", int((res_df["Squeeze"] == "ON").sum()))
    
    render_signal_board(res_df.head(DISPLAY_ROWS))
    
    # Radar Scatter
    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatter(x=res_df["Momentum Z"], y=res_df["Acceleration Z"], mode="markers+text", text=res_df["Asset"], marker=dict(size=res_df["RVOL"]*15, color=res_df["Setup Score"], colorscale='Viridis', showscale=True)))
    fig_radar.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", height=500, title="Rotation Radar")
    st.plotly_chart(fig_radar, use_container_width=True)
    
    # DEEP INSPECTION (The Bottom Chart)
    st.divider()
    target = st.selectbox("Inspect Asset Detail", res_df["Asset"].tolist())
    if target:
        hist_detail, _ = fetch_price_history(target, tf)
        if not hist_detail.empty:
            full_data = calculate_signals(hist_detail, tf)
            st.plotly_chart(build_overview_chart(target, full_data), use_container_width=True)
