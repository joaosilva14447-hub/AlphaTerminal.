import streamlit as st
import requests
import plotly.graph_objects as go

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Real-Time", layout="wide")

def get_official_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/")
        data = r.json()
        value = int(data["data"][0]["value"])
        status = data["data"][0]["value_classification"]
        return value, status
    except:
        return 50, "Neutral (API Error)"

def color_by_range(value: int) -> str:
    if value < 20:
        return "#8B0000"  # Extreme Fear
    if value < 40:
        return "#FF4B4B"  # Fear
    if value < 60:
        return "#C7D0DB"  # Neutral
    if value < 80:
        return "#00E5FF"  # Greed
    return "#00FF8C"      # Extreme Greed

value, status = get_official_fear_greed()
color = color_by_range(value)

st.title("Fear & Greed Index (Official Data)")

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=value,
    title={"text": f"Market Sentiment: {status}", "font": {"color": color}},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": "white"},
        "bar": {"color": color},
        "bgcolor": "rgba(0,0,0,0)",
        "steps": [
            {"range": [0, 20], "color": "rgba(139, 0, 0, 0.25)"},
            {"range": [20, 40], "color": "rgba(255, 75, 75, 0.25)"},
            {"range": [40, 60], "color": "rgba(199, 208, 219, 0.20)"},
            {"range": [60, 80], "color": "rgba(0, 229, 255, 0.20)"},
            {"range": [80, 100], "color": "rgba(0, 255, 140, 0.25)"},
        ],
    },
))

fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"})
st.plotly_chart(fig, use_container_width=True)

