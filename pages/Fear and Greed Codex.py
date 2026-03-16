import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd

# Configuração Padrão AlphaTerminal
st.set_page_config(page_title="Fear & Greed Pro", layout="wide")

@st.cache_data(ttl=3600)
def get_fng_data(limit=90): # Aumentado para 90 dias para análise histórica
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

    st.title("Fear & Greed Index | Institutional Monitor")
    
    # --- SECÇÃO SUPERIOR: GAUGE E METRICAS ---
    col1, col2 = st.columns([2, 1])

    with col1:
        solid_red = "#FF4B4B"
        solid_aqua = "#00E5FF"
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = current_val,
            title = {'text': f"Current Sentiment: {current_status}", 'font': {'color': solid_red if current_val <= 45 else solid_aqua, 'size': 24}},
            gauge = {
                'axis': {'range': [0, 100], 'tickcolor': "white"},
                'bar': {'color': "white", 'thickness': 0.2},
                'bgcolor': "rgba(255, 255, 255, 0.03)",
                'steps': [
                    {'range': [0, 20], 'color': solid_red, 'thickness': 1}, 
                    {'range': [80, 100], 'color': solid_aqua, 'thickness': 1}
                ],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=400, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta (24h)")
        st.metric(label="Change vs Yesterday", value=f"{current_val} pts", delta=delta)
        st.markdown("---")
        st.markdown("### Recent History")
        history_mini = df.head(7)[['timestamp', 'value', 'value_classification']]
        history_mini.columns = ['Date', 'Value', 'Status']
        st.dataframe(history_mini, use_container_width=True, hide_index=True)

    # --- NOVO: GRÁFICO DE TENDÊNCIA HISTÓRICA ---
    st.markdown("---")
    st.subheader("Sentiment Trend Analysis (Last 90 Days)")
    
    fig_trend = go.Figure()

    # Linha de Tendência
    fig_trend.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['value'],
        mode='lines',
        line=dict(color='#00E5FF', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 229, 255, 0.1)', # AlphaBlue glow
        name='Sentiment Value'
    ))

    # Linhas de Referência Institucional
    fig_trend.add_hline(y=80, line_dash="dot", line_color=solid_aqua, annotation_text="Extreme Greed")
    fig_trend.add_hline(y=20, line_dash="dot", line_color=solid_red, annotation_text="Extreme Fear")

    fig_trend.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, font=dict(color="white")),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', font=dict(color="white"), range=[0, 100]),
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)

else:
    st.error("API Connection Error")

st.markdown("---")
st.caption("Alpha Terminal | Institutional Grade Sentiment Analytics")
