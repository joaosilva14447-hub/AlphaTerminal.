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

# Spike detection
data["vol_roc_5d"] = data["vol_ratio"].pct_change(5)
data["spike_raw"] = (data["vol_ratio"] > 1.25) & (data["vol_roc_5d"] > 0.25)

# Cooldown
cooldown = 14
recent_spike = data["spike_raw"].rolling(cooldown).max().shift(1).fillna(0).astype(bool)
data["spike_signal"] = data["spike_raw"] & (~recent_spike)

# Classify spike context
data["spike_top"] = data["spike_signal"] & (data["price"] > data["ma200"]) & (data["ma200_slope"] > 0)
data["spike_bottom"] = data["spike_signal"] & (data["price"] < data["ma200"]) & (data["ma200_slope"] < 0)

data = data.dropna()
last = data.iloc[-1]

# Regime state
if last["vol_ratio"] >= 1.25:
    regime = "Expansion"
elif last["vol_ratio"] <= 0.8:
    regime = "Compression"
else:
    regime = "Neutral"

# Spike state
if last["spike_top"]:
    spike_state = "TOP SPIKE"
elif last["spike_bottom"]:
    spike_state = "BOTTOM SPIKE"
elif last["spike_signal"]:
    spike_state = "SPIKE"
else:
    spike_state = "None"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Volatility Regime Index</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns([1, 1, 1, 1.1])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("REALIZED VOL (30d)", f"{last['vol30']:.2f}%")
c3.metric("REGIME", regime)
c4.metric("SPIKE", spike_state)

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

# Top spike markers (red triangles)
tops = data[data["spike_top"]]
fig.add_trace(
    go.Scatter(
        x=tops.index,
        y=tops["price"],
        mode="markers",
        marker=dict(symbol="triangle-down", size=10, color="#FF4D4D"),
        name="Top Spike",
        showlegend=False,
    ),
    row=1,
    col=1,
)

# Bottom spike markers (green triangles)
bots = data[data["spike_bottom"]]
fig.add_trace(
    go.Scatter(
        x=bots.index,
        y=bots["price"],
        mode="markers",
        marker=dict(symbol="triangle-up", size=10, color="#3DFFB3"),
        name="Bottom Spike",
        showlegend=False,
    ),
    row=1,
    col=1,
)

# Vol ratio line
fig.add_trace(
    go.Scatter(x=data.index, y=data["vol_ratio"], name="Vol Ratio", line=dict(color="#00FBFF", width=1.5)),
    row=2,
    col=1,
)

# Fixed thresholds
fig.add_hline(y=1.25, line=dict(color="#3D5AFE", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=0.8, line=dict(color="#3D5AFE", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=1.0, line=dict(color="rgba(255,255,255,0.15)", width=1), row=2, col=1)

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
