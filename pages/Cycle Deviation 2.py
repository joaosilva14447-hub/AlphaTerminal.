import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

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


DATA_PATH = Path(__file__).resolve().parent / "data" / "btc_history.csv"
BLOCKCHAIN_URL = "https://api.blockchain.info/charts/market-price?timespan=all&format=json"


@st.cache_data(ttl=120)
def load_local_history(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    if df.empty:
        return pd.DataFrame()
    date_col = next((c for c in df.columns if c.lower() in ("date", "time", "timestamp")), None)
    price_col = next((c for c in df.columns if c.lower() in ("close", "price", "adj close", "adj_close")), None)
    if not date_col or not price_col:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, price_col]).sort_values(date_col)
    df = df[[date_col, price_col]].rename(columns={date_col: "date", price_col: "price"})
    df = df.set_index("date")
    df.index = df.index.tz_localize(None)
    return df


@st.cache_data(ttl=3600)
def fetch_blockchain_history() -> pd.DataFrame:
    try:
        resp = requests.get(BLOCKCHAIN_URL, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return pd.DataFrame()
    values = payload.get("values", [])
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values)
    if "x" not in df.columns or "y" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["x"], unit="s", errors="coerce")
    df["price"] = pd.to_numeric(df["y"], errors="coerce")
    df = df[["date", "price"]].dropna().sort_values("date")
    df = df.set_index("date")
    df.index = df.index.tz_localize(None)
    return df


@st.cache_data(ttl=120)
def fetch_btc_history() -> pd.DataFrame:
    local = load_local_history(DATA_PATH)
    if not local.empty:
        last_date = local.index.max()
        if pd.notna(last_date):
            age_days = (pd.Timestamp.utcnow().normalize() - last_date.normalize()).days
            if age_days <= 1:
                return local

    chain = fetch_blockchain_history()
    if not chain.empty:
        try:
            DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            chain.to_csv(DATA_PATH)
        except Exception:
            pass
        return chain

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
    st.error("Data unavailable. Add a local CSV at /data/btc_history.csv or check the data source.")
    st.stop()

data["log_price"] = np.log(data["price"])
short_window = 350
long_window = 1400

data["mean_s"] = data["log_price"].rolling(window=short_window).mean()
data["std_s"] = data["log_price"].rolling(window=short_window).std()
data["mean_l"] = data["log_price"].rolling(window=long_window).mean()
data["std_l"] = data["log_price"].rolling(window=long_window).std()

data["z_s"] = (data["log_price"] - data["mean_s"]) / data["std_s"]
data["z_l"] = (data["log_price"] - data["mean_l"]) / data["std_l"]

# Blend short + long to stabilize cycle regime
data["z_raw"] = 0.7 * data["z_s"] + 0.3 * data["z_l"]

# Soft-squash: preserve shape until +/-3, then smoothly cap at +/-3.5
limit = 3.5
knee = 3.0
abs_z = data["z_raw"].abs()
data["z"] = np.where(
    abs_z <= knee,
    data["z_raw"],
    np.sign(data["z_raw"]) * (knee + (limit - knee) * np.tanh((abs_z - knee) / (limit - knee))),
)

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
    go.Scatter(x=data.index, y=data["z"], name="Z-Score", line=dict(color="#BFC9D6", width=1.6)),
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

fig.update_yaxes(title="BTC Price", type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(title="Z-Score", row=2, col=1, showgrid=False, range=[-3.5, 3.5], tickvals=[-3, -2, -1, 0, 1, 2, 3])

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
