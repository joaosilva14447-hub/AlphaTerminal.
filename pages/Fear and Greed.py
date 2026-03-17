import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuracao Padrao AlphaTerminal
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


@st.cache_data(ttl=3600)  # Cache de 1 hora
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
    # Official bands (Alternative.me): 0-24, 25-49, 50-54, 55-74, 75-100
    if value < 25:
        return "Extreme Fear", "#00E676"
    if value < 50:
        return "Fear", "#3CCB7F"
    if value < 55:
        return "Neutral", "#F5C84B"
    if value < 75:
        return "Greed", "#FF7A45"
    return "Extreme Greed", "#FF3B30"


df = get_fng_data(limit=365)

if df is not None:
    current_val = int(df.iloc[0]["value"])
    current_status = str(df.iloc[0]["value_classification"])
    prev_val = int(df.iloc[1]["value"]) if len(df) > 1 else current_val
    current_delta = current_val - prev_val

    df_hist = df.sort_values("timestamp").copy()
    df_hist["date_label"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d")
    df_hist["state_label"] = df_hist["value"].apply(lambda v: state_from_value(int(v))[0])
    df_hist["state_color"] = df_hist["value"].apply(lambda v: state_from_value(int(v))[1])

    # Use the most recent value as the active signal (no manual date selector)
    selected_row = df_hist.iloc[-1]
    selected_label = selected_row["date_label"]
    selected_val = current_val
    selected_status = current_status
    selected_state_label, selected_state_color = state_from_value(selected_val)
    selected_delta = current_delta

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
                    "axis": {"range": [0, 100], "tickcolor": "white"},
                    "bar": {"color": selected_state_color},
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(0, 230, 118, 0.22)"},
                        {"range": [25, 50], "color": "rgba(60, 203, 127, 0.20)"},
                        {"range": [50, 55], "color": "rgba(245, 200, 75, 0.18)"},
                        {"range": [55, 75], "color": "rgba(255, 122, 69, 0.20)"},
                        {"range": [75, 100], "color": "rgba(255, 59, 48, 0.22)"},
                    ],
                },
            )
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Change vs Previous", value=f"{selected_val} pts", delta=selected_delta)
        st.caption(f"Current: {current_val} pts ({current_status}, {current_delta:+} vs yesterday)")

        st.markdown("---")
        st.markdown("### Last 7 Days")

        history_display = df[["timestamp", "value", "value_classification"]].head(7).copy()
        history_display.columns = ["Date", "Value", "Classification"]

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
    legend_added = set()

    # Draw per-interval colored segments (no cuts)
    for i in range(1, len(df_hist)):
        label = df_hist["state_label"].iloc[i]
        color = df_hist["state_color"].iloc[i]
        seg = df_hist.iloc[i - 1 : i + 1]
        fig_hist.add_trace(
            go.Scatter(
                x=seg["timestamp"],
                y=seg["value"],
                mode="lines",
                name=label,
                line=dict(color=color, width=2.2),
                showlegend=label not in legend_added,
                hovertemplate="%{x}<br>Value=%{y}<br>State=" + label + "<extra></extra>",
            )
        )
        legend_added.add(label)

    # Keep only Extreme Greed markers
    extreme_greed = df_hist[df_hist["value"] >= 80]
    fig_hist.add_trace(
        go.Scatter(
            x=extreme_greed["timestamp"],
            y=extreme_greed["value"],
            mode="markers",
            name="Extreme Greed",
            marker=dict(color="#FF3B30", size=7, symbol="triangle-up"),
        )
    )

    fig_hist.add_hrect(y0=0, y1=25, fillcolor="rgba(0, 230, 118, 0.10)", line_width=0)
    fig_hist.add_hrect(y0=25, y1=50, fillcolor="rgba(60, 203, 127, 0.08)", line_width=0)
    fig_hist.add_hrect(y0=50, y1=55, fillcolor="rgba(245, 200, 75, 0.06)", line_width=0)
    fig_hist.add_hrect(y0=55, y1=75, fillcolor="rgba(255, 122, 69, 0.08)", line_width=0)
    fig_hist.add_hrect(y0=75, y1=100, fillcolor="rgba(255, 59, 48, 0.10)", line_width=0)

    fig_hist.add_vline(
        x=selected_row["timestamp"],
        line=dict(color=selected_state_color, width=1, dash="dot"),
    )
    fig_hist.add_trace(
        go.Scatter(
            x=[selected_row["timestamp"]],
            y=[selected_val],
            mode="markers",
            name="Selected",
            marker=dict(color=selected_state_color, size=9, symbol="circle"),
            showlegend=False,
        )
    )

    fig_hist.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=420,
        margin=dict(l=40, r=20, t=20, b=40),
        showlegend=True,
    )
    fig_hist.update_yaxes(
        range=[0, 100],
        tickvals=[0, 20, 40, 60, 80, 100],
        showgrid=False,
        tickfont=dict(color="#C7D0DB"),
    )
    fig_hist.update_xaxes(showgrid=False, tickfont=dict(color="#C7D0DB"))

    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("Failed to connect to Sentiment API. Check your connection.")

st.markdown("---")
st.caption("Alpha Terminal Institutional Data - Updates every 24h via Alternative.me API")
