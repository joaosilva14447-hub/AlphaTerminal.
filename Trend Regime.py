import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Trend Regime", layout="wide")

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
    return data.dropna()


data = fetch_btc_history()

if data.empty:
    st.error("Data unavailable.")
    st.stop()

data["ma50"] = data["price"].rolling(window=50).mean()
data["ma200"] = data["price"].rolling(window=200).mean()
data["slope200"] = data["ma200"].pct_change(30) * 100
data["trend_gap"] = (data["price"] / data["ma200"] - 1) * 100
data = data.dropna()

last = data.iloc[-1]

if last["price"] > last["ma200"] and last["slope200"] > 0:
    regime = "Expansion"
elif last["price"] < last["ma200"] and last["slope200"] < 0:
    regime = "Contraction"
elif last["price"] > last["ma200"] and last["slope200"] <= 0:
    regime = "Late Cycle"
else:
    regime = "Early Cycle"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Trend Regime Index</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("MA 200", f"${last['ma200']:,.2f}")
c3.metric("TREND GAP", f"{last['trend_gap']:.2f}%")
c4.metric("REGIME", regime)

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.7, 0.3],
)

fig.add_trace(
    go.Scatter(x=data.index, y=data["price"], name="Price", line=dict(color="white", width=2)),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=data["ma50"], name="MA 50", line=dict(color="#00FBFF", width=1.2)),
    row=1,
    col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=data["ma200"], name="MA 200", line=dict(color="#3D5AFE", width=1.2)),
    row=1,
    col=1,
)

fig.add_trace(
    go.Scatter(x=data.index, y=data["slope200"], name="MA200 Slope", line=dict(color="#AAAAAA", width=1.2)),
    row=2,
    col=1,
)
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
fig.update_yaxes(title="Slope (30d %)", row=2, col=1, showgrid=False)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
