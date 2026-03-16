import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600)  # Cache de 1 hora
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

df = get_fng_data(limit=365)

if df is not None:
    # API vem em ordem descendente (mais recente primeiro)
    current_val = df.iloc[0]["value"]
    current_status = df.iloc[0]["value_classification"]
    prev_val = df.iloc[1]["value"] if len(df) > 1 else current_val
    delta = current_val - prev_val

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gauge Chart
        color = "#00E5FF" if current_val > 45 else "#FF4B4B"
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_val,
            title={"text": f"Current Sentiment: {current_status}", "font": {"color": color, "size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar": {"color": color},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 25], "color": "rgba(255, 75, 75, 0.2)"},
                    {"range": [75, 100], "color": "rgba(0, 229, 255, 0.2)"},
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

        def highlight_fng(val):
            if val > 70:
                return "color: #00E5FF; font-weight: bold"
            if val < 30:
                return "color: #FF4B4B; font-weight: bold"
            return "color: white"

        st.dataframe(
            history_display.style.applymap(highlight_fng, subset=["Value"]),
            use_container_width=True
        )

    # Gráfico histórico (últimos meses)
    st.markdown("---")
    st.markdown("### Sentiment Histórico (Últimos Meses)")

    df_hist = df.sort_values("timestamp")

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"],
        y=df_hist["value"],
        mode="lines",
        name="F&G",
        line=dict(color="#C7D0DB", width=2),
    ))

    # Marcar extremos
    extreme_fear = df_hist[df_hist["value"] <= 20]
    extreme_greed = df_hist[df_hist["value"] >= 80]

    fig_hist.add_trace(go.Scatter(
        x=extreme_fear["timestamp"],
        y=extreme_fear["value"],
        mode="markers",
        name="Extreme Fear",
        marker=dict(color="#FF4B4B", size=6),
    ))
    fig_hist.add_trace(go.Scatter(
        x=extreme_greed["timestamp"],
        y=extreme_greed["value"],
        mode="markers",
        name="Extreme Greed",
        marker=dict(color="#00E5FF", size=6),
    ))

    # Faixas de referência
    fig_hist.add_hrect(y0=0, y1=20, fillcolor="rgba(255,75,75,0.12)", line_width=0)
    fig_hist.add_hrect(y0=20, y1=40, fillcolor="rgba(255,75,75,0.06)", line_width=0)
    fig_hist.add_hrect(y0=40, y1=60, fillcolor="rgba(199,208,219,0.05)", line_width=0)
    fig_hist.add_hrect(y0=60, y1=80, fillcolor="rgba(0,229,255,0.06)", line_width=0)
    fig_hist.add_hrect(y0=80, y1=100, fillcolor="rgba(0,229,255,0.12)", line_width=0)

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

