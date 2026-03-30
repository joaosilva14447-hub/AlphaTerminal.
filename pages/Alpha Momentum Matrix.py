import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


st.set_page_config(page_title="Alpha Momentum Matrix", layout="wide")

DISPLAY_ROWS = 10

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

    .signal-rank {
        color: #6E7B91;
        font-size: 0.78rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .signal-asset {
        color: #F7FAFF;
        font-size: 1.28rem;
        font-weight: 800;
        line-height: 1.1;
    }

    .signal-score-pill {
        min-width: 70px;
        padding: 8px 10px;
        border-radius: 999px;
        text-align: center;
        font-weight: 800;
        font-size: 0.98rem;
        color: #F7FAFF;
    }

    .signal-card-setup {
        margin-bottom: 12px;
        color: #D8E2F2;
        font-size: 0.95rem;
        font-weight: 600;
    }

    .signal-card-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
    }

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

    .badge-bull {
        color: #7CFFD1;
        background: rgba(0, 255, 170, 0.10);
        border-color: rgba(0, 255, 170, 0.20);
    }

    .badge-bear {
        color: #FFB18B;
        background: rgba(255, 92, 92, 0.10);
        border-color: rgba(255, 92, 92, 0.22);
    }

    .badge-range {
        color: #C7D0DB;
        background: rgba(141, 154, 175, 0.12);
        border-color: rgba(141, 154, 175, 0.22);
    }

    .badge-compression {
        color: #A9BCFF;
        background: rgba(76, 125, 255, 0.12);
        border-color: rgba(76, 125, 255, 0.26);
    }

    .badge-neutral {
        color: #D5DEEB;
        background: rgba(199, 208, 219, 0.10);
        border-color: rgba(199, 208, 219, 0.16);
    }

    .signal-card-stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
    }

    .signal-stat-label {
        color: #7F8A9E;
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }

    .signal-stat-value {
        color: #F3F7FD;
        font-size: 0.98rem;
        font-weight: 700;
    }

    .signal-table {
        overflow: hidden;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        background: rgba(8, 10, 14, 0.65);
    }

    .signal-table table {
        width: 100%;
        border-collapse: collapse;
    }

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

    .signal-table tbody tr {
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }

    .signal-table tbody tr:nth-child(odd) {
        background: rgba(255, 255, 255, 0.015);
    }

    .signal-table tbody tr:hover {
        background: rgba(76, 125, 255, 0.08);
    }

    .signal-table td {
        padding: 14px;
        color: #EAF2FF;
        font-size: 0.95rem;
        vertical-align: middle;
    }

    .rank-cell {
        color: #6E7B91;
        font-weight: 700;
        width: 48px;
    }

    .asset-cell {
        font-weight: 800;
        font-size: 1.02rem;
        letter-spacing: 0.02em;
    }

    .score-cell {
        min-width: 190px;
    }

    .score-shell {
        position: relative;
        height: 11px;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.08);
        margin-bottom: 8px;
    }

    .score-fill {
        height: 100%;
        border-radius: 999px;
    }

    .score-text {
        font-size: 0.90rem;
        font-weight: 700;
        color: #F7FAFF;
    }

    .metric-pos { color: #7CFFD1; font-weight: 700; }
    .metric-neg { color: #FFB18B; font-weight: 700; }
    .metric-flat { color: #D5DEEB; font-weight: 700; }

    section[data-testid="stSidebar"] {
        background: #090D14;
    }

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

    section[data-testid="stSidebar"] .radar-title {
        color: #F5F9FF;
        font-size: 1.52rem;
        font-weight: 800;
        line-height: 1.08;
        margin-bottom: 8px;
    }

    section[data-testid="stSidebar"] .radar-subtitle {
        color: #8190A7;
        font-size: 0.88rem;
        line-height: 1.5;
        margin-bottom: 8px;
    }

    section[data-testid="stSidebar"] .radar-field-label {
        color: #A7B4C6;
        font-size: 0.70rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-top: 14px;
        margin-bottom: 8px;
    }

    section[data-testid="stSidebar"] .watchlist-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }

    section[data-testid="stSidebar"] .watchlist-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    section[data-testid="stSidebar"] .watchlist-preview {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
        margin-bottom: 4px;
    }

    section[data-testid="stSidebar"] .watchlist-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(28, 37, 54, 0.95);
        border: 1px solid rgba(141, 154, 175, 0.16);
        color: #C8D2E0;
        font-size: 0.75rem;
        font-weight: 700;
    }

    section[data-testid="stSidebar"] .display-note {
        margin-top: 10px;
        padding: 12px 14px;
        border-radius: 16px;
        background: rgba(13, 18, 27, 0.92);
        border: 1px solid rgba(30, 42, 61, 0.96);
        color: #8EA0B7;
        font-size: 0.80rem;
        line-height: 1.45;
    }

    section[data-testid="stSidebar"] [data-testid="stTextArea"] textarea {
        min-height: 132px !important;
        border-radius: 18px !important;
        background: #0C1119 !important;
        border: 1px solid #1F2B3D !important;
        color: #EAF2FF !important;
        font-family: Consolas, "SFMono-Regular", Menlo, monospace !important;
        font-size: 0.95rem !important;
        line-height: 1.55 !important;
        padding-top: 16px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stTextArea"] textarea:focus {
        border-color: rgba(0, 229, 255, 0.48) !important;
        box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.18) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] {
        margin-top: 2px;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex;
        gap: 10px;
        padding: 8px;
        border-radius: 20px;
        border: 1px solid #1E2A3D;
        background: #0D121B;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        flex: 1 1 0;
        margin: 0 !important;
        padding: 10px 0 !important;
        border-radius: 16px;
        background: #111927;
        border: 1px solid transparent;
        justify-content: center;
        transition: 0.2s ease;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #9FB0C8 !important;
        font-size: 0.96rem !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: rgba(0, 214, 143, 0.14);
        border-color: rgba(0, 229, 255, 0.42);
        box-shadow: inset 0 0 0 1px rgba(76, 125, 255, 0.10);
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #F5F9FF !important;
    }

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

    section[data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button:hover {
        filter: brightness(1.04);
    }

    @media (max-width: 1100px) {
        .signal-board-grid { grid-template-columns: 1fr; }
        .signal-card-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .signal-table { overflow-x: auto; }
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Alpha Momentum Matrix</h1>",
    unsafe_allow_html=True,
)
st.caption(
    "Cross-asset squeeze and expansion radar with causal normalization, volatility-scaled momentum, "
    "relative volume confirmation, and a stricter structural regime engine."
)

TIMEFRAME_CONFIG = {
    "1h": {
        "download_interval": "60m",
        "period": "720d", # FIX: Changed from 730d to prevent strict-limit YFinance empty fetches
        "resample": None,
        "z_window": 240,
        "regime_window": 72,
        "release_decay_bars": 5,
        "min_squeeze_bars": 4,
        "display_bars": 240,
        "min_history": 320,
        "weights": {"mom": 0.42, "acc": 0.28, "trend": 0.20, "vol": 0.10},
    },
    "4h": {
        "download_interval": "60m",
        "period": "720d", # FIX: Changed from 730d to prevent strict-limit YFinance empty fetches
        "resample": "4h",
        "z_window": 180,
        "regime_window": 45,
        "release_decay_bars": 5,
        "min_squeeze_bars": 3,
        "display_bars": 220,
        "min_history": 260,
        "weights": {"mom": 0.44, "acc": 0.24, "trend": 0.22, "vol": 0.10},
    },
    "1d": {
        "download_interval": "1d",
        "period": "10y",
        "resample": None,
        "z_window": 126,
        "regime_window": 30,
        "release_decay_bars": 4,
        "min_squeeze_bars": 3,
        "display_bars": 240,
        "min_history": 240,
        "weights": {"mom": 0.47, "acc": 0.18, "trend": 0.25, "vol": 0.10},
    },
}

DEFAULT_WATCHLIST = "BTC-USD, ETH-USD, SOL-USD, SUI-USD, NQ=F, TRX-USD"


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _normalize_index(index: pd.Index) -> pd.DatetimeIndex:
    normalized = pd.to_datetime(index)
    if getattr(normalized, "tz", None) is not None:
        normalized = normalized.tz_convert(None)
    return normalized


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def _causal_rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    history = series.shift(1)
    mean = history.rolling(window=window, min_periods=window).mean()
    std = history.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    out = df.resample(rule, label="right", closed="right").agg(agg)
    return out.dropna(subset=["Open", "High", "Low", "Close"])


def _clean_watchlist(raw_text: str) -> list[str]:
    seen: set[str] = set()
    tickers: list[str] = []
    for item in raw_text.split(","):
        symbol = item.strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        tickers.append(symbol)
    return tickers


def _squeeze_ranges(index: pd.Index, mask: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    ranges: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    active_start: pd.Timestamp | None = None
    active_end: pd.Timestamp | None = None

    for ts, active in zip(index, mask.fillna(False).tolist()):
        if active and active_start is None:
            active_start = ts
        if active:
            active_end = ts
        elif active_start is not None and active_end is not None:
            ranges.append((active_start, active_end))
            active_start = None
            active_end = None

    if active_start is not None and active_end is not None:
        ranges.append((active_start, active_end))

    return ranges


def _bias_label(score: float) -> str:
    if score >= 70:
        return "Strong Long"
    if score >= 57:
        return "Long"
    if score <= 30:
        return "Strong Short"
    if score <= 43:
        return "Short"
    return "Neutral"


def _score_visuals(score: float) -> tuple[str, str]:
    if score >= 70:
        return "linear-gradient(90deg, #00D68F, #00FFAA)", "rgba(0, 255, 170, 0.18)"
    if score >= 57:
        return "linear-gradient(90deg, #00B8D9, #00E5FF)", "rgba(0, 229, 255, 0.18)"
    if score <= 30:
        return "linear-gradient(90deg, #FF6B6B, #FF3B30)", "rgba(255, 92, 92, 0.18)"
    if score <= 43:
        return "linear-gradient(90deg, #FFB86B, #FF9F43)", "rgba(255, 159, 67, 0.18)"
    return "linear-gradient(90deg, #7A869A, #A0AEC0)", "rgba(160, 174, 192, 0.16)"


def _badge_class(value: str, column: str) -> str:
    value_lower = value.lower()
    if column == "Regime":
        if value_lower == "bull":
            return "badge-bull"
        if value_lower == "bear":
            return "badge-bear"
        return "badge-range"
    if "compression" in value_lower:
        return "badge-compression"
    if "bull" in value_lower or "long" in value_lower:
        return "badge-bull"
    if "bear" in value_lower or "short" in value_lower:
        return "badge-bear"
    return "badge-neutral"


def _metric_class(value: float, positive_threshold: float, negative_threshold: float) -> str:
    if value >= positive_threshold:
        return "metric-pos"
    if value <= negative_threshold:
        return "metric-neg"
    return "metric-flat"


def _regime_symbol(value: str) -> str:
    return {"Bull": "diamond", "Bear": "x", "Range": "circle"}.get(value, "circle")


def _setup_label(
    regime: str,
    squeeze_on: bool,
    squeeze_fired: bool,
    momentum_z: float,
    accel_z: float,
    rvol: float,
    score: float,
) -> str:
    if squeeze_on:
        return "Compression"
    if regime == "Bull" and score >= 60 and momentum_z > 0.35 and accel_z > -0.1:
        return "Bull Expansion"
    if regime == "Bear" and score <= 40 and momentum_z < -0.35 and accel_z < 0.1:
        return "Bear Expansion"
    if squeeze_fired and momentum_z > 0:
        return "Bull Release"
    if squeeze_fired and momentum_z < 0:
        return "Bear Release"
    if abs(momentum_z) < 0.35 and abs(accel_z) < 0.35 and 0.9 <= rvol <= 1.15:
        return "Neutral"
    return "Transition"


def _data_health_label(volume_quality: float, bars: int, min_history: int) -> str:
    if bars < min_history:
        return "Thin"
    if volume_quality < 0.35:
        return "Sparse"
    if volume_quality < 0.75:
        return "Mixed"
    return "Healthy"


def _ensure_results_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    normalized = df.copy()
    defaults: dict[str, object] = {
        "Asset": "",
        "Price": np.nan,
        "Regime": "Range",
        "Bias": "Neutral",
        "Setup": "Transition",
        "Setup Score": 50.0,
        "Confidence": 0.50,
        "Squeeze": "OFF",
        "Squeeze Bars": 0,
        "Momentum Z": 0.0,
        "Acceleration Z": 0.0,
        "Trend Z": 0.0,
        "RVOL": 1.0,
        "NATR %": np.nan,
        "Data Health": "Mixed",
    }

    for column, default_value in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default_value

    numeric_columns = [
        "Price",
        "Setup Score",
        "Confidence",
        "Squeeze Bars",
        "Momentum Z",
        "Acceleration Z",
        "Trend Z",
        "RVOL",
        "NATR %",
    ]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized["Setup Score"] = normalized["Setup Score"].fillna(50.0)
    normalized["Confidence"] = normalized["Confidence"].fillna(0.50).clip(0, 1)
    normalized["Squeeze Bars"] = normalized["Squeeze Bars"].fillna(0).astype(int)
    normalized["Momentum Z"] = normalized["Momentum Z"].fillna(0.0)
    normalized["Acceleration Z"] = normalized["Acceleration Z"].fillna(0.0)
    normalized["Trend Z"] = normalized["Trend Z"].fillna(0.0)
    normalized["RVOL"] = normalized["RVOL"].fillna(1.0)
    normalized["Data Health"] = normalized["Data Health"].fillna("Mixed").astype(str)

    return normalized


@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_history(ticker: str, timeframe: str) -> tuple[pd.DataFrame, str | None]:
    config = TIMEFRAME_CONFIG[timeframe]
    try:
        df = yf.download(
            ticker,
            period=config["period"],
            interval=config["download_interval"],
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception as exc:
        return pd.DataFrame(), f"download failed: {exc}"

    df = _flatten_columns(df)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if df.empty or any(column not in df.columns for column in required):
        return pd.DataFrame(), "missing required OHLCV columns"

    df = df[required].copy()
    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = _normalize_index(df.index)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    if config["resample"]:
        df = _resample_ohlcv(df, config["resample"])

    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        return pd.DataFrame(), "cleaned history is empty"

    return df, None


def calculate_signals(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    config = TIMEFRAME_CONFIG[timeframe]
    weights = config["weights"]

    data = df.copy()
    close = data["Close"]
    
    # FIX: Prevent NaN propagation from zero-volume bars (thin hours) wiping out valid history.
    # We enforce a minimal value instead of NaN, ensuring perfectly smooth RVOL calculations.
    volume = data["Volume"].fillna(1e-6).replace(0.0, 1e-6)

    ema_20 = _ema(close, 20)
    ema_50 = _ema(close, 50)
    ema_200 = _ema(close, 200)
    atr_14 = _atr(data, 14)
    atr_20 = _atr(data, 20)
    natr = (atr_14 / close.replace(0.0, np.nan)) * 100.0

    bb_basis = close.rolling(window=20, min_periods=20).mean()
    bb_std = close.rolling(window=20, min_periods=20).std(ddof=0)
    bb_upper = bb_basis + 2.0 * bb_std
    bb_lower = bb_basis - 2.0 * bb_std

    kc_basis = ema_20
    kc_upper = kc_basis + 1.5 * atr_20
    kc_lower = kc_basis - 1.5 * atr_20

    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    squeeze_group = (~squeeze_on).cumsum()
    squeeze_duration = squeeze_on.groupby(squeeze_group).cumsum().fillna(0).astype(int)
    prior_squeeze_duration = squeeze_duration.where(squeeze_on).ffill().shift(1).fillna(0).astype(int)
    squeeze_fired = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    post_squeeze_bars = (~squeeze_on).groupby(squeeze_on.cumsum()).cumsum().fillna(0).astype(int)
    release_decay = pd.Series(
        np.where(
            (~squeeze_on)
            & (prior_squeeze_duration >= config["min_squeeze_bars"])
            & (post_squeeze_bars <= config["release_decay_bars"]),
            (config["release_decay_bars"] + 1 - post_squeeze_bars) / config["release_decay_bars"],
            0.0,
        ),
        index=data.index,
    )

    momentum_raw = (close - ema_20) / atr_14.replace(0.0, np.nan)
    momentum = _ema(momentum_raw, 5)
    acceleration = _ema(momentum.diff(), 3)
    trend_raw = (ema_20 - ema_50) / atr_20.replace(0.0, np.nan)
    rvol = volume / volume.rolling(window=20, min_periods=20).mean()

    momentum_z = _causal_rolling_zscore(momentum, config["z_window"])
    acceleration_z = _causal_rolling_zscore(acceleration, config["z_window"])
    trend_z = _causal_rolling_zscore(trend_raw, config["z_window"])
    rvol_z = _causal_rolling_zscore(np.log(rvol.clip(lower=1e-6)), config["z_window"])

    regime_slope = ema_200.pct_change(config["regime_window"])
    regime_distance = (ema_50 - ema_200) / atr_20.replace(0.0, np.nan)
    regime = np.select(
        [
            (close > ema_200) & (ema_50 > ema_200) & (regime_slope > 0),
            (close < ema_200) & (ema_50 < ema_200) & (regime_slope < 0),
        ],
        ["Bull", "Bear"],
        default="Range",
    )

    directional_raw = (
        weights["mom"] * momentum_z.clip(-3, 3)
        + weights["acc"] * acceleration_z.clip(-3, 3)
        + weights["trend"] * trend_z.clip(-3, 3)
        + weights["vol"] * rvol_z.clip(-3, 3) * np.sign(momentum_z.fillna(0.0))
    )
    regime_bias = np.where(
        regime == "Bull",
        0.18 + regime_distance.clip(lower=0, upper=2).fillna(0.0) * 0.08,
        np.where(
            regime == "Bear",
            -0.18 + regime_distance.clip(lower=-2, upper=0).fillna(0.0) * 0.08,
            0.0,
        ),
    )
    release_bias = np.sign(momentum_z.fillna(0.0)) * 0.25 * release_decay
    compression_drag = np.where(
        squeeze_on,
        -0.10 * np.sign(momentum_z.fillna(0.0)) * momentum_z.abs().clip(0, 1.5),
        0.0,
    )
    setup_score = pd.Series(
        50.0 + 42.0 * np.tanh((directional_raw + regime_bias + release_bias + compression_drag) / 2.2),
        index=data.index,
    ).clip(0, 100)

    volume_quality = volume.notna().rolling(window=40, min_periods=10).mean()
    confidence = (
        0.55
        + 0.20 * np.minimum(momentum_z.abs().fillna(0.0), 2.0) / 2.0
        + 0.15 * np.minimum(trend_z.abs().fillna(0.0), 2.0) / 2.0
        + 0.10 * np.minimum(np.abs(setup_score - 50.0), 35.0) / 35.0
    ).clip(0, 1)

    data["EMA20"] = ema_20
    data["EMA50"] = ema_50
    data["EMA200"] = ema_200
    data["ATR14"] = atr_14
    data["NATR"] = natr
    data["BBUpper"] = bb_upper
    data["BBLower"] = bb_lower
    data["KCUpper"] = kc_upper
    data["KCLower"] = kc_lower
    data["SqueezeOn"] = squeeze_on
    data["SqueezeDuration"] = squeeze_duration
    data["SqueezeFired"] = squeeze_fired
    data["ReleaseDecay"] = release_decay
    data["Momentum"] = momentum
    data["Acceleration"] = acceleration
    data["TrendRaw"] = trend_raw
    data["MomentumZ"] = momentum_z
    data["AccelerationZ"] = acceleration_z
    data["TrendZ"] = trend_z
    data["RVOL"] = rvol
    data["RVOLZ"] = rvol_z
    data["SetupScore"] = setup_score
    data["Regime"] = regime
    data["RegimeSlope"] = regime_slope
    data["RegimeDistance"] = regime_distance
    data["Confidence"] = confidence
    data["VolumeQuality"] = volume_quality
    data["Bias"] = data["SetupScore"].apply(_bias_label)

    data["Setup"] = [
        _setup_label(regime_value, squeeze_value, fired_value, momentum_value, accel_value, rvol_value, score_value)
        for regime_value, squeeze_value, fired_value, momentum_value, accel_value, rvol_value, score_value in zip(
            data["Regime"],
            data["SqueezeOn"],
            data["SqueezeFired"],
            data["MomentumZ"].fillna(0.0),
            data["AccelerationZ"].fillna(0.0),
            data["RVOL"].fillna(0.0),
            data["SetupScore"].fillna(50.0),
        )
    ]

    return data.dropna(
        subset=[
            "EMA20",
            "EMA200",
            "ATR14",
            "MomentumZ",
            "AccelerationZ",
            "TrendZ",
            "RVOL",
            "SetupScore",
            "Confidence",
        ]
    )


def build_overview_chart(symbol: str, df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.43, 0.17, 0.22, 0.18],
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            line=dict(color="#EAF2FF", width=2),
            name="Close",
            hovertemplate="%{x}<br>Close=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["EMA20"],
            mode="lines",
            line=dict(color="#00E5FF", width=1.5),
            name="EMA20",
            hovertemplate="%{x}<br>EMA20=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["EMA50"],
            mode="lines",
            line=dict(color="#00FFAA", width=1.25, dash="dot"),
            name="EMA50",
            hovertemplate="%{x}<br>EMA50=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["EMA200"],
            mode="lines",
            line=dict(color="#FF9F43", width=1.4),
            name="EMA200",
            hovertemplate="%{x}<br>EMA200=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    release_points = df[df["SqueezeFired"]]
    if not release_points.empty:
        fig.add_trace(
            go.Scatter(
                x=release_points.index,
                y=release_points["Close"],
                mode="markers",
                marker=dict(
                    size=9,
                    color=np.where(release_points["MomentumZ"] >= 0, "#00FFAA", "#FF5C5C"),
                    line=dict(color="#0F0F0F", width=1),
                    symbol="diamond",
                ),
                name="Release",
                hovertemplate="%{x}<br>Release price=%{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["SetupScore"],
            mode="lines",
            line=dict(color="#D5DEEB", width=2),
            fill="tozeroy",
            fillcolor="rgba(213, 222, 235, 0.08)",
            name="Setup Score",
            hovertemplate="%{x}<br>Score=%{y:.1f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["MomentumZ"],
            mode="lines",
            line=dict(color="#00FFAA", width=2),
            name="Momentum Z",
            hovertemplate="%{x}<br>Momentum Z=%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["AccelerationZ"],
            mode="lines",
            line=dict(color="#4C7DFF", width=1.7),
            name="Acceleration Z",
            hovertemplate="%{x}<br>Acceleration Z=%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["TrendZ"],
            mode="lines",
            line=dict(color="#FF9F43", width=1.3, dash="dot"),
            name="Trend Z",
            hovertemplate="%{x}<br>Trend Z=%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["RVOL"],
            marker=dict(
                color=np.where(df["RVOL"] >= 1.0, "rgba(0, 229, 255, 0.65)", "rgba(120, 130, 140, 0.45)")
            ),
            name="RVOL",
            hovertemplate="%{x}<br>RVOL=%{y:.2f}<extra></extra>",
        ),
        row=4,
        col=1,
    )

    for start, end in _squeeze_ranges(df.index, df["SqueezeOn"]):
        for row in (1, 2, 3, 4):
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor="rgba(76, 125, 255, 0.08)",
                line_width=0,
                row=row,
                col=1,
            )

    fig.add_hline(y=50, line=dict(color="rgba(255,255,255,0.15)", width=1), row=2, col=1)
    fig.add_hline(y=65, line=dict(color="rgba(0,255,170,0.18)", width=1, dash="dash"), row=2, col=1)
    fig.add_hline(y=35, line=dict(color="rgba(255,92,92,0.18)", width=1, dash="dash"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.16)", width=1), row=3, col=1)
    fig.add_hline(y=2, line=dict(color="rgba(0,255,170,0.12)", width=1, dash="dash"), row=3, col=1)
    fig.add_hline(y=-2, line=dict(color="rgba(255,92,92,0.12)", width=1, dash="dash"), row=3, col=1)
    fig.add_hline(y=1, line=dict(color="rgba(255,255,255,0.10)", width=1, dash="dash"), row=4, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F0F0F",
        plot_bgcolor="#0F0F0F",
        height=940,
        margin=dict(l=50, r=40, t=40, b=40),
        title=dict(text=f"{symbol} deep inspection", font=dict(size=18, color="#EAF2FF")),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.0),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
    fig.update_yaxes(title="Price", row=1, col=1)
    fig.update_yaxes(title="Score", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title="Z-Score", row=3, col=1, range=[-3.5, 3.5])
    fig.update_yaxes(title="RVOL", row=4, col=1)
    return fig


def build_scatter_chart(results: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=3.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.04)", line_width=0)
    fig.add_shape(type="rect", x0=-3.5, y0=-3.5, x1=0, y1=0, fillcolor="rgba(255, 92, 92, 0.04)", line_width=0)

    fig.add_trace(
        go.Scatter(
            x=results["Momentum Z"],
            y=results["Acceleration Z"],
            mode="markers+text",
            text=results["Asset"],
            textposition="top center",
            marker=dict(
                size=(results["RVOL"].clip(lower=0.6, upper=3.0) * 12).tolist(),
                color=results["Setup Score"],
                colorscale=[
                    [0.0, "#FF5C5C"],
                    [0.35, "#FF9F43"],
                    [0.50, "#7A869A"],
                    [0.65, "#00B8D9"],
                    [1.0, "#00FFAA"],
                ],
                cmin=0,
                cmax=100,
                symbol=[_regime_symbol(value) for value in results["Regime"]],
                line=dict(color="#0F0F0F", width=1),
                colorbar=dict(title="Score", tickvals=[20, 50, 80]),
            ),
            customdata=np.stack(
                [
                    results["Setup"],
                    results["Regime"],
                    results["Setup Score"],
                    results["RVOL"],
                    results["Trend Z"],
                    results["Confidence"],
                    results["Squeeze Bars"],
                    results["Data Health"],
                ],
                axis=1,
            ),
            hovertemplate=(
                "%{text}<br>"
                "Momentum Z=%{x:.2f}<br>"
                "Acceleration Z=%{y:.2f}<br>"
                "Setup=%{customdata[0]}<br>"
                "Regime=%{customdata[1]}<br>"
                "Score=%{customdata[2]:.1f}<br>"
                "RVOL=%{customdata[3]:.2f}<br>"
                "Trend Z=%{customdata[4]:.2f}<br>"
                "Confidence=%{customdata[5]:.2f}<br>"
                "Squeeze Bars=%{customdata[6]}<br>"
                "Data=%{customdata[7]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.18)", width=1))
    fig.add_vline(x=0, line=dict(color="rgba(255,255,255,0.18)", width=1))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F0F0F",
        plot_bgcolor="#0F0F0F",
        height=560,
        margin=dict(l=40, r=30, t=30, b=40),
        title=dict(text="Rotation Radar", font=dict(size=18, color="#EAF2FF")),
    )
    fig.update_xaxes(title="Momentum Z", showgrid=False, range=[-3.5, 3.5])
    fig.update_yaxes(title="Acceleration Z", showgrid=False, range=[-3.5, 3.5])
    return fig


def render_signal_board(df: pd.DataFrame) -> None:
    records = df.to_dict(orient="records")
    top_cards_html: list[str] = []
    for rank, row_data in enumerate(records[: min(3, len(records))], start=1):
        fill, glow = _score_visuals(float(row_data["Setup Score"]))
        top_cards_html.append(
            (
                f'<div class="signal-card" style="box-shadow: inset 0 0 0 1px {glow};">'
                f'<div class="signal-card-top"><div><div class="signal-rank">Top {rank}</div>'
                f'<div class="signal-asset">{html.escape(str(row_data["Asset"]))}</div></div>'
                f'<div class="signal-score-pill" style="background:{fill};">{row_data["Setup Score"]:.1f}</div></div>'
                f'<div class="signal-card-setup">{html.escape(str(row_data["Setup"]))}</div>'
                f'<div class="signal-card-meta">'
                f'<span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Squeeze"]), "Squeeze")}">Squeeze {html.escape(str(row_data["Squeeze"]))}</span>'
                f'<span class="signal-badge {_badge_class(str(row_data["Data Health"]), "Data")}">{html.escape(str(row_data["Data Health"]))}</span>'
                f"</div>"
                f'<div class="signal-card-stats">'
                f'<div><div class="signal-stat-label">Momentum Z</div><div class="signal-stat-value">{row_data["Momentum Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">Acceleration</div><div class="signal-stat-value">{row_data["Acceleration Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">Trend Z</div><div class="signal-stat-value">{row_data["Trend Z"]:+.2f}</div></div>'
                f'<div><div class="signal-stat-label">RVOL</div><div class="signal-stat-value">{row_data["RVOL"]:.2f}x</div></div>'
                f"</div></div>"
            )
        )

    rows_html: list[str] = []
    for rank, row_data in enumerate(records, start=1):
        score = float(row_data["Setup Score"])
        fill, _ = _score_visuals(score)
        momentum_class = _metric_class(float(row_data["Momentum Z"]), 0.35, -0.35)
        accel_class = _metric_class(float(row_data["Acceleration Z"]), 0.10, -0.10)
        trend_class = _metric_class(float(row_data["Trend Z"]), 0.20, -0.20)
        rvol_class = _metric_class(float(row_data["RVOL"]), 1.05, 0.95)
        rows_html.append(
            (
                "<tr>"
                f'<td class="rank-cell">{rank:02d}</td>'
                f'<td class="asset-cell">{html.escape(str(row_data["Asset"]))}</td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Setup"]), "Setup")}">{html.escape(str(row_data["Setup"]))}</span></td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span></td>'
                f'<td><span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span></td>'
                f'<td class="score-cell"><div class="score-shell"><div class="score-fill" style="width:{score:.1f}%; background:{fill};"></div></div><div class="score-text">{score:.1f}/100</div></td>'
                f'<td class="{momentum_class}">{row_data["Momentum Z"]:+.2f}</td>'
                f'<td class="{accel_class}">{row_data["Acceleration Z"]:+.2f}</td>'
                f'<td class="{trend_class}">{row_data["Trend Z"]:+.2f}</td>'
                f'<td class="{rvol_class}">{row_data["RVOL"]:.2f}x</td>'
                f"<td>{int(row_data['Squeeze Bars'])}</td>"
                f'<td>{html.escape(str(row_data["Data Health"]))}</td>'
                "</tr>"
            )
        )

    board_html = (
        '<div class="signal-board">'
        '<div class="signal-board-header"><div>'
        '<div class="signal-board-title">Signal Board</div>'
        '<div class="signal-board-subtitle">Causally normalized setups ranked by directional imbalance and structural trend quality</div>'
        "</div></div>"
        f'<div class="signal-board-grid">{"".join(top_cards_html)}</div>'
        '<div class="signal-table"><table><thead><tr>'
        "<th>#</th><th>Asset</th><th>Setup</th><th>Bias</th><th>Regime</th><th>Score</th>"
        "<th>Momentum</th><th>Accel</th><th>Trend</th><th>RVOL</th><th>SQZ</th><th>Data</th>"
        f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div></div>'
    )
    st.markdown(board_html, unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        """
        <div class="radar-shell">
            <div class="radar-kicker">Control Node</div>
            <div class="radar-title">Radar Controls</div>
            <div class="radar-subtitle">Institutional command panel with clean hierarchy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("alpha_momentum_controls"):
        st.markdown('<div class="radar-field-label">Watchlist</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="watchlist-head">
                <span class="watchlist-dot" style="background:#00E5FF;"></span>
                <span class="watchlist-dot" style="background:#00D68F;"></span>
                <span class="watchlist-dot" style="background:#FF9F43;"></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        watchlist_text = st.text_area("Watchlist", DEFAULT_WATCHLIST, height=120, label_visibility="collapsed")

        preview_tickers = _clean_watchlist(watchlist_text)[:6]
        preview_html = "".join(
            f'<span class="watchlist-chip">{html.escape(ticker)}</span>'
            for ticker in preview_tickers
        )
        st.markdown(f'<div class="watchlist-preview">{preview_html}</div>', unsafe_allow_html=True)

        st.markdown('<div class="radar-field-label">Timeframe</div>', unsafe_allow_html=True)
        tf = st.radio("Timeframe", ["1h", "4h", "1d"], horizontal=True, index=2, label_visibility="collapsed")

        st.markdown(
            f'<div class="display-note">Display profile fixed at <b>Top {DISPLAY_ROWS}</b> assets for a cleaner, more institutional board.</div>',
            unsafe_allow_html=True,
        )

        btn = st.form_submit_button("Analyze Market")

if "results_df" not in st.session_state:
    st.session_state["results_df"] = pd.DataFrame()
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = []

if btn:
    results = []
    st.session_state["watchlist"] = _clean_watchlist(watchlist_text)

    with st.spinner("Calculating Statistical Edge..."):
        for symbol in st.session_state["watchlist"]:
            try:
                hist, fetch_error = fetch_price_history(symbol, tf)
                if fetch_error:
                    continue

                if len(hist) > TIMEFRAME_CONFIG.get(tf, {}).get("min_history", 240):
                    enriched = calculate_signals(hist, tf)
                    if enriched.empty:
                        continue
                    last_row = enriched.iloc[-1]
                    results.append(
                        {
                            "Asset": symbol,
                            "Price": float(last_row["Close"]),
                            "Regime": str(last_row["Regime"]),
                            "Bias": str(last_row["Bias"]),
                            "Setup": str(last_row["Setup"]),
                            "Setup Score": float(last_row["SetupScore"]),
                            "Confidence": float(last_row["Confidence"]),
                            "Squeeze": "ON" if bool(last_row["SqueezeOn"]) else "OFF",
                            "Squeeze Bars": int(last_row["SqueezeDuration"]),
                            "Momentum Z": float(last_row["MomentumZ"]),
                            "Acceleration Z": float(last_row["AccelerationZ"]),
                            "Trend Z": float(last_row["TrendZ"]),
                            "RVOL": float(last_row["RVOL"]),
                            "NATR %": float(last_row["NATR"]),
                            "Data Health": _data_health_label(
                                float(last_row["VolumeQuality"]) if pd.notna(last_row["VolumeQuality"]) else 0.0,
                                len(hist),
                                TIMEFRAME_CONFIG[tf]["min_history"],
                            ),
                        }
                    )
            except Exception:
                continue

    if results:
        st.session_state["results_df"] = (
            pd.DataFrame(results)
            .sort_values("Setup Score", ascending=False)
            .reset_index(drop=True)
        )
    else:
        st.warning("No data found.")

results_df = st.session_state.get("results_df", pd.DataFrame())
results_df = _ensure_results_schema(results_df)
st.session_state["results_df"] = results_df

if results_df.empty:
    st.info("Run the scan to populate the matrix.")
    st.stop()

top_asset = results_df.iloc[0]
market_bias = "BULLISH" if results_df["Setup Score"].mean() > 50 else "BEARISH"
breadth = ((results_df["Setup Score"] > 57).sum() - (results_df["Setup Score"] < 43).sum()) / max(len(results_df), 1)
breadth_label = "Bullish" if breadth > 0.15 else "Bearish" if breadth < -0.15 else "Balanced"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Assets Scanned", f"{len(results_df)}")
col2.metric("Top Alpha Pick", top_asset["Asset"], f'{top_asset["Setup Score"]:.1f}')
col3.metric("Market Sentiment", market_bias)
col4.metric("Breadth", breadth_label, f"{breadth:+.0%}")

col5, col6, col7 = st.columns(3)
col5.metric("Long Bias", int((results_df["Setup Score"] >= 57).sum()))
col6.metric("Short Bias", int((results_df["Setup Score"] <= 43).sum()))
col7.metric("Squeeze Alerts", int((results_df["Squeeze"] == "ON").sum()))

display_df = results_df.head(DISPLAY_ROWS).copy()

render_signal_board(display_df)

csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download current radar as CSV",
    data=csv_bytes,
    file_name=f"alpha_momentum_matrix_{tf}.csv",
    mime="text/csv",
)

st.plotly_chart(build_scatter_chart(display_df), use_container_width=True, config={"displayModeBar": False})

selected_symbol = st.selectbox("Inspect asset", display_df["Asset"].tolist(), index=0)
selected_history = None
for candidate in st.session_state.get("watchlist", []):
    if candidate == selected_symbol:
        selected_history, _ = fetch_price_history(selected_symbol, tf)
        break

if selected_history is not None and not selected_history.empty:
    selected_history = calculate_signals(selected_history, tf)
    if not selected_history.empty:
        st.plotly_chart(
            build_overview_chart(selected_symbol, selected_history.tail(TIMEFRAME_CONFIG[tf]["display_bars"])),
            use_container_width=True,
            config={"displayModeBar": False},
        )

with st.expander("Methodology", expanded=False):
    st.markdown(
        """
- `4h` is built by explicit `1h -> 4h` OHLCV resampling, so the timeframe is temporally honest instead of a relabeled `1h`.
- `Momentum Z`, `Acceleration Z`, `Trend Z`, and `RVOL Z` use a causal rolling baseline that only looks at prior bars.
- `Squeeze` uses Bollinger Bands inside Keltner Channels, and the post-release boost only survives for a short decay window after a real compression.
- `Regime` requires price above or below `EMA200`, confirmation from `EMA50`, and a slower `EMA200` slope so it does not flip on one noisy bar.
- `Setup Score` is bounded from `0` to `100` with `tanh`, which keeps tails informative without letting a single component dominate.
- `Auto-adjusted` OHLC reduces split and dividend contamination for equities when mixing stocks, futures, and crypto in one watchlist.
- `Confidence` is a secondary quality readout, not a trading signal. It rewards cleaner trend alignment and stronger directional separation.
        """.strip()
    )

st.caption(
    "Data source: Yahoo Finance public market data. Cross-asset dashboards remain heuristic by nature, "
    "so the score is best used for ranking within a watchlist rather than as a universal forecast probability."
)
