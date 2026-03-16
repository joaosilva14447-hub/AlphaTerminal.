import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


st.set_page_config(page_title="Fear & Greed Index", layout="wide")

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
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Fear & Greed Index (Derivatives)</h1>",
    unsafe_allow_html=True,
)


BINANCE_FAPI = "https://fapi.binance.com"


class ApiError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None) -> dict | list:
    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    return r.json()


def _zscore(series: pd.Series, window: int) -> pd.Series:
    window = int(window)
    window = max(10, min(500, window))
    mu = series.rolling(window=window, min_periods=window).mean()
    sigma = series.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mu) / sigma.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def _label(score: float) -> str:
    if score < 20:
        return "Extreme Fear"
    if score < 40:
        return "Fear"
    if score < 60:
        return "Neutral"
    if score < 80:
        return "Greed"
    return "Extreme Greed"


@dataclass(frozen=True)
class SeriesPack:
    df: pd.DataFrame
    last_price: float | None


@st.cache_data(ttl=120)
def fetch_series(symbol: str, limit: int, interval: str) -> SeriesPack:
    symbol = symbol.strip().upper()
    limit = int(limit)
    limit = max(100, min(1000, limit))

    # Price (futures klines)
    klines = _get_json(f"{BINANCE_FAPI}/fapi/v1/klines", {"symbol": symbol, "interval": interval, "limit": limit})
    if not isinstance(klines, list) or not klines:
        raise ApiError("No kline data returned.")
    kdf = pd.DataFrame(
        klines,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "qav",
            "num_trades",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    )
    kdf["ts"] = pd.to_datetime(kdf["open_time"], unit="ms", utc=True, errors="coerce")
    kdf["close"] = pd.to_numeric(kdf["close"], errors="coerce")
    kdf = kdf.dropna(subset=["ts", "close"]).sort_values("ts")

    # Open interest history
    oi = _get_json(
        f"{BINANCE_FAPI}/futures/data/openInterestHist",
        {"symbol": symbol, "period": interval, "limit": limit},
    )
    if not isinstance(oi, list) or not oi:
        raise ApiError("No open interest history returned.")
    oidf = pd.DataFrame(oi)
    oidf["ts"] = pd.to_datetime(oidf["timestamp"], unit="ms", utc=True, errors="coerce")
    oidf["oi"] = pd.to_numeric(oidf["sumOpenInterest"], errors="coerce")
    oidf = oidf.dropna(subset=["ts", "oi"]).sort_values("ts")

    # Funding history (8h cadence)
    funding = _get_json(f"{BINANCE_FAPI}/fapi/v1/fundingRate", {"symbol": symbol, "limit": min(1000, limit)})
    if not isinstance(funding, list) or not funding:
        raise ApiError("No funding history returned.")
    fdf = pd.DataFrame(funding)
    fdf["funding_ts"] = pd.to_datetime(fdf["fundingTime"], unit="ms", utc=True, errors="coerce")
    fdf["funding_pct"] = pd.to_numeric(fdf["fundingRate"], errors="coerce") * 100.0
    fdf = fdf.dropna(subset=["funding_ts", "funding_pct"]).sort_values("funding_ts")

    # Merge price + OI on timestamp (hourly)
    base = pd.merge(kdf[["ts", "close"]], oidf[["ts", "oi"]], on="ts", how="inner")
    if base.empty:
        raise ApiError("Price and OI timestamps do not overlap.")

    # Align funding to each timestamp (backward fill)
    base = pd.merge_asof(
        base.sort_values("ts"),
        fdf.sort_values("funding_ts"),
        left_on="ts",
        right_on="funding_ts",
        direction="backward",
    )

    try:
        last_price = float(base["close"].iloc[-1])
    except Exception:
        last_price = None

    return SeriesPack(df=base, last_price=last_price)


left, right = st.columns([1.2, 1.0])
with left:
    symbol = st.text_input("SYMBOL", "BTCUSDT").strip().upper()
with right:
    interval = st.selectbox("INTERVAL", ["1h", "4h"], index=0)

controls = st.columns([1, 1, 1, 1])
limit = int(controls[0].selectbox("LOOKBACK POINTS", [200, 400, 800, 1000], index=1))
z_window = int(controls[1].selectbox("Z-WINDOW", [21, 42, 84, 168], index=1))
vol_window = int(controls[2].selectbox("VOL WINDOW", [12, 24, 48, 96], index=1))
smooth = controls[3].selectbox("SMOOTHING", ["None", "EMA-5", "EMA-10"], index=1)

weights = st.columns([1, 1, 1, 1])
w_funding = float(weights[0].selectbox("W FUNDING", [0.2, 0.3, 0.35, 0.4], index=2))
w_momentum = float(weights[1].selectbox("W MOMENTUM", [0.2, 0.25, 0.3], index=1))
w_oi = float(weights[2].selectbox("W OI", [0.2, 0.25, 0.3], index=1))
w_vol = float(weights[3].selectbox("W VOL (FEAR)", [0.1, 0.15, 0.2], index=1))

try:
    pack = fetch_series(symbol=symbol, limit=limit, interval=interval)
except Exception as exc:
    st.error(f"Data unavailable: {exc}")
    st.stop()

df = pack.df.copy()
df["price_return"] = np.log(df["close"]).diff()
df["oi_return"] = df["oi"].pct_change()
df["vol"] = df["price_return"].rolling(window=vol_window, min_periods=vol_window).std(ddof=0)

df["funding_z"] = _zscore(df["funding_pct"], window=z_window)
df["momentum_z"] = _zscore(df["price_return"], window=z_window)
df["oi_z"] = _zscore(df["oi_return"], window=z_window)
df["vol_z"] = _zscore(df["vol"], window=z_window)

df = df.dropna(subset=["funding_z", "momentum_z", "oi_z", "vol_z"]).copy()
if df.empty:
    st.warning("Not enough data to compute the index. Try a smaller window or larger lookback.")
    st.stop()

df["score_raw"] = (
    w_funding * df["funding_z"]
    + w_momentum * df["momentum_z"]
    + w_oi * df["oi_z"]
    - w_vol * df["vol_z"]
)
df["score"] = 50 + 50 * np.tanh(df["score_raw"] / 2.0)

if smooth == "EMA-5":
    df["score"] = df["score"].ewm(span=5, adjust=False).mean()
elif smooth == "EMA-10":
    df["score"] = df["score"].ewm(span=10, adjust=False).mean()

latest = df.iloc[-1]
score = float(latest["score"])
label = _label(score)
last_ts = latest["ts"].to_pydatetime()

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
if pack.last_price is None:
    c1.metric("PRICE", "n/a")
else:
    c1.metric("PRICE", f"${pack.last_price:,.2f}")
c2.metric("INDEX", f"{score:.1f}")
c3.metric("STATE", label)
c4.metric("LAST UPDATE (UTC)", last_ts.strftime("%Y-%m-%d %H:%M"))

gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": "#EAF2FF"}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#19D3C5"},
            "bgcolor": "#0F0F0F",
            "steps": [
                {"range": [0, 20], "color": "#3D2C8D"},
                {"range": [20, 40], "color": "#5B3FA3"},
                {"range": [40, 60], "color": "#1C6E8C"},
                {"range": [60, 80], "color": "#1FA187"},
                {"range": [80, 100], "color": "#7AD151"},
            ],
            "threshold": {"line": {"color": "#EAF2FF", "width": 2}, "thickness": 0.7, "value": score},
        },
        title={"text": "Fear & Greed Index"},
    )
)
gauge.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    margin=dict(l=20, r=20, t=40, b=20),
    height=360,
)

score_fig = go.Figure(
    go.Scatter(
        x=df["ts"],
        y=df["score"],
        mode="lines",
        line=dict(color="#EAF2FF", width=2),
        hovertemplate="%{x}<br>Score=%{y:.1f}<extra></extra>",
    )
)
score_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=360,
    margin=dict(l=40, r=20, t=10, b=30),
    showlegend=False,
)
score_fig.update_yaxes(range=[0, 100], showgrid=False, tickfont=dict(color="#C7D0DB"))
score_fig.update_xaxes(showgrid=False, tickfont=dict(color="#C7D0DB"))

g1, g2 = st.columns([1, 2])
g1.plotly_chart(gauge, use_container_width=True, config={"displayModeBar": False})
g2.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})

components = make_subplots(rows=1, cols=1)
components.add_trace(
    go.Scatter(x=df["ts"], y=df["funding_z"], name="Funding Z", line=dict(color="#00FF8C", width=1.6)),
)
components.add_trace(
    go.Scatter(x=df["ts"], y=df["momentum_z"], name="Momentum Z", line=dict(color="#4CA7FF", width=1.6)),
)
components.add_trace(
    go.Scatter(x=df["ts"], y=df["oi_z"], name="OI Z", line=dict(color="#B39DFF", width=1.6)),
)
components.add_trace(
    go.Scatter(x=df["ts"], y=df["vol_z"], name="Vol Z (Fear)", line=dict(color="#FF6B6B", width=1.6)),
)
components.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=420,
    margin=dict(l=40, r=20, t=30, b=30),
    legend=dict(orientation="h", y=1.02, x=0),
)
components.update_yaxes(showgrid=False, tickfont=dict(color="#C7D0DB"))
components.update_xaxes(showgrid=False, tickfont=dict(color="#C7D0DB"))

st.plotly_chart(components, use_container_width=True, config={"displayModeBar": False})

with st.expander("How This Index Works", expanded=False):
    st.markdown(
        """
- **Funding Z**: extreme positive = crowded longs (greed), extreme negative = crowded shorts (fear).
- **Momentum Z**: positive price momentum = greed; negative momentum = fear.
- **OI Z**: leverage build-up = greed; leverage unwind = fear.
- **Vol Z**: higher volatility = fear; lower volatility = greed.

The composite is a weighted sum mapped to `0..100` with a `tanh` curve.
        """.strip()
    )

st.caption(
    "Free data sources (public): Binance USD-M `klines`, `openInterestHist`, `fundingRate`."
)

