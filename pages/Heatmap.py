import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

# 1. Configuração AlphaTerminal
st.set_page_config(page_title="Liquidation Engine", layout="wide")

@st.cache_data(ttl=300) # Atualiza a cada 5 minutos
def get_liq_data():
    # Puxamos dados do BTC para simular os níveis de liquidez
    df = yf.download("BTC-USD", period="1mo", interval="1h")
    return df

df = get_liq_data()

if not df.empty:
    current_price = df['Close'].iloc[-1]
    
    st.title("Liquidation Heatmap | Order Flow Engine")
    
    # 2. Lógica de Clusters (Simulação Institucional de Alavancagem)
    # Calculamos onde estão os "stops" de 25x, 50x e 100x
    leverages = {"100x": 0.01, "50x": 0.02, "25x": 0.04}
    
    short_liq_levels = []
    long_liq_levels = []
    
    for label, margin in leverages.items():
        long_liq_levels.append({'label': f'Longs {label}', 'price': current_price * (1 - margin), 'color': '#00E5FF'})
        short_liq_levels.append({'label': f'Shorts {label}', 'price': current_price * (1 + margin), 'color': '#FF4B4B'})

    # 3. Layout Lateral (Métricas Rápidas)
    col1, col2 = st.columns([3, 1])

    with col1:
        # Gráfico de Heatmap
        fig = go.Figure()

        # Preço Atual
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="BTC Price", line=dict(color="white", width=2)))

        # Adicionar Zonas de Liquidez (Heatmap)
        for liq in long_liq_levels:
            fig.add_hline(y=liq['price'], line_dash="dot", line_color=liq['color'], 
                          annotation_text=liq['label'], annotation_position="bottom right")
            fig.add_hrect(y0=liq['price']*0.998, y1=liq['price']*1.002, fillcolor=liq['color'], opacity=0.1, line_width=0)

        for liq in short_liq_levels:
            fig.add_hline(y=liq['price'], line_dash="dot", line_color=liq['color'], 
                          annotation_text=liq['label'], annotation_position="top right")
            fig.add_hrect(y0=liq['price']*0.998, y1=liq['price']*1.002, fillcolor=liq['color'], opacity=0.1, line_width=0)

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=600, margin=dict(l=0, r=0, t=20, b=0),
            yaxis=dict(title="Liquidation Price (USD)", gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Liquidation Risk")
        # Simulação de Proximidade (Qual lado vai quebrar primeiro?)
        risk_val = 65 # Exemplo: 65% de chance de Long Liquidation
        
        fig_risk = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_val,
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#00E5FF" if risk_val < 50 else "#FF4B4B"},
                'steps': [
                    {'range': [0, 50], 'color': "rgba(0, 229, 255, 0.1)"},
                    {'range': [50, 100], 'color': "rgba(255, 75, 75, 0.1)"}
                ]
            },
            title={'text': "Pressure: Shorts" if risk_val < 50 else "Pressure: Longs"}
        ))
        fig_risk.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=300)
        st.plotly_chart(fig_risk, use_container_width=True)

        st.markdown("---")
        st.markdown("### Key Clusters")
        # Tabela com as tuas cores [cite: 2026-02-26]
        all_levels = pd.DataFrame(long_liq_levels + short_liq_levels)
        st.table(all_levels[['label', 'price']].style.format(precision=2))

else:
    st.error("Engine Error: No Data Found")

st.caption("Alpha Terminal | Estimated Liquidation Engine based on Price Momentum")
