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

@st.cache_data(ttl=3600)  # 1-hour cache
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
    """
    Strict mapping logic:
    0-25: Extreme Fear (#00E676)
    26-40: Fear (#00C853)
    41-59: Neutral (#F5C84B)
    60-74: Greed (#FF7A45)
    75-100: Extreme Greed (#FF3B30)
    """
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
    # Data Processing
    df_hist = df.sort_values("timestamp").copy()
    
    # Apply strict logic to all rows
    df_hist["details"] = df_hist["value"].apply(lambda v: state_from_value(int(v)))
    df_hist["state_label"] = df_hist["details"].apply(lambda x: x[0])
    df_hist["state_color"] = df_hist["details"].apply(lambda x: x[1])
    df_hist["date_label"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d")

    # Current Selection (Most recent)
    current_row = df_hist.iloc[-1]
    prev_val = df_hist.iloc[-2]["value"] if len(df_hist) > 1 else current_row["value"]
    
    selected_val = int(current_row["value"])
    selected_status = current_row["state_label"]
    selected_state_color = current_row["state_color"]
    selected_label = current_row["date_label"]
    selected_delta = selected_val - prev_val

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=selected_val,
                title={
                    "text": f"Sentiment on {selected_label}: {selected_status}",
                    "font": {"color": selected_state_color, "size": 24},
                },
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "white", "tickvals": [0, 25, 40, 60, 75, 100]},
                    "bar": {"color": selected_state_color},
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 25.5], "color": "rgba(0, 230, 118, 0.22)"},
                        {"range": [25.5, 40.5], "color": "rgba(0, 200, 83, 0.20)"},
                        {"range": [40.5, 59.5], "color": "rgba(245, 200, 75, 0.18)"},
                        {"range": [59.5, 74.5], "color": "rgba(255, 122, 69, 0.20)"},
                        {"range": [74.5, 100], "color": "rgba(255, 59, 48, 0.22)"},
                    ],
                },
            )
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Change vs Previous", value=f"{selected_val} pts", delta=selected_delta)
        st.caption(f"Status: {selected_status} ({selected_delta:+} pts vs yesterday)")

        st.markdown("---")
        st.markdown("### Last 7 Days")

        history_display = df_hist.tail(7)[["date_label", "value", "state_label"]].copy()
        history_display.columns = ["Date", "Value", "Classification"]
        history_display = history_display.iloc[::-1] # Newest first

        def highlight_fng(val):
            _, color = state_from_value(int(val))
            return f"color: {color}; font-weight: bold"

        st.dataframe(
            history_display.style.applymap(highlight_fng, subset=["Value"]),
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("### Sentiment Historical (Last Months)")

    fig_hist = go.Figure()

    # Optimized line: Uses a single trace with point-by-point data to ensure hover accuracy
    fig_hist.add_trace(
        go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="lines",
            line=dict(color="#888888", width=1.5),
            name="Index",
            hoverinfo="none",
            showlegend=False
        )
    )

    # Invisible scatter for perfect Hover labels
    fig_hist.add_trace(
        go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="markers",
            marker=dict(
                color=df_hist["state_color"],
                size=4,
                opacity=0.8
            ),
            customdata=df_hist["state_label"],
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
            name="Daily State"
        )
    )

    # Background Zones (Matching your exact logic)
    fig_hist.add_hrect(y0=0, y1=25, fillcolor="#00E676", opacity=0.1, line_width=0)
    fig_hist.add_hrect(y0=25, y1=40, fillcolor="#00C853", opacity=0.08, line_width=0)
    fig_hist.add_hrect(y0=40, y1=59, fillcolor="#F5C84B", opacity=0.06, line_width=0)
    fig_hist.add_hrect(y0=59, y1=74, fillcolor="#FF7A45", opacity=0.08, line_width=0)
    fig_hist.add_hrect(y0=74, y1=100, fillcolor="#FF3B30", opacity=0.1, line_width=0)

    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=40, r=20, t=20, b=40),
        showlegend=False,
    )
    fig_hist.update_yaxes(range=[0, 100], showgrid=False, tickfont=dict(color="#C7D0DB"))
    fig_hist.update_xaxes(showgrid=False, tickfont=dict(color="#C7D0DB"))

    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("Failed to connect to Sentiment API. Check your connection.")

st.markdown("---")
st.caption("Alpha Terminal Institutional Data - Updates every 24h via Alternative.me API")
