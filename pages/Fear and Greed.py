import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Official | Institutional Terminal", layout="wide")

# Custom CSS for Institutional Styling and Perfectly Uniform Legend
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
    [data-testid="stMetricValue"] { font-size: 28px; color: #FFFFFF; }
    
    /* Legend Styles - Uniform height for all 5 lines */
    .legend-container {
        padding-top: 60px;
        padding-left: 20px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        color: #C7D0DB;
    }
    .legend-line {
        width: 30px;
        height: 2.5px;
        margin-right: 12px;
        border-radius: 1px;
    }
    /* Table Styling */
    .stDataFrame { background-color: #161616; border-radius: 6px; }
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
    # Professional Palette: Aqua/AlphaBlue for Fear and Red/AlphaRed for Greed
    if value <= 25:
        return "Extreme Fear", "#00FFAA"  # Aqua
    elif value <= 45:
        return "Fear", "#00CC88"          # Deep Aqua
    elif value <= 55:
        return "Neutral", "#FFCC00"       # Gold
    elif value <= 75:
        return "Greed", "#FF6600"         # Orange
    else:
        return "Extreme Greed", "#FF0000" # Red

df_hist = get_fng_data(limit=365)

if df_hist is not None:
    # Data Preparation
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

    st.title("Sentiment Terminal | Alpha-V6")

    # --- TOP ROW: GAUGE & METRICS ---
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=selected_val,
            title={"text": f"{current_row['date_label']} | {selected_status}", "font": {"color": selected_color, "size": 22}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white", "tickwidth": 1},
                "bar": {"color": selected_color},
                "bgcolor": "rgba(255,255,255,0.05)",
                "steps": [
                    {"range": [0, 25], "color": "rgba(0, 255, 170, 0.1)"},
                    {"range": [25, 45], "color": "rgba(0, 204, 136, 0.08)"},
                    {"range": [45, 55], "color": "rgba(255, 204, 0, 0.05)"},
                    {"range": [55, 75], "color": "rgba(255, 102, 0, 0.08)"},
                    {"range": [75, 100], "color": "rgba(255, 0, 0, 0.1)"},
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.75,
                    "value": selected_val
                }
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400, margin=dict(t=80, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta")
        st.metric(label="Current Score", value=f"{selected_val} pts", delta=selected_delta)
        st.markdown("---")
        
        # Recent History Table with logic consistent with previous indicators
        history_table = df_hist.tail(7)[["date_label", "value", "state_label"]].copy()
        history_table.columns = ["Date", "Score", "State"]
        
        st.dataframe(
            history_table.iloc[::-1].style.apply(
                lambda x: [f"color: {state_from_value(int(v))[1]}" for v in x] if x.name == "Score" else ["" for _ in x], 
                axis=0
            ), 
            use_container_width=True, 
            hide_index=True
        )

    # --- BOTTOM ROW: HISTORICAL CHART ---
    st.markdown("---")
    st.markdown("### Historical Sentiment Analysis")

    chart_col, legend_col = st.columns([8, 1])

    with chart_col:
        fig_hist = go.Figure()

        # Fix: Segmented line drawing to avoid the ValueError with single-trace arrays
        # This creates the multi-color effect safely
        for i in range(1, len(df_hist)):
            fig_hist.add_trace(go.Scatter(
                x=df_hist["timestamp"].iloc[i-1:i+1], 
                y=df_hist["value"].iloc[i-1:i+1],
                mode="lines", 
                line=dict(color=df_hist["state_color"].iloc[i], width=2),
                hoverinfo="skip", 
                showlegend=False
            ))

        # Tooltip and Interaction layer
        fig_hist.add_trace(go.Scatter(
            x=df_hist["timestamp"], y=df_hist["value"],
            mode="markers", marker=dict(color="rgba(0,0,0,0)", size=1),
            customdata=df_hist["state_label"],
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
            name="Sentiment"
        ))

        # Current Signal Highlight
        fig_hist.add_trace(go.Scatter(
            x=[current_row["timestamp"]],
            y=[current_row["value"]],
            mode="markers",
            marker=dict(color=selected_color, size=12, line=dict(width=2, color='white')),
            showlegend=False,
            hovertemplate="Current: %{y}<extra></extra>"
        ))
        
        # Background Zones (Brightness optimized for extremes)
        zones = [
            (0, 25, "#00FFAA", 0.15),
            (25, 45, "#00CC88", 0.05),
            (45, 55, "#FFCC00", 0.05),
            (55, 75, "#FF6600", 0.05),
            (75, 100, "#FF0000", 0.15)
        ]
        
        for y0, y1, color, op in zones:
            fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)
        
        fig_hist.update_layout(
            template="plotly_dark", 
            paper_bgcolor="rgba(0,0,0,0)", 
            plot_bgcolor="rgba(0,0,0,0)",
            height=450, 
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False, zeroline=False), 
            yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#222222", zeroline=False),
            hovermode="x unified"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with legend_col:
        st.markdown('<div class="legend-container">', unsafe_allow_html=True)
        legend_items = [
            ("Extreme Fear", "#00FFAA"),
            ("Fear", "#00CC88"),
            ("Neutral", "#FFCC00"),
            ("Greed", "#FF6600"),
            ("Extreme Greed", "#FF0000")
        ]
        for label, color in legend_items:
            st.markdown(f'''
                <div class="legend-item">
                    <div class="legend-line" style="background-color: {color};"></div>
                    {label}
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("Terminal Error: Could not fetch institutional sentiment data.")
