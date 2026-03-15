import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Derivatives Monitor", layout="wide")

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


API_SPOT = "https://api.binance.com"
API_FUTURES = "https://fapi.binance.com"


def get_json(url, params=None):
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120)
def fetch_derivatives(symbol="BTCUSDT"):
    spot = float(get_json(f"{API_SPOT}/api/v3/ticker/price", {"symbol": symbol})["price"])
    premium = get_json(f"{API_FUTURES}/fapi/v1/premiumIndex", {"symbol": symbol})
    mark = float(premium["markPrice"])
    funding = float(premium["lastFundingRate"]) * 100
    basis = (mark - spot) / spot * 100

    funding_hist = get_json(f"{API_FUTURES}/fapi/v1/fundingRate", {"symbol": symbol, "limit": 200})
    funding_df = pd.DataFrame(funding_hist)
    if not funding_df.empty:
        funding_df["fundingTime"] = pd.to_datetime(funding_df["fundingTime"], unit="ms")
        funding_df["fundingRate"] = pd.to_numeric(funding_df["fundingRate"]) * 100
        funding_df = funding_df.sort_values("fundingTime")
    funding_avg_7d = funding_df["fundingRate"].tail(21).mean() if not funding_df.empty else np.nan

    oi_now = float(get_json(f"{API_FUTURES}/fapi/v1/openInterest", {"symbol": symbol})["openInterest"])
    oi_hist = get_json(
        f"{API_FUTURES}/futures/data/openInterestHist",
        {"symbol": symbol, "period": "1d", "limit": 30},
    )
    oi_df = pd.DataFrame(oi_hist)
    if not oi_df.empty:
        oi_df["timestamp"] = pd.to_datetime(oi_df["timestamp"], unit="ms")
        oi_df["sumOpenInterest"] = pd.to_numeric(oi_df["sumOpenInterest"])
        oi_df = oi_df.sort_values("timestamp")
    oi_change = (
        (oi_now - oi_df["sumOpenInterest"].iloc[-1]) / oi_df["sumOpenInterest"].iloc[-1] * 100
        if not oi_df.empty
        else np.nan
    )

    return {
        "spot": spot,
        "mark": mark,
        "basis": basis,
        "funding": funding,
        "funding_avg_7d": funding_avg_7d,
        "funding_df": funding_df,
        "open_interest": oi_now,
        "open_interest_change": oi_change,
        "oi_df": oi_df,
    }


try:
    data = fetch_derivatives()
except Exception as exc:
    st.error(f"Derivatives data unavailable: {exc}")
    st.stop()

st.markdown(
    "<h1 style='text-align:center; color:#EAF2FF;'>Derivatives Monitor</h1>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
c1.metric("SPOT PRICE", f"${data['spot']:,.2f}")
c2.metric("FUNDING (LAST)", f"{data['funding']:.4f}%")
c3.metric("FUNDING (7D AVG)", f"{data['funding_avg_7d']:.4f}%")
c4.metric("BASIS", f"{data['basis']:.3f}%")

c5, c6 = st.columns([1, 1])
c5.metric("OPEN INTEREST", f"{data['open_interest']:,.0f}")
c6.metric("OI 30D CHANGE", f"{data['open_interest_change']:.2f}%")

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.06,
    row_heights=[0.6, 0.4],
)

if not data["oi_df"].empty:
    fig.add_trace(
        go.Scatter(
            x=data["oi_df"]["timestamp"],
            y=data["oi_df"]["sumOpenInterest"],
            name="Open Interest",
            line=dict(color="#00FBFF", width=1.8),
        ),
        row=1,
        col=1,
    )

if not data["funding_df"].empty:
    fig.add_trace(
        go.Bar(
            x=data["funding_df"]["fundingTime"],
            y=data["funding_df"]["fundingRate"],
            name="Funding Rate",
            marker_color="#3D5AFE",
        ),
        row=2,
        col=1,
    )

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0F0F0F",
    plot_bgcolor="#0F0F0F",
    height=900,
    margin=dict(l=60, r=60, t=40, b=40),
    showlegend=False,
)

fig.update_yaxes(title="Open Interest", row=1, col=1, showgrid=False)
fig.update_yaxes(title="Funding (%)", row=2, col=1, showgrid=False)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
