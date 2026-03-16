import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

# Configuração da página seguindo o padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Index", layout="wide", initial_sidebar_state="expanded")

def get_fear_greed_data():
    # Simulação de cálculo institucional baseado em Volatilidade e Momentum
    # No futuro, podemos conectar à API da Alternative.me
    data = yf.download("BTC-USD", period="1y", interval="1d")
    
    # Cálculo de exemplo: RSI como proxy de sentimento
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_value = int(rsi.iloc[-1])
    return current_value

value = get_fear_greed_data()

# Lógica de Categorização
if value <= 25:
    status = "Extreme Fear"
    color = "#FF4B4B" # AlphaRed
elif value <= 45:
    status = "Fear"
    color = "#FFA500"
elif value <= 55:
    status = "Neutral"
    color = "#808080"
elif value <= 75:
    status = "Greed"
    color = "#00E5FF" # AlphaBlue
else:
    status = "Extreme Greed"
    color = "#00E5FF" # Aqua

st.title("Fear & Greed Index")
st.markdown("---")

# Gauge Chart
fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = value,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': f"Current Sentiment: {status}", 'font': {'size': 24, 'color': color}},
    gauge = {
        'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
        'bar': {'color': color},
        'bgcolor': "rgba(0,0,0,0)",
        'borderwidth': 2,
        'bordercolor': "#333",
        'steps': [
            {'range': [0, 25], 'color': 'rgba(255, 75, 75, 0.3)'},
            {'range': [75, 100], 'color': 'rgba(0, 229, 255, 0.3)'}
        ],
    }
))

fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})

st.plotly_chart(fig, use_container_width=True)
