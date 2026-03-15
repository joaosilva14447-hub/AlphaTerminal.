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

data["roc60"] = (data["price"] / data["price"].shift(60) - 1) * 100
data["roc_mean"] = data["roc60"].rolling(365).mean()
data["roc_std"] = data["roc60"].rolling(365).std()
data["roc_z"] = (data["roc60"] - data["roc_mean"]) / data["roc_std"]
data["roc_z"] = data["roc_z"].clip(-3.5, 3.5)
data = data.dropna()

last = data.iloc[-1]

if last["roc_z"] >= 2:
    regime = "Overheated"
elif last["roc_z"] <= -2:
    regime = "Capitulation"
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
    vertical_spacing=0.06,
    row_heights=[0.65, 0.35],
)

fig.add_trace(
    go.Scatter(x=data.index, y=data["price"], name="Price", line=dict(color="white", width=2)),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=data["roc_z"], name="ROC Z", line=dict(color="#00FBFF", width=1.5)),
    row=2,
    col=1,
)
fig.add_hline(y=2, line=dict(color="#3D5AFE", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=-2, line=dict(color="#3D5AFE", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.15)", width=1), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(title="ROC Z-Score", row=2, col=1, showgrid=False)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
