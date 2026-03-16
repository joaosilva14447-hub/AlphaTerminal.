import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600) # Cache de 1 hora para performance
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
        # Gauge Chart OTIMIZADO para o visual de "arco preenchido" em ambas as pontas
        
        # Cores Sólidas AlphaTerminal
        solid_red = "#FF4B4B" # AlphaRed para Medo
        solid_aqua = "#00E5FF" # Aqua para Ganância
        arc_bg_color = "rgba(255, 255, 255, 0.05)" # Fundo muito suave

        # Define a cor principal do ponteiro e do número
        # main_color = solid_aqua if current_val > 45 else solid_red

        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_val,
            title = {'text': f"Current Sentiment: {current_status}", 'font': {'color': solid_red if current_val <= 45 else solid_aqua, 'size': 24}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "white"},
                'bar': {'color': solid_red if current_val <= 45 else solid_aqua}, # O ponteiro brilha
                'bgcolor': arc_bg_color,
                'borderwidth': 0, # Remove a borda para ficar limpo
                'steps': [
                    # AQUI ESTÁ A CHAVE: Preenchimento SÓLIDO e BRILHANTE nas pontas
                    {'range': [0, 20], 'color': solid_red}, # Fear Sólido (como na imagem 8)
                    {'range': [20, 80], 'color': "rgba(128, 128, 128, 0.05)"}, # Zona Neutra suave
                    {'range': [80, 100], 'color': solid_aqua} # Greed Sólido (Aqua)
                ]
            }
        ))
        
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=450)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
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
