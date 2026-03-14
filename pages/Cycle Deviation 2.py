import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Cycle Deviation", layout="wide")

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

data["log_price"] = np.log(data["price"])
window = 350
data["mean"] = data["log_price"].rolling(window=window).mean()
data["std"] = data["log_price"].rolling(window=window).std()
data["z"] = (data["log_price"] - data["mean"]) / data["std"]
data["z"] = data["z"].clip(-3.5, 3.5)
data = data.dropna()

last = data.iloc[-1]

if last["z"] >= 2:
    state = "Overbought"
elif last["z"] <= -2:
    state = "Oversold"
else:
    state = "Neutral"

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Cycle Deviation Index</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1, 1, 1])
c1.metric("BTC PRICE", f"${last['price']:,.2f}")
c2.metric("CDI Z-SCORE", f"{last['z']:.2f} SD")
c3.metric("STATE", state)

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
    go.Scatter(x=data.index, y=data["z"], name="Z-Score", line=dict(color="#00FBFF", width=1.5)),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=[2] * len(data), line=dict(width=0), showlegend=False),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=data.index,
        y=np.where(data["z"] >= 2, data["z"], 2),
        fill="tonexty",
        fillcolor="rgba(76, 167, 255, 0.35)",
        line=dict(width=0),
        showlegend=False,
    ),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(x=data.index, y=[-2] * len(data), line=dict(width=0), showlegend=False),
    row=2,
    col=1,
)
fig.add_trace(
    go.Scatter(
        x=data.index,
        y=np.where(data["z"] <= -2, data["z"], -2),
        fill="tonexty",
        fillcolor="rgba(53, 240, 208, 0.35)",
        line=dict(width=0),
        showlegend=False,
    ),
    row=2,
    col=1,
)
fig.add_hline(y=3, line=dict(color="rgba(76, 167, 255, 0.55)", width=1, dash="dot"), row=2, col=1)
fig.add_hline(y=2, line=dict(color="rgba(76, 167, 255, 0.45)", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=1, line=dict(color="rgba(76, 167, 255, 0.25)", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.08)", width=1), row=2, col=1)
fig.add_hline(y=-1, line=dict(color="rgba(53, 240, 208, 0.25)", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=-2, line=dict(color="rgba(53, 240, 208, 0.45)", width=1, dash="dash"), row=2, col=1)
fig.add_hline(y=-3, line=dict(color="rgba(53, 240, 208, 0.55)", width=1, dash="dot"), row=2, col=1)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(title="Z-Score", row=2, col=1, showgrid=False, range=[-3.5, 3.5], tickvals=[-3, -2, -1, 0, 1, 2, 3])

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
