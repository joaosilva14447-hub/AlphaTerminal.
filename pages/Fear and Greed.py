import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=5)
        data = r.json()
        df = pd.DataFrame(data["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except:
        return None

# Helper to get color based on 5 phases
def get_sentiment_color(val):
    if val <= 25: return "#FF4B4B"          # Extreme Fear (AlphaRed)
    if val <= 45: return "rgba(255, 75, 75, 0.6)" # Fear
    if val <= 55: return "#FACC15"          # Neutral (Yellow/Gold)
    if val <= 75: return "rgba(0, 229, 255, 0.6)" # Greed
    return "#00E5FF"                        # Extreme Greed (Aqua)

df = get_fng_data(limit=365)

if df is not None:
    current_val = df.iloc[0]["value"]
    current_status = df.iloc[0]["value_classification"]
    current_color = get_sentiment_color(current_val)
    prev_val = df.iloc[1]["value"] if len(df) > 1 else current_val
    delta = current_val - prev_val

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 1. Gauge Chart with 5 Defined Steps
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_val,
            title={"text": f"Current Sentiment: {current_status}", "font": {"color": current_color, "size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white", "tickwidth": 2},
                "bar": {"color": "white", "thickness": 0.25},
                "bgcolor": "rgba(255,255,255,0.05)",
                "steps": [
                    {"range": [0, 25], "color": "#FF4B4B"},
                    {"range": [25, 45], "color": "rgba(255, 75, 75, 0.4)"},
                    {"range": [45, 55], "color": "#FACC15"},
                    {"range": [55, 75], "color": "rgba(0, 229, 255, 0.4)"},
                    {"range": [75, 100], "color": "#00E5FF"},
                ],
            },
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Change vs Yesterday", value=f"{current_val} pts", delta=delta)
        st.markdown("---")
        st.markdown("### Last 7 Days")
        
        history_display = df[["timestamp", "value", "value_classification"]].head(7).copy()
        history_display.columns = ["Date", "Value", "Classification"]
        st.dataframe(history_display, use_container_width=True, hide_index=True)

    # 2. Historical Chart with Multi-Color Sentiment Line
    st.markdown("---")
    st.markdown("### Historical Sentiment Spectrum")
    
    df_hist = df.sort_values("timestamp")
    
    fig_hist = go.Figure()

    # Create segments to color the line dynamically
    for i in range(len(df_hist) - 1):
        x_seg = df_hist["timestamp"].iloc[i:i+2]
        y_seg = df_hist["value"].iloc[i:i+2]
        # Color based on the start of the segment
        seg_color = get_sentiment_color(y_seg.iloc[0])
        
        fig_hist.add_trace(go.Scatter(
            x=x_seg, y=y_seg, mode="lines",
            line=dict(color=seg_color, width=2.5),
            showlegend=False, hoverinfo='none'
        ))

    # Reference Background Zones
    fig_hist.add_hrect(y0=0, y1=25, fillcolor="#FF4B4B", opacity=0.08, line_width=0)
    fig_hist.add_hrect(y0=75, y1=100, fillcolor="#00E5FF", opacity=0.08, line_width=0)

    fig_hist.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=450,
        margin=dict(l=40, r=20, t=20, b=40),
        yaxis=dict(range=[0, 100], gridcolor="rgba(255,255,255,0.05)")
    )
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("API Connection Failed")

st.caption("Alpha Terminal | Dynamic Sentiment Engine")
