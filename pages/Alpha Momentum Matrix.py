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

# Pool de ativos para seleção rápida (Podes expandir esta lista conforme necessário)
TICKER_POOL = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOT-USD", "MATIC-USD",
    "GC=F", "SI=F", "CL=F", "NQ=F", "ES=F", "YM=F",
    "AAPL", "TSLA", "NVDA", "AMD", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "PLTR", "COIN"
]

# Watchlist Inicial (Igual à da imagem/configuração anterior)
INITIAL_WATCHLIST = ["BTC-USD", "ETH-USD", "SOL-USD", "GC=F", "NQ=F", "AAPL", "TSLA", "NVDA"]

st.markdown(
    """
<style>
    .main { background-color: #0F0F0F; }

    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }

    .stDataFrame { background-color: #161616; border-radius: 6px; }

    /* Custom Signal Board CSS */
    .signal-board {
        margin-top: 12px;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid rgba(76, 125, 255, 0.18);
        background:
            radial-gradient(circle at top right, rgba(76, 125, 255, 0.16), transparent 28%),
            linear-gradient(180deg, rgba(19, 24, 33, 0.98), rgba(10, 13, 18, 0.98));
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.28);
    }

    .signal-board-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 18px;
    }

    .signal-board-title {
        color: #EAF2FF;
        font-size: 1.08rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .signal-board-subtitle {
        color: #8D9AAF;
        font-size: 0.86rem;
    }

    .signal-board-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin-bottom: 18px;
    }

    .signal-card {
        padding: 16px 18px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        background: linear-gradient(180deg, rgba(24, 29, 38, 0.96), rgba(14, 17, 24, 0.96));
    }

    .signal-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 10px;
    }

    .signal-rank { color: #6E7B91; font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; }
    .signal-asset { color: #F7FAFF; font-size: 1.28rem; font-weight: 800; line-height: 1.1; }

    .signal-score-pill {
        min-width: 70px;
        padding: 8px 10px;
        border-radius: 999px;
        text-align: center;
        font-weight: 800;
        font-size: 0.98rem;
        color: #F7FAFF;
    }

    .signal-card-setup { margin-bottom: 12px; color: #D8E2F2; font-size: 0.95rem; font-weight: 600; }

    .signal-card-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }

    .signal-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        border: 1px solid transparent;
    }

    .badge-bull { color: #7CFFD1; background: rgba(0, 255, 170, 0.10); border-color: rgba(0, 255, 170, 0.20); }
    .badge-bear { color: #FFB18B; background: rgba(255, 92, 92, 0.10); border-color: rgba(255, 92, 92, 0.22); }
    .badge-range { color: #C7D0DB; background: rgba(141, 154, 175, 0.12); border-color: rgba(141, 154, 175, 0.22); }
    .badge-compression { color: #A9BCFF; background: rgba(76, 125, 255, 0.12); border-color: rgba(76, 125, 255, 0.26); }
    .badge-neutral { color: #D5DEEB; background: rgba(199, 208, 219, 0.10); border-color: rgba(199, 208, 219, 0.16); }

    .signal-card-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .signal-stat-label { color: #7F8A9E; font-size: 0.70rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px; }
    .signal-stat-value { color: #F3F7FD; font-size: 0.98rem; font-weight: 700; }

    .signal-table { overflow: hidden; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.06); background: rgba(8, 10, 14, 0.65); }
    .signal-table table { width: 100%; border-collapse: collapse; }
    .signal-table thead th {
        padding: 12px 14px;
        text-align: left;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        color: #7F8A9E;
        background: rgba(255, 255, 255, 0.03);
    }
    .signal-table tbody tr { border-top: 1px solid rgba(255, 255, 255, 0.05); }
    .signal-table tbody tr:hover { background: rgba(76, 125, 255, 0.08); }
    .signal-table td { padding: 14px; color: #EAF2FF; font-size: 0.95rem; vertical-align: middle; }

    .rank-cell { color: #6E7B91; font-weight: 700; width: 48px; }
    .asset-cell { font-weight: 800; font-size: 1.02rem; letter-spacing: 0.02em; }
    .score-cell { min-width: 190px; }
    .score-shell { position: relative; height: 11px; border-radius: 999px; overflow: hidden; background: rgba(255, 255, 255, 0.08); margin-bottom: 8px; }
    .score-fill { height: 100%; border-radius: 999px; }
    .score-text { font-size: 0.90rem; font-weight: 700; color: #F7FAFF; }

    .metric-pos { color: #7CFFD1; font-weight: 700; }
    .metric-neg { color: #FFB18B; font-weight: 700; }
    .metric-flat { color: #D5DEEB; font-weight: 700; }

    section[data-testid="stSidebar"] { background: #090D14; }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background:
            radial-gradient(circle at top right, rgba(76, 125, 255, 0.12), transparent 26%),
            linear-gradient(180deg, #0B1018 0%, #090D14 100%);
        padding: 26px 18px 28px;
    }

    section[data-testid="stSidebar"] .radar-shell {
        padding: 20px 18px 18px;
        border-radius: 22px;
        border: 1px solid rgba(76, 125, 255, 0.22);
        background:
            radial-gradient(circle at top right, rgba(76, 125, 255, 0.16), transparent 28%),
            linear-gradient(180deg, rgba(19, 24, 33, 0.98), rgba(10, 13, 18, 0.98));
        box-shadow: 0 22px 48px rgba(0, 0, 0, 0.34);
        margin-bottom: 14px;
    }

    section[data-testid="stSidebar"] .radar-kicker {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 6px 12px;
        border-radius: 999px;
        background: rgba(17, 24, 39, 0.95);
        border: 1px solid rgba(141, 154, 175, 0.16);
        color: #9FB0C8;
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 16px;
    }

    section[data-testid="stSidebar"] .radar-title { color: #F5F9FF; font-size: 1.52rem; font-weight: 800; line-height: 1.08; margin-bottom: 8px; }
    section[data-testid="stSidebar"] .radar-subtitle { color: #8190A7; font-size: 0.88rem; line-height: 1.5; margin-bottom: 8px; }
    section[data-testid="stSidebar"] .radar-field-label { color: #A7B4C6; font-size: 0.70rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; margin-top: 14px; margin-bottom: 8px; }

    /* Estilização Profissional do Multiselect (Chips) */
    span[data-baseweb="tag"] {
        background-color: rgba(0, 229, 255, 0.12) !important;
        border: 1px solid rgba(0, 229, 255, 0.3) !important;
        border-radius: 999px !important;
    }
    span[data-baseweb="tag"] span { color: #EAF2FF !important; font-weight: 700 !important; }

    section[data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button {
        width: 100%;
        margin-top: 18px;
        min-height: 52px;
        border-radius: 18px;
        border: none;
        background: linear-gradient(90deg, #00D68F, #00A3FF);
        color: #06131C;
        font-size: 1rem;
        font-weight: 900;
        letter-spacing: 0.02em;
        box-shadow: 0 18px 32px rgba(0, 0, 0, 0.26);
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<h1 style='text-align:center; color:#EAF2FF;'>Alpha Momentum Matrix</h1>", unsafe_allow_html=True)

# --- 2. CONFIGURATION & UTILS (MANTIDOS) ---
TIMEFRAME_CONFIG = {
    "1h": {"download_interval": "60m", "period": "730d", "resample": None, "z_window": 240, "regime_window": 72, "release_decay_bars": 5, "min_squeeze_bars": 4, "display_bars": 240, "min_history": 320, "weights": {"mom": 0.42, "acc": 0.28, "trend": 0.20, "vol": 0.10}},
    "4h": {"download_interval": "60m", "period": "730d", "resample": "4h", "z_window": 180, "regime_window": 45, "release_decay_bars": 5, "min_squeeze_bars": 3, "display_bars": 220, "min_history": 260, "weights": {"mom": 0.44, "acc": 0.24, "trend": 0.22, "vol": 0.10}},
    "1d": {"download_interval": "1d", "period": "10y", "resample": None, "z_window": 126, "regime_window": 30, "release_decay_bars": 4, "min_squeeze_bars": 3, "display_bars": 240, "min_history": 240, "weights": {"mom": 0.47, "acc": 0.18, "trend": 0.25, "vol": 0.10}},
}

def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df

def _normalize_index(index):
    normalized = pd.to_datetime(index)
    if getattr(normalized, "tz", None) is not None: normalized = normalized.tz_convert(None)
    return normalized

def _ema(series, length): return series.ewm(span=length, adjust=False, min_periods=length).mean()

def _causal_rolling_zscore(series, window):
    history = series.shift(1)
    mean = history.rolling(window=window, min_periods=window).mean()
    std = history.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)

def _atr(df, length=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()

def _resample_ohlcv(df, rule):
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    return df.resample(rule, label="right", closed="right").agg(agg).dropna()

def _bias_label(score):
    if score >= 70: return "Strong Long"
    if score >= 57: return "Long"
    if score <= 30: return "Strong Short"
    if score <= 43: return "Short"
    return "Neutral"

def _score_visuals(score):
    if score >= 70: return "linear-gradient(90deg, #00D68F, #00FFAA)", "rgba(0, 255, 170, 0.18)"
    if score >= 57: return "linear-gradient(90deg, #00B8D9, #00E5FF)", "rgba(0, 229, 255, 0.18)"
    if score <= 30: return "linear-gradient(90deg, #FF6B6B, #FF3B30)", "rgba(255, 92, 92, 0.18)"
    if score <= 43: return "linear-gradient(90deg, #FFB86B, #FF9F43)", "rgba(255, 159, 67, 0.18)"
    return "linear-gradient(90deg, #7A869A, #A0AEC0)", "rgba(160, 174, 192, 0.16)"

def _badge_class(value, column):
    v = value.lower()
    if column == "Regime":
        if v == "bull": return "badge-bull"
        if v == "bear": return "badge-bear"
        return "badge-range"
    if "compression" in v: return "badge-compression"
    if "bull" in v or "long" in v: return "badge-bull"
    if "bear" in v or "short" in v: return "badge-bear"
    return "badge-neutral"

def _metric_class(v, pos, neg):
    if v >= pos: return "metric-pos"
    if v <= neg: return "metric-neg"
    return "metric-flat"

def _setup_label(regime, sqz_on, sqz_fired, mom_z, acc_z, rvol, score):
    if sqz_on: return "Compression"
    if regime == "Bull" and score >= 60 and mom_z > 0.35 and acc_z > -0.1: return "Bull Expansion"
    if regime == "Bear" and score <= 40 and mom_z < -0.35 and acc_z < 0.1: return "Bear Expansion"
    if sqz_fired: return "Bull Release" if mom_z > 0 else "Bear Release"
    if abs(mom_z) < 0.35 and abs(acc_z) < 0.35 and 0.9 <= rvol <= 1.15: return "Neutral"
    return "Transition"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker, timeframe):
    config = TIMEFRAME_CONFIG[timeframe]
    try:
        df = yf.download(ticker, period=config["period"], interval=config["download_interval"], progress=False, auto_adjust=True, threads=False)
        df = _flatten_columns(df)
        if df.empty or any(c not in df.columns for c in ["Open", "High", "Low", "Close", "Volume"]): return pd.DataFrame(), "error"
        df.index = _normalize_index(df.index)
        if config["resample"]: df = _resample_ohlcv(df, config["resample"])
        return df.dropna(), None
    except: return pd.DataFrame(), "failed"

def calculate_signals(df, timeframe):
    config = TIMEFRAME_CONFIG[timeframe]
    w = config["weights"]
    data = df.copy()
    c, v = data["Close"], data["Volume"].replace(0, np.nan)
    
    ema20, ema50, ema200 = _ema(c, 20), _ema(c, 50), _ema(c, 200)
    atr14, atr20 = _atr(data, 14), _atr(data, 20)
    
    # Squeeze
    bb_std = c.rolling(20).std(ddof=0)
    sqz_on = (c.rolling(20).mean() - 2*bb_std > ema20 - 1.5*atr20) & (c.rolling(20).mean() + 2*bb_std < ema20 + 1.5*atr20)
    sqz_duration = sqz_on.groupby((~sqz_on).cumsum()).cumsum()
    sqz_fired = (~sqz_on) & sqz_on.shift(1).fillna(False)
    
    # Momentum & Z-Scores
    mom_z = _causal_rolling_zscore(_ema((c - ema20) / atr14, 5), config["z_window"])
    acc_z = _causal_rolling_zscore(_ema(mom_z.diff(), 3), config["z_window"])
    trend_z = _causal_rolling_zscore((ema20 - ema50) / atr20, config["z_window"])
    rvol = v / v.rolling(20).mean()
    rvol_z = _causal_rolling_zscore(np.log(rvol.clip(lower=1e-6)), config["z_window"])
    
    regime = np.where((c > ema200) & (ema50 > ema200), "Bull", np.where((c < ema200) & (ema50 < ema200), "Bear", "Range"))
    
    raw = w["mom"]*mom_z.clip(-3,3) + w["acc"]*acc_z.clip(-3,3) + w["trend"]*trend_z.clip(-3,3) + w["vol"]*rvol_z.clip(-3,3)*np.sign(mom_z.fillna(0))
    score = (50 + 42 * np.tanh(raw / 2.2)).clip(0, 100)
    
    data["SetupScore"] = score
    data["MomentumZ"], data["AccelerationZ"], data["TrendZ"] = mom_z, acc_z, trend_z
    data["RVOL"], data["Regime"], data["SqueezeOn"], data["SqueezeDuration"] = rvol, regime, sqz_on, sqz_duration
    data["Bias"] = data["SetupScore"].apply(_bias_label)
    data["SqueezeFired"] = sqz_fired
    data["EMA20"], data["EMA50"], data["EMA200"] = ema20, ema50, ema200
    
    data["Setup"] = [_setup_label(r, s, f, mz, az, rv, sc) for r, s, f, mz, az, rv, sc in zip(data["Regime"], data["SqueezeOn"], data["SqueezeFired"], data["MomentumZ"].fillna(0), data["AccelerationZ"].fillna(0), data["RVOL"].fillna(0), data["SetupScore"].fillna(50))]
    return data.dropna()

# --- 3. DASHBOARD COMPONENTS (MANTIDOS) ---
def render_signal_board(df):
    records = df.to_dict(orient="records")
    top_cards = []
    for rank, row in enumerate(records[:3], 1):
        fill, glow = _score_visuals(row["Setup Score"])
        top_cards.append(f'<div class="signal-card" style="box-shadow: inset 0 0 0 1px {glow};"><div class="signal-card-top"><div><div class="signal-rank">Top {rank}</div><div class="signal-asset">{row["Asset"]}</div></div><div class="signal-score-pill" style="background:{fill};">{row["Setup Score"]:.1f}</div></div><div class="signal-card-setup">{row["Setup"]}</div><div class="signal-card-meta"><span class="signal-badge {_badge_class(row["Regime"], "Regime")}">{row["Regime"]}</span><span class="signal-badge {_badge_class(row["Bias"], "Bias")}">{row["Bias"]}</span><span class="signal-badge badge-compression">Squeeze {row["Squeeze"]}</span></div><div class="signal-card-stats"><div><div class="signal-stat-label">Mom Z</div><div class="signal-stat-value">{row["Momentum Z"]:+.2f}</div></div><div><div class="signal-stat-label">Accel</div><div class="signal-stat-value">{row["Acceleration Z"]:+.2f}</div></div><div><div class="signal-stat-label">Trend Z</div><div class="signal-stat-value">{row["Trend Z"]:+.2f}</div></div><div><div class="signal-stat-label">RVOL</div><div class="signal-stat-value">{row["RVOL"]:.2f}x</div></div></div></div>')
    
    table_rows = []
    for rank, row in enumerate(records, 1):
        fill, _ = _score_visuals(row["Setup Score"])
        table_rows.append(f'<tr><td class="rank-cell">{rank:02d}</td><td class="asset-cell">{row["Asset"]}</td><td><span class="signal-badge {_badge_class(row["Setup"], "Setup")}">{row["Setup"]}</span></td><td><span class="signal-badge {_badge_class(row["Bias"], "Bias")}">{row["Bias"]}</span></td><td><span class="signal-badge {_badge_class(row["Regime"], "Regime")}">{row["Regime"]}</span></td><td class="score-cell"><div class="score-shell"><div class="score-fill" style="width:{row["Setup Score"]:.1f}%; background:{fill};"></div></div><div class="score-text">{row["Setup Score"]:.1f}/100</div></td><td class="{_metric_class(row["Momentum Z"], 0.35, -0.35)}">{row["Momentum Z"]:+.2f}</td><td class="{_metric_class(row["Acceleration Z"], 0.1, -0.1)}">{row["Acceleration Z"]:+.2f}</td><td class="{_metric_class(row["Trend Z"], 0.2, -0.2)}">{row["Trend Z"]:+.2f}</td><td>{row["RVOL"]:.2f}x</td><td>{int(row["Squeeze Bars"])}</td></tr>')

    st.markdown(f'<div class="signal-board"><div class="signal-board-header"><div><div class="signal-board-title">Signal Board</div><div class="signal-board-subtitle">Institutional Alpha Tracking Matrix</div></div></div><div class="signal-board-grid">{"".join(top_cards)}</div><div class="signal-table"><table><thead><tr><th>#</th><th>Asset</th><th>Setup</th><th>Bias</th><th>Regime</th><th>Score</th><th>Mom Z</th><th>Accel</th><th>Trend</th><th>RVOL</th><th>SQZ</th></tr></thead><tbody>{"".join(table_rows)}</tbody></table></div></div>', unsafe_allow_html=True)

# --- 4. SIDEBAR COMMAND CENTER (NOVA WATCHLIST) ---
with st.sidebar:
    st.markdown('<div class="radar-shell"><div class="radar-kicker">Control Node</div><div class="radar-title">Radar Controls</div><div class="radar-subtitle">Manage your institutional watchlist and timeframe.</div></div>', unsafe_allow_html=True)

    with st.form("alpha_momentum_controls"):
        st.markdown('<div class="radar-field-label">Watchlist Selection</div>', unsafe_allow_html=True)
        
        # Substituição do Text Area pelo Multiselect (Igual à imagem)
        watchlist = st.multiselect(
            "Select Tickers",
            options=TICKER_POOL,
            default=INITIAL_WATCHLIST,
            label_visibility="collapsed"
        )
        
        # Opção para adicionar um ticker customizado não presente na lista
        custom_ticker = st.text_input("Add Custom Ticker (e.g. NVDA, TSLA)", "").upper().strip()
        if custom_ticker and custom_ticker not in watchlist:
            watchlist.append(custom_ticker)

        st.markdown('<div class="radar-field-label">Timeframe</div>', unsafe_allow_html=True)
        tf = st.radio("Timeframe", ["1h", "4h", "1d"], horizontal=True, index=2, label_visibility="collapsed")

        btn = st.form_submit_button("Analyze Market")

# --- 5. EXECUTION ENGINE ---
if btn:
    results = []
    with st.spinner("Executing High-Frequency Analysis..."):
        for symbol in watchlist:
            hist, _ = fetch_price_history(symbol, tf)
            if not hist.empty and len(hist) > 200:
                data = calculate_signals(hist, tf).iloc[-1]
                results.append({
                    "Asset": symbol, "Price": data["Close"], "Regime": data["Regime"], "Bias": data["Bias"],
                    "Setup": data["Setup"], "Setup Score": data["SetupScore"], "Squeeze": "ON" if data["SqueezeOn"] else "OFF",
                    "Squeeze Bars": data["SqueezeDuration"], "Momentum Z": data["MomentumZ"], "Acceleration Z": data["AccelerationZ"],
                    "Trend Z": data["TrendZ"], "RVOL": data["RVOL"]
                })
    
    if results:
        res_df = pd.DataFrame(results).sort_values("Setup Score", ascending=False)
        render_signal_board(res_df.head(DISPLAY_ROWS))
        
        # Scatter Radar
        fig = go.Figure()
        fig.add_shape(type="rect", x0=0, y0=0, x1=3.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0)
        fig.add_shape(type="rect", x0=-3.5, y0=-3.5, x1=0, y1=0, fillcolor="rgba(255, 92, 92, 0.05)", line_width=0)
        fig.add_trace(go.Scatter(x=res_df["Momentum Z"], y=res_df["Acceleration Z"], mode="markers+text", text=res_df["Asset"], textposition="top center", marker=dict(size=res_df["RVOL"].clip(0.6, 3)*15, color=res_df["Setup Score"], colorscale='Viridis', showscale=True)))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=550, title="Rotation Radar")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data found for the selected assets.")
