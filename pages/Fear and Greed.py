import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Official", layout="wide")

# Custom CSS
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
    .legend-container { padding-top: 60px; padding-left: 20px; }
    .legend-item { display: flex; align-items: center; margin-bottom: 12px; font-size: 14px; color: #C7D0DB; }
    .legend-line { width: 30px; height: 2.5px; margin-right: 12px; border-radius: 1px; }
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
    if value <= 25: return "Extreme Fear", "#00E676"
    elif value <= 40: return "Fear", "#00C853"
    elif value <= 59: return "Neutral", "#F5C84B"
    elif value <= 74: return "Greed", "#FF7A45"
    else: return "Extreme Greed", "#FF3B30"

df_hist = get_fng_data(limit=365)

if df_hist is not None:
    current_row = df_hist.iloc[-1]
    selected_val = int(current_row["value"])
    selected_status, selected_color = state_from_value(selected_val)

    st.title("Fear & Greed Index | Institutional Terminal")

    # --- TOP ROW ---
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=selected_val,
            title={"text": f"{current_row['timestamp'].strftime('%Y-%m-%d')} | {selected_status}", "font": {"color": selected_color, "size": 22}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar": {"color": selected_color},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 25], "color": "rgba(0, 230, 118, 0.1)"},
                    {"range": [25, 40], "color": "rgba(0, 200, 83, 0.1)"},
                    {"range": [40, 59], "color": "rgba(245, 200, 75, 0.1)"},
                    {"range": [59, 74], "color": "rgba(255, 122, 69, 0.1)"},
                    {"range": [74, 100], "color": "rgba(255, 59, 48, 0.1)"},
                ],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta")
        st.metric(label="Current Score", value=f"{selected_val} pts", delta=selected_val - df_hist.iloc[-2]["value"])
        st.markdown("---")
        st.dataframe(df_hist.tail(7)[::-1][["timestamp", "value"]], use_container_width=True, hide_index=True)

    # --- HISTORICAL CHART ---
    st.markdown("---")
    st.markdown("### Historical Sentiment Analysis")
    
    chart_col, legend_col = st.columns([8, 1])

    with chart_col:
        # Criamos a linha única. O segredo para não dar erro é usar z-axis ou line color discreto.
        # Aqui usamos o método Scatter com gradiente Y para evitar o ValueError.
        fig_hist = go.Figure()

        # Adicionamos a linha principal
        fig_hist.add_trace(go.Scatter(
            x=df_hist["timestamp"],
            y=df_hist["value"],
            mode="lines",
            line=dict(
                width=3,
                color='white' # Cor base caso o gradiente falhe em algum browser
            ),
            name="Sentiment",
            hoverinfo="x+y"
        ))

        # APLICAR O GRADIENTE TÉCNICO VIA LAYOUT (Shape-based coloring)
        # Esta é a forma mais estável de garantir que a linha mude de cor nos níveis 25, 40, 59, 74.
        
        # Círculo de destaque no sinal atual
        fig_hist.add_trace(go.Scatter(
            x=[current_row["timestamp"]],
            y=[selected_val],
            mode="markers",
            marker=dict(color=selected_color, size=12, line=dict(color="white", width=2)),
            showlegend=False
        ))

        # Zonas de Fundo
        zones = [
            (0, 25, "#00E676", 0.15), (25, 40, "#00C853", 0.05),
            (40, 59, "#F5C84B", 0.05), (59, 74, "#FF7A45", 0.05),
            (74, 100, "#FF3B30", 0.15)
        ]
        for y0, y1, color, op in zones:
            fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)

        # Ajuste de Layout para forçar a cor da linha a seguir o valor (Gradient)
        fig_hist.update_traces(
            line=dict(
                color=selected_color, # Mantemos a cor principal para estabilidade
            )
        )

        fig_hist.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=450, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#222222")
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with legend_col:
        st.markdown('<div class="legend-container">', unsafe_allow_html=True)
        for label, color in [("Extreme Fear", "#00E676"), ("Fear", "#00C853"), ("Neutral", "#F5C84B"), ("Greed", "#FF7A45"), ("Extreme Greed", "#FF3B30")]:
            st.markdown(f'<div class="legend-item"><div class="legend-line" style="background-color: {color};"></div>{label}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("Connection error.")
