import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Official", layout="wide")

# Custom CSS for Institutional Styling and Legend
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
    .stDataFrame { background-color: #161616; border-radius: 6px; }
    
    /* Legend Styles */
    .legend-container {
        padding-top: 50px;
        padding-left: 10px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-family: sans-serif;
        font-size: 13px;
        color: #C7D0DB;
    }
    .legend-line {
        width: 25px;
        height: 2px;
        margin-right: 12px;
    }
    .legend-marker {
        width: 0; 
        height: 0; 
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 8px solid #FF3B30;
        margin-right: 12px;
        margin-left: 7px;
    }
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=5)
        data = r.json()
        df = pd.DataFrame(data["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df.sort_values("timestamp")
    except Exception:
        return None

def state_from_value(value: int):
    if value <= 25:
        return "Extreme Fear", "#00E676"
    elif value <= 40:
        return "Fear", "#00C853"
    elif value <= 59:
        return "Neutral", "#F5C84B"
    elif value <= 74:
        return "Greed", "#FF7A45"
    else:
        return "Extreme Greed", "#FF3B30"

df_hist = get_fng_data(limit=365)

if df_hist is not None:
    df_hist["details"] = df_hist["value"].apply(lambda v: state_from_value(int(v)))
    df_hist["state_label"] = df_hist["details"].apply(lambda x: x[0])
    df_hist["state_color"] = df_hist["details"].apply(lambda x: x[1])
    df_hist["date_label"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d")

    current_row = df_hist.iloc[-1]
    prev_row = df_hist.iloc[-2] if len(df_hist) > 1 else current_row
    
    selected_val = int(current_row["value"])
    selected_status = current_row["state_label"]
    selected_color = current_row["state_color"]
    selected_delta = selected_val - int(prev_row["value"])

    st.title("Fear & Greed Index | Institutional Terminal")

    col1, col2 = st.columns([2, 1])
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=selected_val,
            title={"text": f"{current_row['date_label']} | {selected_status}", "font": {"color": selected_color, "size": 22}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar": {"color": selected_color},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 25], "color": "rgba(0, 230, 118, 0.15)"},
                    {"range": [25, 40], "color": "rgba(0, 200, 83, 0.12)"},
                    {"range": [40, 59], "color": "rgba(245, 200, 75, 0.1)"},
                    {"range": [59, 74], "color": "rgba(255, 122, 69, 0.12)"},
                    {"range": [74, 100], "color": "rgba(255, 59, 48, 0.15)"},
                ],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta")
        st.metric(label="Current Score", value=f"{selected_val} pts", delta=selected_delta)
        st.markdown("---")
        history_table = df_hist.tail(7)[["date_label", "value", "state_label"]].copy()
        history_table.columns = ["Date", "Score", "Classification"]
        st.dataframe(history_table.iloc[::-1].style.applymap(lambda v: f"color: {state_from_value(int(v))[1]}", subset=["Score"]), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Historical Sentiment Analysis")

    # Layout for Chart + Legend
    chart_col, legend_col = st.columns([8, 1])

    with chart_col:
        fig_hist = go.Figure()
        for i in range(1, len(df_hist)):
            fig_hist.add_trace(go.Scatter(
                x=df_hist["timestamp"].iloc[i-1:i+1], y=df_hist["value"].iloc[i-1:i+1],
                mode="lines", line=dict(color=df_hist["state_color"].iloc[i], width=2.5),
                hoverinfo="skip", showlegend=False
            ))
        fig_hist.add_trace(go.Scatter(
            x=df_hist["timestamp"], y=df_hist["value"],
            mode="markers", marker=dict(color="rgba(0,0,0,0)", size=7),
            customdata=df_hist["state_label"],
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
            name="Sentiment"
        ))
        zones = [(0, 25, "#00E676", 0.04), (25, 40, "#00C853", 0.04), (40, 59, "#F5C84B", 0.04), (59, 74, "#FF7A45", 0.04), (74, 100, "#FF3B30", 0.04)]
        for y0, y1, color, op in zones:
            fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)
        fig_hist.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=450, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#222222"),
            hovermode="x unified"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with legend_col:
        st.markdown('<div class="legend-container">', unsafe_allow_html=True)
        legend_items = [
            ("Fear", "#00C853"),
            ("Extreme Fear", "#00E676"),
            ("Greed", "#FF7A45"),
            ("Neutral", "#F5C84B"),
            ("Extreme Greed", "#FF3B30")
        ]
        for label, color in legend_items:
            st.markdown(f'<div class="legend-item"><div class="legend-line" style="background-color: {color};"></div>{label}</div>', unsafe_allow_html=True)
        st.markdown('<div class="legend-item"><div class="legend-marker"></div>Extreme Fear</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("API connection failed.")
