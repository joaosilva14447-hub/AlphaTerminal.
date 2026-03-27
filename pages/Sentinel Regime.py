import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots


st.set_page_config(page_title="Alpha Momentum Matrix", layout="wide")

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
        grid-template-columns: repeat(3, minmax(0, 1fr));
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
    @media (max-width: 1100px) {
        .signal-board-grid { grid-template-columns: 1fr; }
        .signal-card-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); }
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
    "Cross-asset squeeze and expansion radar with volatility-normalized momentum, "
    "relative volume, and a regime filter designed to stay simple and interpretable."
)


TIMEFRAME_CONFIG = {
    "1h": {"download_interval": "60m", "period": "730d", "resample": None},
    "4h": {"download_interval": "60m", "period": "730d", "resample": "4H"},
    "1d": {"download_interval": "1d", "period": "5y", "resample": None},
}

DEFAULT_WATCHLIST = "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, AAPL"


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


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def _atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low),
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
    out = df.resample(rule).agg(agg)
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
    if score >= 65:
        return "Strong Long"
    if score >= 55:
        return "Long"
    if score <= 35:
        return "Strong Short"
    if score <= 45:
        return "Short"
    return "Neutral"


def _score_visuals(score: float) -> tuple[str, str]:
    if score >= 65:
        return "linear-gradient(90deg, #00D68F, #00FFAA)", "rgba(0, 255, 170, 0.18)"
    if score >= 55:
        return "linear-gradient(90deg, #00B8D9, #00E5FF)", "rgba(0, 229, 255, 0.18)"
    if score <= 35:
        return "linear-gradient(90deg, #FF6B6B, #FF3B30)", "rgba(255, 92, 92, 0.18)"
    if score <= 45:
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


def _setup_label(regime: str, squeeze_on: bool, squeeze_fired: bool, momentum_z: float, accel_z: float, rvol: float) -> str:
    if squeeze_on:
        return "Compression"
    if regime == "Bull" and momentum_z > 0.35 and accel_z > 0 and rvol > 1.05:
        return "Bull Expansion"
    if regime == "Bear" and momentum_z < -0.35 and accel_z < 0 and rvol > 1.05:
        return "Bear Expansion"
    if squeeze_fired and momentum_z > 0:
        return "Bull Release"
    if squeeze_fired and momentum_z < 0:
        return "Bear Release"
    if abs(momentum_z) < 0.35 and abs(accel_z) < 0.35:
        return "Neutral"
    return "Transition"


@st.cache_data(ttl=300)
def fetch_price_history(ticker: str, timeframe: str) -> pd.DataFrame:
    config = TIMEFRAME_CONFIG[timeframe]
    df = yf.download(
        ticker,
        period=config["period"],
        interval=config["download_interval"],
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    df = _flatten_columns(df)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if df.empty or any(column not in df.columns for column in required):
        return pd.DataFrame()

    df = df[required].copy()
    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = _normalize_index(df.index)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    if config["resample"]:
        df = _resample_ohlcv(df, config["resample"])

    return df.dropna()


def calculate_signals(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    close = data["Close"]
    volume = data["Volume"].replace(0.0, np.nan)

    ema_20 = _ema(close, 20)
    ema_50 = _ema(close, 50)
    ema_200 = _ema(close, 200)
    atr_14 = _atr(data, 14)
    atr_20 = _atr(data, 20)

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
    squeeze_fired = (~squeeze_on) & squeeze_on.shift(1).fillna(False)

    momentum_raw = (close - ema_20) / atr_14.replace(0.0, np.nan)
    momentum = _ema(momentum_raw, 5)
    acceleration = _ema(momentum.diff(), 3)
    rvol = volume / volume.rolling(window=20, min_periods=20).mean()

    regime_slope = ema_200.pct_change(20)
    regime = np.select(
        [
            (close > ema_200) & (regime_slope > 0),
            (close < ema_200) & (regime_slope < 0),
        ],
        ["Bull", "Bear"],
        default="Range",
    )

    momentum_z = _rolling_zscore(momentum, 126)
    acceleration_z = _rolling_zscore(acceleration, 126)
    rvol_z = _rolling_zscore(np.log(rvol.replace(0.0, np.nan)), 126)

    directional_raw = (
        0.55 * momentum_z.clip(-3, 3)
        + 0.30 * acceleration_z.clip(-3, 3)
        + 0.15 * rvol_z.clip(-3, 3) * np.sign(momentum_z.fillna(0.0))
    )
    regime_bias = np.where(regime == "Bull", 0.35, np.where(regime == "Bear", -0.35, 0.0))
    release_bias = np.where(squeeze_fired, np.sign(momentum.fillna(0.0)) * 0.20, 0.0)
    setup_score = pd.Series(
        50.0 + 40.0 * np.tanh((directional_raw + regime_bias + release_bias) / 2.5),
        index=data.index,
    ).clip(0, 100)

    data["EMA20"] = ema_20
    data["EMA50"] = ema_50
    data["EMA200"] = ema_200
    data["ATR14"] = atr_14
    data["BBUpper"] = bb_upper
    data["BBLower"] = bb_lower
    data["KCUpper"] = kc_upper
    data["KCLower"] = kc_lower
    data["SqueezeOn"] = squeeze_on
    data["SqueezeDuration"] = squeeze_duration
    data["SqueezeFired"] = squeeze_fired
    data["Momentum"] = momentum
    data["Acceleration"] = acceleration
    data["MomentumZ"] = momentum_z
    data["AccelerationZ"] = acceleration_z
    data["RVOL"] = rvol
    data["SetupScore"] = setup_score
    data["Regime"] = regime
    data["Bias"] = data["SetupScore"].apply(_bias_label)

    data["Setup"] = [
        _setup_label(regime_value, squeeze_value, fired_value, momentum_value, accel_value, rvol_value)
        for regime_value, squeeze_value, fired_value, momentum_value, accel_value, rvol_value in zip(
            data["Regime"],
            data["SqueezeOn"],
            data["SqueezeFired"],
            data["MomentumZ"].fillna(0.0),
            data["AccelerationZ"].fillna(0.0),
            data["RVOL"].fillna(0.0),
        )
    ]

    return data.dropna(
        subset=[
            "EMA20",
            "EMA200",
            "ATR14",
            "MomentumZ",
            "AccelerationZ",
            "RVOL",
            "SetupScore",
        ]
    )


def build_overview_chart(symbol: str, df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.52, 0.24, 0.24],
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
            y=df["EMA200"],
            mode="lines",
            line=dict(color="#FF9F43", width=1.4),
            name="EMA200",
            hovertemplate="%{x}<br>EMA200=%{y:,.2f}<extra></extra>",
        ),
        row=1,
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
        row=2,
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
        row=2,
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
        row=3,
        col=1,
    )

    for start, end in _squeeze_ranges(df.index, df["SqueezeOn"]):
        for row in (1, 2, 3):
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor="rgba(76, 125, 255, 0.08)",
                line_width=0,
                row=row,
                col=1,
            )

    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.16)", width=1), row=2, col=1)
    fig.add_hline(y=1, line=dict(color="rgba(255,255,255,0.10)", width=1, dash="dash"), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F0F0F",
        plot_bgcolor="#0F0F0F",
        height=860,
        margin=dict(l=50, r=40, t=40, b=40),
        title=dict(text=f"{symbol} overview", font=dict(size=18, color="#EAF2FF")),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.0),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
    fig.update_yaxes(title="Price", row=1, col=1)
    fig.update_yaxes(title="Z-Score", row=2, col=1, range=[-3.5, 3.5])
    fig.update_yaxes(title="RVOL", row=3, col=1)
    return fig


def build_scatter_chart(results: pd.DataFrame) -> go.Figure:
    palette = {
        "Bull Expansion": "#00FFAA",
        "Bull Release": "#2DD4BF",
        "Compression": "#4C7DFF",
        "Neutral": "#A0AEC0",
        "Transition": "#C7D0DB",
        "Bear Release": "#FF9F43",
        "Bear Expansion": "#FF5C5C",
    }
    colors = [palette.get(value, "#C7D0DB") for value in results["Setup"]]
    sizes = (results["RVOL"].clip(lower=0.5, upper=3.0) * 12).tolist()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=results["Momentum Z"],
            y=results["Acceleration Z"],
            mode="markers+text",
            text=results["Asset"],
            textposition="top center",
            marker=dict(size=sizes, color=colors, line=dict(color="#0F0F0F", width=1)),
            customdata=np.stack(
                [
                    results["Setup"],
                    results["Regime"],
                    results["Setup Score"],
                    results["RVOL"],
                    results["Squeeze Bars"],
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
                "Squeeze Bars=%{customdata[4]}<extra></extra>"
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
    )
    fig.update_xaxes(title="Momentum Z", showgrid=False)
    fig.update_yaxes(title="Acceleration Z", showgrid=False)
    return fig


def render_signal_board(df: pd.DataFrame) -> None:
    records = df.to_dict(orient="records")
    top_cards_html: list[str] = []
    for rank, row_data in enumerate(records[: min(3, len(records))], start=1):
        fill, glow = _score_visuals(float(row_data["Setup Score"]))
        top_cards_html.append(
            f"""
            <div class="signal-card" style="box-shadow: inset 0 0 0 1px {glow};">
                <div class="signal-card-top">
                    <div>
                        <div class="signal-rank">Top {rank}</div>
                        <div class="signal-asset">{html.escape(str(row_data["Asset"]))}</div>
                    </div>
                    <div class="signal-score-pill" style="background:{fill};">
                        {row_data["Setup Score"]:.1f}
                    </div>
                </div>
                <div class="signal-card-setup">{html.escape(str(row_data["Setup"]))}</div>
                <div class="signal-card-meta">
                    <span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span>
                    <span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span>
                    <span class="signal-badge {_badge_class(str(row_data["Squeeze"]), "Squeeze")}">Squeeze {html.escape(str(row_data["Squeeze"]))}</span>
                </div>
                <div class="signal-card-stats">
                    <div>
                        <div class="signal-stat-label">Momentum Z</div>
                        <div class="signal-stat-value">{row_data["Momentum Z"]:+.2f}</div>
                    </div>
                    <div>
                        <div class="signal-stat-label">Acceleration</div>
                        <div class="signal-stat-value">{row_data["Acceleration Z"]:+.2f}</div>
                    </div>
                    <div>
                        <div class="signal-stat-label">RVOL</div>
                        <div class="signal-stat-value">{row_data["RVOL"]:.2f}x</div>
                    </div>
                </div>
            </div>
            """
        )

    rows_html: list[str] = []
    for rank, row_data in enumerate(records, start=1):
        score = float(row_data["Setup Score"])
        fill, _ = _score_visuals(score)
        momentum_class = _metric_class(float(row_data["Momentum Z"]), 0.35, -0.35)
        accel_class = _metric_class(float(row_data["Acceleration Z"]), 0.10, -0.10)
        rvol_class = _metric_class(float(row_data["RVOL"]), 1.05, 0.95)
        rows_html.append(
            f"""
            <tr>
                <td class="rank-cell">{rank:02d}</td>
                <td class="asset-cell">{html.escape(str(row_data["Asset"]))}</td>
                <td><span class="signal-badge {_badge_class(str(row_data["Setup"]), "Setup")}">{html.escape(str(row_data["Setup"]))}</span></td>
                <td><span class="signal-badge {_badge_class(str(row_data["Bias"]), "Bias")}">{html.escape(str(row_data["Bias"]))}</span></td>
                <td><span class="signal-badge {_badge_class(str(row_data["Regime"]), "Regime")}">{html.escape(str(row_data["Regime"]))}</span></td>
                <td class="score-cell">
                    <div class="score-shell"><div class="score-fill" style="width:{score:.1f}%; background:{fill};"></div></div>
                    <div class="score-text">{score:.1f}/100</div>
                </td>
                <td class="{momentum_class}">{row_data["Momentum Z"]:+.2f}</td>
                <td class="{accel_class}">{row_data["Acceleration Z"]:+.2f}</td>
                <td class="{rvol_class}">{row_data["RVOL"]:.2f}x</td>
                <td>{int(row_data["Squeeze Bars"])}</td>
            </tr>
            """
        )

    board_html = f"""
    <div class="signal-board">
        <div class="signal-board-header">
            <div>
                <div class="signal-board-title">Signal Board</div>
                <div class="signal-board-subtitle">Priority-ranked setups with stronger visual hierarchy for fast decision-making</div>
            </div>
        </div>
        <div class="signal-board-grid">
            {''.join(top_cards_html)}
        </div>
        <div class="signal-table">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Asset</th>
                        <th>Setup</th>
                        <th>Bias</th>
                        <th>Regime</th>
                        <th>Score</th>
                        <th>Momentum</th>
                        <th>Accel</th>
                        <th>RVOL</th>
                        <th>SQZ</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows_html)}
                </tbody>
            </table>
        </div>
    </div>
    """
    st.markdown(board_html, unsafe_allow_html=True)


with st.sidebar:
    with st.form("alpha_momentum_controls"):
        st.header("Radar Controls")
        watchlist_text = st.text_area("Watchlist", DEFAULT_WATCHLIST, height=120)
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
        top_n = st.slider("Rows displayed", min_value=4, max_value=20, value=10, step=1)
        submitted = st.form_submit_button("Analyze Market")

run_analysis = submitted or "alpha_momentum_results" not in st.session_state

if run_analysis:
    tickers = _clean_watchlist(watchlist_text)
    results_rows: list[dict[str, object]] = []
    histories: dict[str, pd.DataFrame] = {}
    failures: list[str] = []

    if not tickers:
        st.warning("Add at least one ticker to the watchlist.")
        st.stop()

    with st.spinner("Processing squeeze, momentum, and volume structure..."):
        for symbol in tickers:
            try:
                raw = fetch_price_history(symbol, timeframe)
                if raw.empty or len(raw) < 220:
                    failures.append(f"{symbol}: not enough clean history")
                    continue

                enriched = calculate_signals(raw)
                if enriched.empty:
                    failures.append(f"{symbol}: indicators could not be computed")
                    continue

                last = enriched.iloc[-1]
                histories[symbol] = enriched.tail(250)
                results_rows.append(
                    {
                        "Asset": symbol,
                        "Price": float(last["Close"]),
                        "Regime": str(last["Regime"]),
                        "Bias": str(last["Bias"]),
                        "Setup": str(last["Setup"]),
                        "Setup Score": float(last["SetupScore"]),
                        "Squeeze": "ON" if bool(last["SqueezeOn"]) else "OFF",
                        "Squeeze Bars": int(last["SqueezeDuration"]),
                        "Momentum Z": float(last["MomentumZ"]),
                        "Acceleration Z": float(last["AccelerationZ"]),
                        "RVOL": float(last["RVOL"]),
                    }
                )
            except Exception as exc:
                failures.append(f"{symbol}: {exc}")

    results_df = pd.DataFrame(results_rows)
    if not results_df.empty:
        results_df["Priority"] = (results_df["Setup Score"] - 50.0).abs()
        results_df = results_df.sort_values(["Priority", "Setup Score"], ascending=[False, False]).reset_index(drop=True)
    st.session_state["alpha_momentum_results"] = results_df
    st.session_state["alpha_momentum_histories"] = histories
    st.session_state["alpha_momentum_failures"] = failures
    st.session_state["alpha_momentum_watchlist"] = tickers
    st.session_state["alpha_momentum_timeframe"] = timeframe

results_df = st.session_state.get("alpha_momentum_results", pd.DataFrame())
histories = st.session_state.get("alpha_momentum_histories", {})
failures = st.session_state.get("alpha_momentum_failures", [])
active_timeframe = st.session_state.get("alpha_momentum_timeframe", timeframe)

if results_df.empty:
    st.warning("No assets returned enough clean data to compute the matrix.")
    if failures:
        with st.expander("Diagnostics", expanded=False):
            st.write("\n".join(failures))
    st.stop()

long_count = int((results_df["Setup Score"] >= 55).sum())
short_count = int((results_df["Setup Score"] <= 45).sum())
compression_count = int((results_df["Setup"] == "Compression").sum())
leader = results_df.iloc[0]

c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
c1.metric("Assets Scanned", f"{len(results_df)}")
c2.metric("Long Bias", f"{long_count}")
c3.metric("Short Bias", f"{short_count}")
c4.metric("Top Priority", f"{leader['Asset']} ({leader['Setup']})")

d1, d2, d3 = st.columns([1, 1, 1.4])
d1.metric("Compressions", f"{compression_count}")
d2.metric("Timeframe", active_timeframe)
d3.metric("Average Score", f"{results_df['Setup Score'].mean():.1f}")

display_df = results_df.drop(columns=["Priority"]).head(top_n)
render_signal_board(display_df)

csv_bytes = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download current radar as CSV",
    data=csv_bytes,
    file_name=f"alpha_momentum_matrix_{active_timeframe}.csv",
    mime="text/csv",
)

st.plotly_chart(build_scatter_chart(display_df), use_container_width=True, config={"displayModeBar": False})

selected_symbol = st.selectbox("Inspect asset", display_df["Asset"].tolist(), index=0)
selected_history = histories.get(selected_symbol)
if selected_history is not None and not selected_history.empty:
    st.plotly_chart(build_overview_chart(selected_symbol, selected_history), use_container_width=True, config={"displayModeBar": False})

if failures:
    with st.expander("Diagnostics", expanded=False):
        for failure in failures:
            st.write(f"- {failure}")

with st.expander("Methodology", expanded=False):
    st.markdown(
        """
- `Squeeze` uses Bollinger Bands inside Keltner Channels to flag compression.
- `Momentum Z` measures distance from `EMA20` in ATR units, then standardizes it on a rolling basis.
- `Acceleration Z` tracks the first derivative of normalized momentum instead of raw price change.
- `RVOL` is relative volume versus the 20-bar average and is used as confirmation, not as a standalone signal.
- `Setup Score` is a bounded ranking signal from 0 to 100, centered at 50, with a light regime and squeeze-release adjustment.
- The matrix deliberately keeps a small feature set and fixed defaults to reduce the risk of overfitting.
        """.strip()
    )

st.caption(
    "Data source: Yahoo Finance public market data. The `4h` view is derived from `1h` data to avoid interval inconsistencies."
)
