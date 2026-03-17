import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


st.set_page_config(page_title="Funding Stress Index", layout="wide")

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
    "<h1 style='text-align:center; color:#EAF2FF;'>Funding Stress Index</h1>",
    unsafe_allow_html=True,
)


BINANCE_FAPI = "https://fapi.binance.com"
BYBIT_API = "https://api.bybit.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}


class ApiError(RuntimeError):
    pass


def _get_json(url: str, params: dict | None = None) -> dict | list:
    r = requests.get(url, params=params, timeout=10, headers=HEADERS)
    r.raise_for_status()
    return r.json()


@dataclass(frozen=True)
class FundingSeries:
    exchange: str
    symbol: str
    df: pd.DataFrame  # columns: ts_utc, funding_pct
    last_price: float | None


def _parse_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


@st.cache_data(ttl=60)
def fetch_funding_series(exchange: str, symbol: str, points: int) -> FundingSeries:
    symbol = symbol.strip().upper()
    points = int(points)
    points = max(20, min(1000, points))

    if exchange == "Binance (USD-M)":
        rows = _get_json(f"{BINANCE_FAPI}/fapi/v1/fundingRate", {"symbol": symbol, "limit": points})
        if not isinstance(rows, list) or not rows:
            raise ApiError("No funding history returned.")

        df = pd.DataFrame(rows)
        df["ts_utc"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True, errors="coerce")
        df["funding_pct"] = pd.to_numeric(df["fundingRate"], errors="coerce") * 100.0
        df = df.dropna(subset=["ts_utc", "funding_pct"]).sort_values("ts_utc")
        if df.empty:
            raise ApiError("Funding history parsed to empty dataset.")

        try:
            ticker = _get_json(f"{BINANCE_FAPI}/fapi/v1/ticker/price", {"symbol": symbol})
            last_price = _parse_float(ticker.get("price") if isinstance(ticker, dict) else None)
        except Exception:
            last_price = None

        return FundingSeries(exchange="binance_usdm", symbol=symbol, df=df[["ts_utc", "funding_pct"]], last_price=last_price)

    if exchange == "Bybit (Linear)":
        # Bybit V5: /v5/market/funding/history returns up to 200 points per request.
        need = min(points, 200)
        payload = _get_json(
            f"{BYBIT_API}/v5/market/funding/history",
            {"category": "linear", "symbol": symbol, "limit": need},
        )
        if not isinstance(payload, dict):
            raise ApiError("Unexpected response from Bybit.")
        if int(payload.get("retCode", -1)) != 0:
            raise ApiError(str(payload.get("retMsg") or "Bybit API error"))

        result = payload.get("result") or {}
        items = result.get("list")
        if not isinstance(items, list) or not items:
            raise ApiError("No funding history returned.")

        df = pd.DataFrame(items)
        df["ts_utc"] = pd.to_datetime(df["fundingRateTimestamp"], unit="ms", utc=True, errors="coerce")
        df["funding_pct"] = pd.to_numeric(df["fundingRate"], errors="coerce") * 100.0
        df = df.dropna(subset=["ts_utc", "funding_pct"]).sort_values("ts_utc")
        if df.empty:
            raise ApiError("Funding history parsed to empty dataset.")

        try:
            tickers = _get_json(
                f"{BYBIT_API}/v5/market/tickers",
                {"category": "linear", "symbol": symbol},
            )
            last_price = None
            if isinstance(tickers, dict) and int(tickers.get("retCode", -1)) == 0:
                lst = (tickers.get("result") or {}).get("list")
                if isinstance(lst, list) and lst:
                    last_price = _parse_float(lst[0].get("lastPrice"))
        except Exception:
            last_price = None

        return FundingSeries(exchange="bybit_linear", symbol=symbol, df=df[["ts_utc", "funding_pct"]], last_price=last_price)

    raise ApiError(f"Unsupported exchange: {exchange}")


def funding_zscore(series: pd.Series, window: int) -> pd.Series:
    window = int(window)
    window = max(10, min(500, window))
    mu = series.rolling(window=window, min_periods=window).mean()
    sigma = series.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mu) / sigma.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


def persistence_count(z: pd.Series, threshold: float) -> tuple[int, str]:
    threshold = float(threshold)
    threshold = max(0.0, threshold)
    z = z.dropna()
    if z.empty:
        return 0, "neutral"

    last = float(z.iloc[-1])
    if last >= threshold and threshold > 0:
        cond = z >= threshold
        side = "positive"
    elif last <= -threshold and threshold > 0:
        cond = z <= -threshold
        side = "negative"
    else:
        return 0, "neutral"

    count = 0
    for v in reversed(cond.tolist()):
        if v:
            count += 1
        else:
            break
    return count, side


def stress_score(z_last: float, persistence: int) -> float:
    # Simple: keep sign from z, grow magnitude with persistence (diminishing returns).
    return float(z_last) * (1.0 + math.log1p(max(0, int(persistence))))


left, right = st.columns([1.2, 1.0])

with left:
    exchange = st.selectbox("EXCHANGE", ["Binance (USD-M)", "Bybit (Linear)"], index=0)
with right:
    symbol = st.text_input("SYMBOL", "BTCUSDT").strip().upper()

controls = st.columns([1, 1, 1, 1])
points = int(controls[0].selectbox("HISTORY POINTS", [200, 400, 800, 1000], index=1))
window = int(controls[1].selectbox("Z-WINDOW (POINTS)", [21, 42, 84, 168], index=1))
threshold = float(controls[2].selectbox("PERSIST THRESH", [0.0, 0.5, 1.0, 1.5, 2.0], index=2))
chart_mode = controls[3].selectbox("CHART", ["Funding + Z-Score", "Funding Only"], index=0)

try:
    fs = fetch_funding_series(exchange=exchange, symbol=symbol, points=points)
except Exception as exc:
    st.error(f"Funding data unavailable: {exc}")
    st.stop()

df = fs.df.copy()
df["z"] = funding_zscore(df["funding_pct"], window=window)

if exchange == "Bybit (Linear)" and points > 200:
    st.caption("Note: Bybit funding history endpoint returns up to 200 points per request; using the latest 200.")
else:
    st.caption(f"Loaded {len(df):,} funding points.")

df_ready = df.dropna(subset=["z"]).copy()
if df_ready.empty:
    st.warning("Not enough data to compute Z-Score. Try a smaller Z-window or more history points.")
    st.stop()

last_ts = df_ready["ts_utc"].iloc[-1].to_pydatetime()
last_funding = float(df_ready["funding_pct"].iloc[-1])
last_z = float(df_ready["z"].iloc[-1])
p_count, p_side = persistence_count(df_ready["z"], threshold=threshold)
score = stress_score(last_z, p_count)

if last_z >= 0:
    crowd = "Long crowded" if abs(last_z) >= 1.5 else "Neutral"
else:
    crowd = "Short crowded" if abs(last_z) >= 1.5 else "Neutral"

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
if fs.last_price is None:
    c1.metric("PRICE", "n/a")
else:
    c1.metric("PRICE", f"${fs.last_price:,.2f}")
c2.metric("FUNDING (LAST)", f"{last_funding:.4f}%")
c3.metric("Z-SCORE", f"{last_z:.2f}")
c4.metric("PERSISTENCE", f"{p_count} ({p_side})" if threshold > 0 else "off")

d1, d2, d3, d4 = st.columns([1, 1, 1, 1])
d1.metric("STRESS SCORE", f"{score:.2f}")
d2.metric("CROWDING", crowd)
d3.metric("LAST SETTLE (UTC)", last_ts.strftime("%Y-%m-%d %H:%M"))
d4.metric("EXCHANGE", fs.exchange)

fig = make_subplots(
    rows=2 if chart_mode == "Funding + Z-Score" else 1,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.6, 0.4] if chart_mode == "Funding + Z-Score" else [1.0],
)

fig.add_trace(
    go.Bar(
        x=df["ts_utc"],
        y=df["funding_pct"],
        name="Funding (%)",
        marker_color=np.where(df["funding_pct"] >= 0, "#00FF8C", "#FF4D4D"),
        hovertemplate="%{x}<br>Funding=%{y:.4f}%<extra></extra>",
    ),
    row=1,
    col=1,
)

fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.12)", width=1), row=1, col=1)

if chart_mode == "Funding + Z-Score":
    fig.add_trace(
        go.Scatter(
            x=df_ready["ts_utc"],
            y=df_ready["z"],
            mode="lines",
            line=dict(color="#BFC9D6", width=2),
            name="Z-Score",
            hovertemplate="%{x}<br>Z=%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.12)", width=1), row=2, col=1)
    if threshold > 0:
        fig.add_hline(y=threshold, line=dict(color="rgba(0,255,140,0.40)", width=1, dash="dash"), row=2, col=1)
        fig.add_hline(y=-threshold, line=dict(color="rgba(255,77,77,0.40)", width=1, dash="dash"), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=860,
    margin=dict(l=60, r=60, t=20, b=40),
    showlegend=False,
)

fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
fig.update_yaxes(title="Funding (%)", row=1, col=1)
if chart_mode == "Funding + Z-Score":
    fig.update_yaxes(title="Z-Score", row=2, col=1)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with st.expander("How To Read This", expanded=False):
    st.markdown(
        """
- **Funding** is the periodic payment between longs and shorts on perpetual futures.
- **Z-Score** compares the latest funding to its recent distribution (window-based). Extreme positive = crowded longs; extreme negative = crowded shorts.
- **Persistence** counts how many consecutive funding periods the Z-Score stayed beyond the chosen threshold.
- **Stress Score** = `z * (1 + log(1 + persistence))` (simple composite to rank extremes).
        """.strip()
    )

st.caption(
    "Free data sources (public): Binance USD-M `fundingRate` + `ticker/price`, Bybit V5 `market/funding/history` + `market/tickers`."
)
