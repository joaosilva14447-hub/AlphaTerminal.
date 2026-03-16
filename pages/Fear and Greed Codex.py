import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600) # Cache de 1 hora para performance de elite
def get_fng_data(limit=7):
    try:
        r = requests.get(f'https://api.alternative.me/fng/?limit={limit}')
        data = r.json()
        df = pd.DataFrame(data['data'])
        df['value'] = df['value'].astype(int)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        return df
    except:
        return None

df = get_fng_data()

if df is not None:
    current_val = df.iloc[0]['value']
    current_status = df.iloc[0]['value_classification']
    prev_val = df.iloc[1]['value']
    delta = current_val - prev_val

    # Layout do Terminal
    st.title("Fear & Greed Index | Institutional Monitor")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        # Gauge Chart
        color = "#00E5FF" if current_val > 45 else "#FF4B4B"
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_val,
            title = {'text': f"Current Sentiment: {current_status}", 'font': {'color': color, 'size': 24}},
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
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        delta_color = "inverse" if delta < 0 else "normal"
        st.metric(label="Change vs Yesterday", value=f"{current_val} pts", delta=delta)
        
        st.markdown("---")
        st.markdown("### Last 7 Days")
        
        # Tabela de Histórico seguindo a tua lógica de cores
        history_display = df[['timestamp', 'value', 'value_classification']].copy()
        history_display.columns = ['Date', 'Value', 'Classification']
        
        def highlight_fng(val):
            if val > 70: return 'color: #00E5FF; font-weight: bold' # Aqua
            if val < 30: return 'color: #FF4B4B; font-weight: bold' # AlphaRed
            return 'color: white'

        st.dataframe(history_display.style.applymap(highlight_fng, subset=['Value']), use_container_width=True)

else:
    st.error("Failed to connect to Sentiment API. Check your connection.")

st.markdown("---")
st.caption("Alpha Terminal Institutional Data - Updates every 24h via Alternative.me API")
