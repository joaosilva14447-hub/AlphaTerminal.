import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Momentum Exhaustion", layout="wide")

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

START_DATE = "2017-01-01"

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

# Core
data["roc60"] = (data["price"] / data["price"].shift(60) - 1) * 100
data["roc_mean"] = data["roc60"].rolling(365).mean()
data["roc_std"] = data["roc60"].rolling(365).std()
data["roc_z"] = (data["roc60"] - data["roc_mean"]) / data["roc_std"]
data["roc_z"] = data["roc_z"].clip(-3.5, 3.5)

# Smooth
smooth_window = 5
data["roc_z_smooth"] = data["roc_z"].rolling(smooth_window).mean()

data = data.dropna()
data = data.loc[data.index >= START_DATE]

if data.empty:
    st.error("Data unavailable for selected period.")
    st.stop()

last = data.iloc[-1]

thr = 1.8

if last["roc_z_smooth"] >= thr:
    regime = "Overbought"
elif last["roc_z_smooth"] <= -thr:
    regime = "Oversold"
else:
    regime = "Neutral"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Momentum Exhaustion</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1, 1, 1.2])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("ROC 60D", f"{last['roc60']:.2f}%")
c3.metric("STATE", regime)

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.60, 0.40],
)

# Price
fig.add_trace(
    go.Scatter(x=data.index, y=data["price"], name="Price", line=dict(color="white", width=2)),
    row=1,
    col=1,
)

# Signal line
fig.add_trace(
    go.Scatter(x=data.index, y=data["roc_z_smooth"], name="ROC Z (Smooth)", line=dict(color="#BFC9D6", width=1.6)),
    row=2,
    col=1,
)

# ===== Bands full-height =====
top_mask = data["roc_z_smooth"] >= thr
bottom_mask = data["roc_z_smooth"] <= -thr

min_days = 3
def filter_persistent(mask, min_len):
    groups = (~mask).cumsum()
    return mask & (mask.groupby(groups).transform("size") >= min_len)

top_mask = filter_persistent(top_mask, min_days)
bottom_mask = filter_persistent(bottom_mask, min_days)

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

# Bands (full-height)
add_full_bands(top_mask, "rgba(64,153,255,0.40)")    # overbought
add_full_bands(bottom_mask, "rgba(32,220,200,0.38)") # oversold

# Zero line
fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.15)", width=1), row=2, col=1)

# SD lines
def rgba(color, alpha):
    return f"rgba({color[0]},{color[1]},{color[2]},{alpha})"

up_rgb = (76,167,255)
down_rgb = (53,240,208)

alpha_3 = 0.50
alpha_2 = 0.35
alpha_1 = 0.20

for y, a in [(3, alpha_3), (2, alpha_2), (1, alpha_1)]:
    fig.add_hline(y=y, line=dict(color=rgba(up_rgb, a), width=1, dash="dash"), row=2, col=1)

for y, a in [(-1, alpha_1), (-2, alpha_2), (-3, alpha_3)]:
    fig.add_hline(y=y, line=dict(color=rgba(down_rgb, a), width=1, dash="dash"), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

tickvals = [-3, -2, -1, 0, 1, 2, 3]
ticktext = ["3", "2", "1", "0", "-1", "-2", "-3"]

fig.update_yaxes(
    title="Momentum Score",
    row=2, col=1,
    showgrid=False,
    tickvals=tickvals,
    ticktext=ticktext,
    tickfont=dict(size=12, color="#C7D0DB"),
    title_font=dict(size=13, color="#C7D0DB"),
    tickcolor="rgba(255,255,255,0.15)",
    linecolor="rgba(255,255,255,0.12)"
)
fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_xaxes(tickfont=dict(size=12, color="#C7D0DB"))

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
