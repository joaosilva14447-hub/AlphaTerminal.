import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Padrão AlphaTerminal
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
    # Faixas oficiais (Alternative.me): 0-24, 25-49, 50-54, 55-74, 75-100
    if value < 25:
        return "Extreme Fear", "#1B5E20"
    if value < 50:
        return "Fear", "#2E7D32"
    if value < 55:
        return "Neutral", "#F9A825"
    if value < 75:
        return "Greed", "#E65100"
    return "Extreme Greed", "#B71C1C"

df = get_fng_data(limit=365)

if df is not None:
    current_val = df.iloc[0]["value"]
    current_status = df.iloc[0]["value_classification"]
    prev_val = df.iloc[1]["value"] if len(df) > 1 else current_val
    delta = current_val - prev_val

    state_label, state_color = state_from_value(current_val)

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=current_val,
                title={"text": f"Current Sentiment: {current_status}", "font": {"color": state_color, "size": 24}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "white"},
                    "bar": {"color": state_color},
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(27, 94, 32, 0.20)"},
                        {"range": [25, 50], "color": "rgba(46, 125, 50, 0.18)"},
                        {"range": [50, 55], "color": "rgba(249, 168, 37, 0.16)"},
                        {"range": [55, 75], "color": "rgba(230, 81, 0, 0.18)"},
                        {"range": [75, 100], "color": "rgba(183, 28, 28, 0.22)"},
                    ],
                },
            )
        )
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Change vs Yesterday", value=f"{current_val} pts", delta=delta)

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

    # Gráfico histórico (últimos meses)
    st.markdown("---")
    st.markdown("### Sentiment Historical (Last Months)")

    df_hist = df.sort_values("timestamp")

    fig_hist = go.Figure()
    fig_hist.add_trace(
        go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="lines",
            name="F&G",
            line=dict(color=state_color, width=2.2),
        )
    )

    extreme_fear = df_hist[df_hist["value"] <= 20]
    extreme_greed = df_hist[df_hist["value"] >= 80]

    fig_hist.add_trace(
        go.Scatter(
            x=extreme_fear["timestamp"],
            y=extreme_fear["value"],
            mode="markers",
            name="Extreme Fear",
            marker=dict(color="#1B5E20", size=7, symbol="triangle-down"),
        )
    )
    fig_hist.add_trace(
        go.Scatter(
            x=extreme_greed["timestamp"],
            y=extreme_greed["value"],
            mode="markers",
            name="Extreme Greed",
            marker=dict(color="#B71C1C", size=7, symbol="triangle-up"),
        )
    )

    fig_hist.add_hrect(y0=0, y1=25, fillcolor="rgba(27, 94, 32, 0.10)", line_width=0)
    fig_hist.add_hrect(y0=25, y1=50, fillcolor="rgba(46, 125, 50, 0.08)", line_width=0)
    fig_hist.add_hrect(y0=50, y1=55, fillcolor="rgba(249, 168, 37, 0.06)", line_width=0)
    fig_hist.add_hrect(y0=55, y1=75, fillcolor="rgba(230, 81, 0, 0.08)", line_width=0)
    fig_hist.add_hrect(y0=75, y1=100, fillcolor="rgba(183, 28, 28, 0.10)", line_width=0)

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
