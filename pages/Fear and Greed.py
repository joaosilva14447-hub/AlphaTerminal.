import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- AlphaTerminal Configuration ---
st.set_page_config(page_title="AlphaTerminal | Sentiment Codex", layout="wide")

# Custom CSS for a professional dark-pool aesthetic
st.markdown(
    """
    <style>
        .main { background-color: #0F0F0F; }
        div[data-testid='stMetric'] {
            background-color: #161616;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #2A2A2A;
        }
        .stDataFrame { border: 1px solid #2A2A2A; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=10)
        data = r.json()
        df = pd.DataFrame(data["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except Exception as e:
        st.error(f"Data acquisition error: {e}")
        return None

def get_sentiment_metadata(value: int):
    """Returns classification and the professional Alpha Palette color."""
    if value < 25:
        return "Extreme Fear", "#FF3B30"  # AlphaRed
    if value < 50:
        return "Fear", "#FF7A45"
    if value < 55:
        return "Neutral", "#F5C84B"
    if value < 75:
        return "Greed", "#3CCB7F"
    return "Extreme Greed", "#00E676" # AlphaBlue/Green

# --- Data Processing ---
df = get_fng_data(limit=365)

if df is not None:
    # Latest Data Point
    current_val = int(df.iloc[0]["value"])
    current_status = str(df.iloc[0]["value_classification"])
    prev_val = int(df.iloc[1]["value"]) if len(df) > 1 else current_val
    delta_val = current_val - prev_val
    
    current_label, current_color = get_sentiment_metadata(current_val)
    latest_date = df.iloc[0]["timestamp"].strftime("%Y-%m-%d")

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # --- Custom Needle Logic (Trigonometry) ---
        # Map 0-100 to 180-0 degrees: theta = 180 - (value * 1.8)
        theta = 180 - (current_val * 1.8)
        rad = np.deg2rad(theta)
        
        # Coordinates for the needle tip
        # x = center_x + radius * cos(theta), y = center_y + radius * sin(theta)
        x_tip = 0.5 + 0.3 * np.cos(rad)
        y_tip = 0.35 + 0.35 * np.sin(rad)
        
        fig = go.Figure()

        # 1. Background Gauge (Static Steps)
        fig.add_trace(go.Indicator(
            mode="gauge",
            value=current_val,
            domain={'x': [0, 1], 'y': [0, 1]},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white", 'nticks': 6},
                'bar': {'color': "rgba(0,0,0,0)"}, # Invisible bar to let the needle shine
                'bgcolor': "rgba(0,0,0,0)",
                'steps': [
                    {"range": [0, 25], "color": "rgba(255, 59, 48, 0.15)"},
                    {"range": [25, 50], "color": "rgba(255, 122, 69, 0.12)"},
                    {"range": [50, 55], "color": "rgba(245, 200, 75, 0.10)"},
                    {"range": [55, 75], "color": "rgba(60, 203, 127, 0.12)"},
                    {"range": [75, 100], "color": "rgba(0, 230, 118, 0.15)"},
                ],
            }
        ))

        # 2. The Needle (Manual Shape)
        fig.update_layout(
            shapes=[
                # The "Needle" Line
                dict(
                    type='line',
                    x0=0.5, y0=0.35,
                    x1=x_tip, y1=y_tip,
                    line=dict(color=current_color, width=5)
                ),
                # The Central Pivot (Mechanical Look)
                dict(
                    type='circle',
                    x0=0.47, y0=0.32, x1=0.53, y1=0.38,
                    fillcolor='white',
                    line=dict(color=current_color, width=3),
                )
            ],
            annotations=[
                dict(
                    x=0.5, y=0.15,
                    text=f"<span style='font-size:48px; font-weight:bold;'>{current_val}</span><br><span style='font-size:18px; color:{current_color};'>{current_label}</span>",
                    showarrow=False,
                    align="center",
                    font=dict(color="white")
                )
            ],
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=500,
            margin=dict(t=50, b=0, l=50, r=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Market Sentiment Delta")
        st.metric(label=f"Value on {latest_date}", value=f"{current_val} pts", delta=f"{delta_val} vs Yesterday")
        
        st.markdown("---")
        st.markdown("### Weekly Order-Flow Context")
        
        history = df[["timestamp", "value", "value_classification"]].head(7).copy()
        history.columns = ["Date", "Value", "State"]
        
        def style_rows(val):
            _, color = get_sentiment_metadata(int(val))
            return f"color: {color}; font-weight: bold;"

        st.dataframe(
            history.style.map(style_rows, subset=["Value"]),
            use_container_width=True,
            hide_index=True
        )

    # --- Historical Timeline ---
    st.markdown("---")
    st.markdown("### Historical Sentiment Archetypes")
    
    df_hist = df.sort_values("timestamp")
    fig_hist = go.Figure()
    
    # Colored Area Zones
    fig_hist.add_hrect(y0=0, y1=25, fillcolor="#FF3B30", opacity=0.05, line_width=0)
    fig_hist.add_hrect(y0=75, y1=100, fillcolor="#00E676", opacity=0.05, line_width=0)

    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"],
        y=df_hist["value"],
        mode="lines",
        line=dict(color="#C7D0DB", width=1.5),
        fill='tonexty',
        fillcolor='rgba(199, 208, 219, 0.05)',
        name="Index Value"
    ))

    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        yaxis=dict(range=[0, 100], showgrid=False),
        xaxis=dict(showgrid=False)
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("Terminal offline: Unable to reach the liquidity sentiment API.")

st.caption("Alpha Terminal Institutional Data - Real-time synchronization active.")
