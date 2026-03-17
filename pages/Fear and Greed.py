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
    df_hist["details"] = df_hist["value"].apply(lambda v: state_from_value(int(v)))
    df_hist["state_label"] = df_hist["details"].apply(lambda x: x[0])
    df_hist["state_color"] = df_hist["details"].apply(lambda x: x[1])
    df_hist["date_label"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d")

    current_row = df_hist.iloc[-1]
    selected_val = int(current_row["value"])
    selected_status = current_row["state_label"]
    selected_state_color = current_row["state_color"]
    selected_label = current_row["date_label"]
    selected_delta = selected_val - (df_hist.iloc[-2]["value"] if len(df_hist) > 1 else selected_val)

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=selected_val,
            title={"text": f"Sentiment on {selected_label}: {selected_status}", "font": {"color": selected_state_color, "size": 24}},
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
            }
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Current Value", value=f"{selected_val} pts", delta=selected_delta)
        st.markdown("---")
        st.markdown("### Last 7 Days")
        history_display = df_hist.tail(7)[["date_label", "value", "state_label"]].copy()
        history_display = history_display.iloc[::-1]
        st.dataframe(history_display, use_container_width=True)

    st.markdown("---")
    st.markdown("### Sentiment Historical (Last Months)")

    fig_hist = go.Figure()

    # CAMADA 1: Linha de tendência original
    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"], y=df_hist["value"],
        mode="lines", line=dict(color="rgba(180, 180, 180, 0.4)", width=1.5),
        hoverinfo="skip", showlegend=False
    ))

    # CAMADA 2: Trilha invisível para hover
    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"], y=df_hist["value"],
        mode="markers", marker=dict(color=df_hist["state_color"], size=4, opacity=0.01),
        customdata=df_hist["state_label"],
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
        showlegend=False
    ))

    # CAMADA 3: O CÍRCULO NO SINAL ATUAL (Única adição nova)
    fig_hist.add_shape(
        type="circle",
        xref="x", yref="y",
        x0=current_row["timestamp"] - pd.Timedelta(hours=12),
        y0=selected_val - 1.5,
        x1=current_row["timestamp"] + pd.Timedelta(hours=12),
        y1=selected_val + 1.5,
        line=dict(color=selected_state_color, width=2),
        fillcolor=selected_state_color, # Círculo preenchido como na imagem
        opacity=1
    )

    # ZONAS DE FUNDO
    zones = [(0, 25, "#00E676", 0.05), (25, 40, "#00C853", 0.05), (40, 59, "#F5C84B", 0.05), (59, 74, "#FF7A45", 0.05), (74, 100, "#FF3B30", 0.05)]
    for y0, y1, color, op in zones:
        fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)

    fig_hist.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=420, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, hovermode="closest"
    )
    fig_hist.update_yaxes(range=[0, 100], showgrid=False)
    fig_hist.update_xaxes(showgrid=False)

    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("Terminal offline.")
