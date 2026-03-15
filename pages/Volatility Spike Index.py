import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Volatility Spike Index", layout="wide")

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
    return data

data = fetch_btc_history()

if data.empty:
    st.error("Data unavailable.")
    st.stop()

# ===== VIX-style volatility spike logic =====
data["ret"] = np.log(data["price"] / data["price"].shift(1))

# Realized vol (30d)
data["vol30"] = data["ret"].rolling(30).std() * np.sqrt(365) * 100

# Z-score of vol (spike score)
vol_mean = data["vol30"].rolling(365).mean()
vol_std = data["vol30"].rolling(365).std()
data["vol_z"] = (data["vol30"] - vol_mean) / vol_std
data["vol_z"] = data["vol_z"].clip(-4, 4)

data = data.dropna()
data = data.loc[data.index >= START_DATE]

last = data.iloc[-1]

# Thresholds
thr = 2.2
compress_thr = -1.8
min_days_spike = 2
min_days_compress = 10

def filter_persistent(mask, min_len):
    groups = (~mask).cumsum()
    return mask & (mask.groupby(groups).transform("size") >= min_len)

spike_raw = data["vol_z"] >= thr
spike_persist = filter_persistent(spike_raw, min_days_spike)

spike_up = spike_persist & (data["ret"] > 0)
spike_down = spike_persist & (data["ret"] <= 0)

compress_raw = data["vol_z"] <= compress_thr
compress_mask = filter_persistent(compress_raw, min_days_compress)

# Regime + line color
signal_color = "#52F1FF"
if last["vol_z"] >= thr:
    if last["ret"] > 0:
        regime = "Spike Up"
        signal_color = "#4CA7FF"
    else:
        regime = "Spike Down"
        signal_color = "#35F0D0"
elif last["vol_z"] <= compress_thr:
    regime = "Compression"
else:
    regime = "Normal"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Volatility Spike Index</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns([1, 1, 1.1, 1.1])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("REALIZED VOL (30d)", f"{last['vol30']:.2f}%")
c3.metric("SPIKE SCORE (Z)", f"{last['vol_z']:.2f}")
c4.metric("REGIME", regime)

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=[0.65, 0.35],
)

# Price
fig.add_trace(
    go.Scatter(x=data.index, y=data["price"], name="Price", line=dict(color="white", width=2)),
    row=1, col=1
)

# Vol spike score
fig.add_trace(
    go.Scatter(x=data.index, y=data["vol_z"], name="Spike Score", line=dict(color=signal_color, width=1.9)),
    row=2, col=1
)

# ===== Full-height bands =====
def add_full_bands(mask, color, opacity=0.26):
    in_band = False
    start = None
    for dt, flag in zip(data.index, mask):
        if flag and not in_band:
            start = dt
            in_band = True
        elif not flag and in_band:
            fig.add_shape(
                type="rect",
                x0=start, x1=dt,
                y0=0, y1=1,
                xref="x", yref="paper",
                fillcolor=color, opacity=opacity,
                line_width=0, layer="below"
            )
            in_band = False
    if in_band:
        fig.add_shape(
            type="rect",
            x0=start, x1=data.index[-1],
            y0=0, y1=1,
            xref="x", yref="paper",
            fillcolor=color, opacity=opacity,
            line_width=0, layer="below"
        )

# Blue full-band (spike up)
add_full_bands(spike_up, "rgba(64,153,255,0.32)")

# Aqua full-band (spike down)
add_full_bands(spike_down, "rgba(32,220,200,0.30)")

# Aqua full-band (compression)
add_full_bands(compress_mask, "rgba(32,220,200,0.26)")

# Trigger lines
fig.add_hline(y=thr, line=dict(color="rgba(255,255,255,0.20)", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=compress_thr, line=dict(color="rgba(90,130,200,0.35)", width=1, dash="dot"), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(title="Vol Spike Score (Z)", row=2, col=1, showgrid=False)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
