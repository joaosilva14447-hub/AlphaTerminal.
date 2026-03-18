import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots


st.set_page_config(page_title="Perp-Spot Basis Index", layout="wide")

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
    "<h1 style='text-align:center; color:#EAF2FF;'>Perp-Spot Basis Index</h1>",
    unsafe_allow_html=True,
)


BINANCE_SPOT = "https://api.binance.com"
BINANCE_FUTURES = "https://fapi.binance.com"
BYBIT_API = "https://api.bybit.com"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TIMEFRAME_TO_DAYS = {
    "5m": 5 / (60 * 24),
    "15m": 15 / (60 * 24),
    "30m": 30 / (60 * 24),
    "1h": 1 / 24,
    "2h": 2 / 24,
    "4h": 4 / 24,
    "6h": 6 / 24,
    "12h": 12 / 24,
    "1d": 1.0,
}


def _get_json(url: str, params: dict | None = None) -> dict | list:
    r = requests.get(url, params=params, timeout=12, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def _kline_frame(rows: list, close_idx: int = 4, ts_idx: int = 0) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["ts_utc"] = pd.to_datetime(df.iloc[:, ts_idx], unit="ms", utc=True, errors="coerce")
    df["close"] = pd.to_numeric(df.iloc[:, close_idx], errors="coerce")
    return df.dropna(subset=["ts_utc", "close"])[["ts_utc", "close"]].sort_values("ts_utc")


def _periods_per_year(interval: str) -> float:
    days = TIMEFRAME_TO_DAYS.get(interval, 1 / 24)
    return 365.0 / days if days > 0 else 365.0


def _basis_state(basis_pct: float, z_score: float) -> tuple[str, str]:
    if basis_pct >= 0.75 and z_score >= 1.5:
        return "Leverage Overheated", "#FF4D4D"
    if basis_pct >= 0.20 and z_score >= 0.5:
        return "Carry Rich", "#FF9F43"
    if basis_pct <= -0.20 and z_score <= -0.5:
        return "Backwardation", "#00E5FF"
    return "Balanced", "#C7D0DB"


@st.cache_data(ttl=120)
def fetch_basis_series(exchange: str, symbol: str, interval: str, limit: int) -> pd.DataFrame:
    symbol = symbol.strip().upper()
    limit = max(50, min(500, int(limit)))

    if exchange == "Binance":
        spot_rows = _get_json(
            f"{BINANCE_SPOT}/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        perp_rows = _get_json(
            f"{BINANCE_FUTURES}/fapi/v1/markPriceKlines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        if not isinstance(spot_rows, list) or not isinstance(perp_rows, list):
            raise RuntimeError("Unexpected Binance response.")

        spot_df = _kline_frame(spot_rows)
        perp_df = _kline_frame(perp_rows)

    elif exchange == "Bybit":
        bybit_interval = {"5m": "5", "15m": "15", "30m": "30", "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720", "1d": "D"}.get(interval, "60")

        spot_payload = _get_json(
            f"{BYBIT_API}/v5/market/kline",
            {"category": "spot", "symbol": symbol, "interval": bybit_interval, "limit": limit},
        )
        perp_payload = _get_json(
            f"{BYBIT_API}/v5/market/mark-price-kline",
            {"category": "linear", "symbol": symbol, "interval": bybit_interval, "limit": limit},
        )

        if not isinstance(spot_payload, dict) or not isinstance(perp_payload, dict):
            raise RuntimeError("Unexpected Bybit response.")
        if int(spot_payload.get("retCode", -1)) != 0:
            raise RuntimeError(str(spot_payload.get("retMsg") or "Bybit spot error"))
        if int(perp_payload.get("retCode", -1)) != 0:
            raise RuntimeError(str(perp_payload.get("retMsg") or "Bybit perp error"))

        spot_rows = (spot_payload.get("result") or {}).get("list") or []
        perp_rows = (perp_payload.get("result") or {}).get("list") or []
        if not isinstance(spot_rows, list) or not isinstance(perp_rows, list):
            raise RuntimeError("No Bybit kline data returned.")

        spot_df = _kline_frame(spot_rows, close_idx=4, ts_idx=0)
        perp_df = _kline_frame(perp_rows, close_idx=4, ts_idx=0)
    else:
        raise RuntimeError(f"Unsupported exchange: {exchange}")

    df = pd.merge(
        spot_df.rename(columns={"close": "spot_close"}),
        perp_df.rename(columns={"close": "perp_close"}),
        on="ts_utc",
        how="inner",
    )
    if df.empty:
        raise RuntimeError("No overlapping spot/perp timestamps.")

    df["basis_pct"] = (df["perp_close"] - df["spot_close"]) / df["spot_close"] * 100.0
    annualizer = _periods_per_year(interval)
    df["annualized_basis_pct"] = df["basis_pct"] * annualizer

    return df.sort_values("ts_utc").reset_index(drop=True)


def basis_zscore(series: pd.Series, window: int) -> pd.Series:
    window = max(20, min(250, int(window)))
    mean = series.rolling(window=window, min_periods=window).mean()
    std = series.rolling(window=window, min_periods=window).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan)


left, right = st.columns([1, 1])
with left:
    exchange = st.selectbox("EXCHANGE", ["Binance", "Bybit"], index=0)
with right:
    symbol = st.text_input("SYMBOL", "BTCUSDT").strip().upper()

controls = st.columns([1, 1, 1, 1])
interval = controls[0].selectbox("TIMEFRAME", ["5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"], index=3)
limit = int(controls[1].selectbox("HISTORY POINTS", [100, 200, 300, 500], index=1))
z_window = int(controls[2].selectbox("Z-WINDOW", [21, 42, 84, 126], index=1))
chart_mode = controls[3].selectbox("CHART", ["Basis + Z-Score", "Spot vs Perp"], index=0)

try:
    df = fetch_basis_series(exchange=exchange, symbol=symbol, interval=interval, limit=limit)
except Exception as exc:
    st.error(f"Basis data unavailable: {exc}")
    st.stop()

df["basis_z"] = basis_zscore(df["basis_pct"], z_window)
df_ready = df.dropna(subset=["basis_z"]).copy()
if df_ready.empty:
    st.warning("Not enough data to compute basis z-score. Try a smaller z-window or more history points.")
    st.stop()

last = df_ready.iloc[-1]
state_label, state_color = _basis_state(float(last["basis_pct"]), float(last["basis_z"]))

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
c1.metric("SPOT", f"${last['spot_close']:,.2f}")
c2.metric("PERP", f"${last['perp_close']:,.2f}")
c3.metric("BASIS", f"{last['basis_pct']:.3f}%")
c4.metric("ANNUALIZED", f"{last['annualized_basis_pct']:.2f}%")

d1, d2, d3 = st.columns([1, 1, 1.2])
d1.metric("Z-SCORE", f"{last['basis_z']:.2f}")
d2.metric("EXCHANGE", exchange)
d3.metric("STATE", state_label)

fig = make_subplots(
    rows=2 if chart_mode == "Basis + Z-Score" else 1,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.6, 0.4] if chart_mode == "Basis + Z-Score" else [1.0],
)

if chart_mode == "Spot vs Perp":
    fig.add_trace(
        go.Scatter(
            x=df["ts_utc"],
            y=df["spot_close"],
            mode="lines",
            line=dict(color="#C7D0DB", width=2),
            name="Spot",
            hovertemplate="%{x}<br>Spot=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["ts_utc"],
            y=df["perp_close"],
            mode="lines",
            line=dict(color="#00E5FF", width=2),
            name="Perp",
            hovertemplate="%{x}<br>Perp=%{y:,.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
else:
    fig.add_trace(
        go.Scatter(
            x=df["ts_utc"],
            y=df["basis_pct"],
            mode="lines",
            line=dict(color=state_color, width=2.5),
            name="Basis (%)",
            hovertemplate="%{x}<br>Basis=%{y:.3f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[last["ts_utc"]],
            y=[last["basis_pct"]],
            mode="markers",
            marker=dict(color=state_color, size=10, symbol="circle"),
            showlegend=False,
            hovertemplate="%{x}<br>Basis=%{y:.3f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.12)", width=1), row=1, col=1)

    fig.add_trace(
        go.Scatter(
            x=df_ready["ts_utc"],
            y=df_ready["basis_z"],
            mode="lines",
            line=dict(color="#BFC9D6", width=2),
            name="Basis Z",
            hovertemplate="%{x}<br>Z=%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.12)", width=1), row=2, col=1)
    fig.add_hline(y=1.5, line=dict(color="rgba(255,77,77,0.35)", width=1, dash="dash"), row=2, col=1)
    fig.add_hline(y=-1.5, line=dict(color="rgba(0,229,255,0.35)", width=1, dash="dash"), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=780,
    margin=dict(l=60, r=60, t=20, b=40),
    showlegend=chart_mode == "Spot vs Perp",
)

fig.update_xaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
fig.update_yaxes(showgrid=False, tickfont=dict(size=11, color="#C7D0DB"))
if chart_mode == "Basis + Z-Score":
    fig.update_yaxes(title="Basis (%)", row=1, col=1)
    fig.update_yaxes(title="Z-Score", row=2, col=1)
else:
    fig.update_yaxes(title="Price", row=1, col=1)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with st.expander("How To Read This", expanded=False):
    st.markdown(
        """
- **Basis** = difference between perpetual and spot price, in percent.
- **Positive basis** means perp trades above spot, usually reflecting leverage demand.
- **Negative basis** means backwardation, often associated with stress or forced positioning.
- **Annualized basis** helps compare basis across timeframes.
- **Basis Z-Score** shows when the current spread is statistically stretched versus its recent history.
        """.strip()
    )

st.caption(
    "Free public data sources: Binance spot `klines` + USD-M `markPriceKlines`, "
    "Bybit spot `market/kline` + linear `mark-price-kline`."
)
