import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Institucional
st.set_page_config(page_title="Fear & Greed Index", layout="wide")

@st.cache_data(ttl=3600)
def get_fng_data(limit=365):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={limit}", timeout=5)
        df = pd.DataFrame(r.json()["data"])
        df["value"] = df["value"].astype(int)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
        return df.sort_values("timestamp")
    except:
        return None

def get_sentiment_details(val):
    if val <= 25: return "Extreme Fear", "#00E676"  # Verde Brilhante
    if val <= 40: return "Fear", "#00C853"          # Verde Escuro
    if val <= 59: return "Neutral", "#F5C84B"       # Amarelo
    if val <= 74: return "Greed", "#FF7A45"         # Laranja
    return "Extreme Greed", "#FF3B30"               # Vermelho

df = get_fng_data()

if df is not None:
    # Processamento de labels para garantir precisão atômica
    df["state"] = df["value"].apply(lambda v: get_sentiment_details(v)[0])
    df["color"] = df["value"].apply(lambda v: get_sentiment_details(v)[1])

    st.title("Sentiment Historical Analysis")

    fig = go.Figure()

    # 1. CAMADA VISUAL: Segmentos de Linha Coloridos (Igual à imagem de referência)
    for i in range(1, len(df)):
        # O segmento entre ontem e hoje assume a cor do valor de hoje
        color = df["color"].iloc[i]
        fig.add_trace(go.Scatter(
            x=df["timestamp"].iloc[i-1:i+1],
            y=df["value"].iloc[i-1:i+1],
            mode="lines",
            line=dict(color=color, width=2.5),
            hoverinfo="skip", # Ignora hover nesta camada para evitar erros
            showlegend=False
        ))

    # 2. CAMADA DE DADOS: Pontos Invisíveis para Precisão do Hover
    # Esta camada garante que ao passar o mouse, o valor e o estado sejam 100% exatos.
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["value"],
        mode="markers",
        marker=dict(color="rgba(0,0,0,0)", size=8), # Marcadores invisíveis
        customdata=df["state"],
        hovertemplate="<b>%{x|%d %b, %Y}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
        name="Sentiment"
    ))

    # 3. ZONAS DE FUNDO (Igual ao seu exemplo)
    zones = [
        (0, 25, "#00E676", 0.05),
        (25, 40, "#00C853", 0.05),
        (40, 59, "#F5C84B", 0.05),
        (59, 74, "#FF7A45", 0.05),
        (74, 100, "#FF3B30", 0.05)
    ]
    for y0, y1, color, op in zones:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0F0F0F",
        plot_bgcolor="#0F0F0F",
        height=500,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#1A1A1A", zeroline=False)
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Data connection failed.")
