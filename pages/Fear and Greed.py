import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# 1. Configuração AlphaTerminal
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}")
        data = r.json()
        df = pd.DataFrame(data["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df
    except:
        return None

df = get_fng_data()

if df is not None:
    current_val = df.iloc[0]["value"]
    current_status = df.iloc[0]["value_classification"]
    
    # 2. Definição de Cores e Fases (Alpha Pallet)
    color_map = {
        "Extreme Fear": "#FF4B4B",        # AlphaRed
        "Fear": "rgba(255, 75, 75, 0.5)", # Red Translucent
        "Neutral": "#C7D0DB",             # Slate/Steel (Neutro)
        "Greed": "rgba(0, 229, 255, 0.5)",# Aqua Translucent
        "Extreme Greed": "#00E5FF"        # Aqua/AlphaBlue
    }
    
    # Lógica de cor dinâmica baseada no valor real
    if current_val <= 25: current_color = color_map["Extreme Fear"]
    elif current_val <= 45: current_color = color_map["Fear"]
    elif current_val <= 55: current_color = color_map["Neutral"]
    elif current_val <= 75: current_color = color_map["Greed"]
    else: current_color = color_map["Extreme Greed"]

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gauge com 5 Fases Sólidas
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_val,
            title={"text": f"Sentiment: {current_status}", "font": {"color": current_color, "size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white", "tickwidth": 2},
                "bar": {"color": "white", "thickness": 0.2},
                "bgcolor": "rgba(255,255,255,0.03)",
                "steps": [
                    {"range": [0, 25], "color": color_map["Extreme Fear"], "thickness": 1},
                    {"range": [25, 45], "color": color_map["Fear"], "thickness": 1},
                    {"range": [45, 55], "color": color_map["Neutral"], "thickness": 1},
                    {"range": [55, 75], "color": color_map["Greed"], "thickness": 1},
                    {"range": [75, 100], "color": color_map["Extreme Greed"], "thickness": 1},
                ],
            },
        ))
        gauge_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=450)
        st.plotly_chart(gauge_fig, use_container_width=True)

    with col2:
        st.markdown("### Historical Analysis")
        # Pequena lógica para mostrar o status do dia anterior
        prev_val = df.iloc[1]["value"]
        delta = current_val - prev_val
        st.metric(label="24h Change", value=f"{current_val} pts", delta=delta)
        
        st.markdown("---")
        st.markdown("### Recent Snapshots")
        st.dataframe(df[["timestamp", "value", "value_classification"]].head(7), use_container_width=True, hide_index=True)

else:
    st.error("Connection Error")

