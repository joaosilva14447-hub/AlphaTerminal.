import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Volatility Regime", layout="wide")

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

START_DATE = "2018-01-01"

@st.cache_data(ttl=120)
def fetch_btc_history():
    ticker = yf.Ticker("BTC-USD")
    df = ticker.history(period="max", interval="1d")
    if df.empty:
        return pd.DataFrame()
    try:
        live_price = ticker.fast_info.get("last_price")
        if live_price:
            df.iloc[-1, df.columns.get_loc("Close")] = live_price
    except Exception:
        pass
    data = df[["Close"]].rename(columns={"Close": "price"})
    data.index = pd.to_datetime(data.index).tz_localize(None)
    data = data.dropna()
    data = data.loc[data.index >= START_DATE]
    return data

data = fetch_btc_history()

if data.empty:
    st.error("Data unavailable.")
    st.stop()

# Volatility regime core
data["returns"] = np.log(data["price"] / data["price"].shift(1))
data["vol30"] = data["returns"].rolling(30).std() * np.sqrt(365) * 100
data["vol365"] = data["returns"].rolling(365).std() * np.sqrt(365) * 100
data["vol_ratio"] = data["vol30"] / data["vol365"]

# Trend context
data["ma200"] = data["price"].rolling(200).mean()
data["ma200_slope"] = data["ma200"].pct_change(30)

data = data.dropna()
last = data.iloc[-1]

# Regime state (keep original)
if last["vol_ratio"] >= 1.25:
    regime = "Expansion"
elif last["vol_ratio"] <= 0.8:
    regime = "Compression"
else:
    regime = "Neutral"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Volatility Regime Index</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1, 1, 1.2])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("REALIZED VOL (30d)", f"{last['vol30']:.2f}%")
c3.metric("REGIME", regime)

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.65, 0.35],
)

# Price line
fig.add_trace(
    go.Scatter(x=data.index, y=data["price"], name="Price", line=dict(color="white", width=2)),
    row=1,
    col=1,
)

# Vol ratio line
fig.add_trace(
    go.Scatter(x=data.index, y=data["vol_ratio"], name="Vol Ratio", line=dict(color="#00FBFF", width=1.5)),
    row=2,
    col=1,
)

# ===== BANDS LOGIC (EXTREME + CONTEXT) =====
top_level = 1.50
bottom_level = 0.65
min_days_top = 5
min_days_bottom = 6

trend_up = (data["price"] > data["ma200"]) & (data["ma200_slope"] > 0)
trend_down = (data["price"] < data["ma200"]) & (data["ma200_slope"] < 0)

top_mask = (data["vol_ratio"] >= top_level) & trend_up
bottom_mask = (data["vol_ratio"] <= bottom_level) & trend_down

def filter_persistent(mask, min_len):
    groups = (~mask).cumsum()
    return mask & (mask.groupby(groups).transform("size") >= min_len)

top_mask = filter_persistent(top_mask, min_days_top)
bottom_mask = filter_persistent(bottom_mask, min_days_bottom)

def add_bands(mask, color, opacity=0.25):
    in_band = False
    start = None
    for dt, flag in zip(data.index, mask):
        if flag and not in_band:
            start = dt
            in_band = True
        elif not flag and in_band:
            fig.add_vrect(
                x0=start, x1=dt,
                fillcolor=color, opacity=opacity, line_width=0,
                row="all", col=1
            )
            in_band = False
    if in_band:
        fig.add_vrect(
            x0=start, x1=data.index[-1],
            fillcolor=color, opacity=opacity, line_width=0,
            row="all", col=1
        )

# Bands (filtered by context)
add_bands(top_mask, "rgba(76, 167, 255, 0.28)")
add_bands(bottom_mask, "rgba(53, 240, 208, 0.24)")

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(title="Vol Ratio", row=2, col=1, showgrid=False)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
