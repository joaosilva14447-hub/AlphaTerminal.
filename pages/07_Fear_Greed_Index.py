import streamlit as st
import requests
import plotly.graph_objects as go

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Real-Time", layout="wide")

def get_official_fear_greed():
    try:
        r = requests.get('https://api.alternative.me/fng/')
        data = r.json()
        value = int(data['data'][0]['value'])
        status = data['data'][0]['value_classification']
        return value, status
    except:
        return 50, "Neutral (API Error)"

value, status = get_official_fear_greed()

# Tradução para a tua paleta de cores institucional
if value <= 45:
    color = "#FF4B4B" # AlphaRed para Medo
else:
    color = "#00E5FF" # Aqua para Ganância

st.title("Fear & Greed Index (Official Data)")

fig = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = value,
    title = {'text': f"Market Sentiment: {status}", 'font': {'color': color}},
    gauge = {
        'axis': {'range': [0, 100], 'tickcolor': "white"},
        'bar': {'color': color},
        'bgcolor': "rgba(0,0,0,0)",
        'steps': [
            {'range': [0, 25], 'color': 'rgba(255, 75, 75, 0.2)'},
            {'range': [75, 100], 'color': 'rgba(0, 229, 255, 0.2)'}
        ]
    }
))

fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
st.plotly_chart(fig, use_container_width=True)
