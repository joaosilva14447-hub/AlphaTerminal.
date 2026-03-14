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
c1.metric("

