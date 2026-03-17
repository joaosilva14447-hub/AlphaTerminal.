import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Official", layout="wide")

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

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=5)
        data = r.json()
        df = pd.DataFrame(data["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except Exception:
        return None

def state_from_value(value: int):
    # Precise Institutional Thresholds
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

df = get_fng_data(limit=365)

if df is not None:
    df_hist = df.sort_values("timestamp").copy()
    
    # Map attributes to each data point
    df_hist["details"] = df_hist["value"].apply(lambda v: state_from_value(int(v)))
    df_hist["state_label"] = df_hist["details"].apply(lambda x: x[0])
    df_hist["state_color"] = df_hist["details"].apply(lambda x: x[1])
    
    current_row = df_hist.iloc[-1]
    prev_val = df_hist.iloc[-2]["value"] if len(df_hist) > 1 else current_row["value"]
    
    selected_val = int(current_row["value"])
    selected_status = current_row["state_label"]
    selected_state_color = current_row["state_color"]
    selected_delta = selected_val - prev_val

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gauge logic
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=selected_val,
                title={"text": f"Current Sentiment: {selected_status}", "font": {"color": selected_state_color, "size": 24}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "white"},
                    "bar": {"color": selected_state_color},
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(0, 230, 118, 0.2)"},
                        {"range": [25, 40], "color": "rgba(0, 200, 83, 0.15)"},
                        {"range": [40, 59], "color": "rgba(245, 200, 75, 0.1)"},
                        {"range": [59, 74], "color": "rgba(255, 122, 69, 0.15)"},
                        {"range": [74, 100], "color": "rgba(255, 59, 48, 0.2)"},
                    ],
                },
            )
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta")
        st.metric(label="Score Change", value=f"{selected_val} pts", delta=selected_delta)
        
        st.markdown("---")
        history_display = df_hist.tail(7)[["timestamp", "value", "state_label"]].copy()
        history_display["timestamp"] = history_display["timestamp"].dt.strftime("%Y-%m-%d")
        history_display.columns = ["Date", "Value", "State"]
        
        st.dataframe(history_display.iloc[::-1], use_container_width=True, hide_index=True)

    st.markdown("### Historical Sentiment Trend")

    fig_hist = go.Figure()

    # 1. THE TREND LINE: Single continuous line (Institutional Gray)
    # This prevents the "Greed/Neutral" mismatch error.
    fig_hist.add_trace(
        go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="lines",
            line=dict(color="rgba(200, 200, 200, 0.3)", width=1.5),
            hoverinfo="skip", # Let markers handle the hover
            showlegend=False
        )
    )

    # 2. THE ACCURACY MARKERS: Every point colored by its OWN status
    fig_hist.add_trace(
        go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="markers",
            marker=dict(
                color=df_hist["state_color"],
                size=6,
                line=dict(width=0)
            ),
            customdata=df_hist["state_label"],
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
            name="Sentiment State"
        )
    )

    # 3. BACKGROUND ZONES
    fig_hist.add_hrect(y0=0, y1=25, fillcolor="#00E676", opacity=0.05, line_width=0)
    fig_hist.add_hrect(y0=25, y1=40, fillcolor="#00C853", opacity=0.05, line_width=0)
    fig_hist.add_hrect(y0=40, y1=59, fillcolor="#F5C84B", opacity=0.05, line_width=0)
    fig_hist.add_hrect(y0=59, y1=74, fillcolor="#FF7A45", opacity=0.05, line_width=0)
    fig_hist.add_hrect(y0=74, y1=100, fillcolor="#FF3B30", opacity=0.05, line_width=0)

    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="closest"
    )
    fig_hist.update_yaxes(range=[0, 100], showgrid=False)
    fig_hist.update_xaxes(showgrid=False)

    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("Connection Error: API Unreachable.")
