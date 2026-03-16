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
        # Gauge Chart OTIMIZADO para cores sólidas de alto impacto
        
        # Define a cor principal do ponteiro e do número
        main_color = "#00E5FF" if current_val > 45 else "#FF4B4B" # Aqua se >45, AlphaRed se <=45
        
        # Cores Sólidas para as zonas (sem transparência)
        solid_red = "#FF4B4B"
        solid_aqua = "#00E5FF"
        arc_bg_color = "rgba(255, 255, 255, 0.05)" # Um cinza muito suave para o fundo do arco

        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_val,
            title = {'text': f"Current Sentiment: {current_status}", 'font': {'color': main_color, 'size': 24}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "white"},
                'bar': {'color': main_color}, # A cor da barra segue o sentimento atual
                'bgcolor': arc_bg_color,
                'borderwidth': 0,
                'steps': [
                    # AQUI ESTÁ A CORREÇÃO: Preenchimento SÓLIDO e BRILHANTE nas pontas
                    {'range': [0, 25], 'color': solid_red}, # Extreme Fear Sólido (AlphaRed)
                    {'range': [25, 75], 'color': "rgba(128, 128, 128, 0.1)"}, # Zona Neutra suave
                    {'range': [75, 100], 'color': solid_aqua} # Extreme Greed Sólido (Aqua)
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
