import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# 1. Configuração e Estilo
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
    # Dados Atuais
    current_val = df.iloc[0]["value"]
    current_status = df.iloc[0]["value_classification"]
    prev_val = df.iloc[1]["value"]
    delta = current_val - prev_val
    
    # Cálculos Institucionais
    df_hist = df.sort_values("timestamp")
    df_hist["SMA7"] = df_hist["value"].rolling(window=7).mean()

    st.title("Fear & Greed Index | Institutional Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gauge com Preenchimento Sólido (O visual que pediste)
        color = "#00E5FF" if current_val > 45 else "#FF4B4B"
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_val,
            title={"text": f"Sentiment: {current_status}", "font": {"color": color, "size": 24}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar": {"color": "white", "thickness": 0.2},
                "bgcolor": "rgba(255,255,255,0.03)",
                "steps": [
                    {"range": [0, 20], "color": "#FF4B4B", "thickness": 1},
                    {"range": [80, 100], "color": "#00E5FF", "thickness": 1}
                ],
            },
        ))
        gauge_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400)
        st.plotly_chart(gauge_fig, use_container_width=True)

    with col2:
        st.metric(label="24h Change", value=f"{current_val} pts", delta=delta)
        st.markdown("---")
        st.markdown("### Signal History")
        st.dataframe(df[["timestamp", "value", "value_classification"]].head(7), use_container_width=True)

    # 2. Gráfico Histórico com Sinais e SMA
    st.markdown("### Sentiment & Trend Analysis")
    
    fig_hist = go.Figure()

    # Faixas de Fundo (Camadas de Sentimento)
    fig_hist.add_hrect(y0=0, y1=20, fillcolor="rgba(255,75,75,0.1)", line_width=0)
    fig_hist.add_hrect(y0=80, y1=100, fillcolor="rgba(0,229,255,0.1)", line_width=0)

    # Linha Principal (Preço do Sentimento)
    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"], y=df_hist["value"],
        mode="lines", name="Daily F&G",
        line=dict(color="rgba(199,208,219,0.4)", width=1.5)
    ))

    # Média Móvel (A tendência real)
    fig_hist.add_trace(go.Scatter(
        x=df_hist["timestamp"], y=df_hist["SMA7"],
        mode="lines", name="7D Trend",
        line=dict(color="#00E5FF", width=2)
    ))

    # Sinais de Execução
    buys = df_hist[df_hist["value"] <= 15]
    sells = df_hist[df_hist["value"] >= 85]

    fig_hist.add_trace(go.Scatter(
        x=buys["timestamp"], y=buys["value"],
        mode="markers", name="Institutional Buy",
        marker=dict(color="#FF4B4B", size=8, symbol="triangle-up")
    ))

    fig_hist.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.error("API Error: Verifica a tua conexão.")
