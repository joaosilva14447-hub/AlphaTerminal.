import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

# 1. Configuração AlphaTerminal
st.set_page_config(page_title="Liquidation Engine", layout="wide")

@st.cache_data(ttl=300)
def get_liq_data():
    try:
        # Puxamos dados do BTC
        df = yf.download("BTC-USD", period="5d", interval="15m")
        # Reset index para garantir que o tempo é tratado corretamente
        df = df.reset_index()
        # Flatten columns caso venham como MultiIndex
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        return df
    except:
        return pd.DataFrame()

df = get_liq_data()

if not df.empty:
    # Converter para float simples para evitar erros de array do Pandas
    current_price = float(df['Close'].iloc[-1])
    
    st.title("Liquidation Heatmap | Order Flow Engine")
    
    col1, col2 = st.columns([3, 1])

    with col1:
        fig = go.Figure()

        # Preço Principal
        fig.add_trace(go.Scatter(
            x=df['Datetime'], y=df['Close'],
            name="BTC Price", line=dict(color="white", width=2)
        ))

        # 2. Lógica de Níveis de Liquidação (Simulação Alpha)
        leverages = [
            {'label': '100x', 'margin': 0.01, 'alpha': 0.3},
            {'label': '50x', 'margin': 0.02, 'alpha': 0.2},
            {'label': '25x', 'margin': 0.04, 'alpha': 0.1}
        ]

        for lev in leverages:
            # Longs (Suporte de Liquidez - Aqua)
            long_p = current_price * (1 - lev['margin'])
            fig.add_hline(y=long_p, line_dash="dot", line_color="#00E5FF", opacity=lev['alpha'])
            
            # Shorts (Resistência de Liquidez - AlphaRed)
            short_p = current_price * (1 + lev['margin'])
            fig.add_hline(y=short_p, line_dash="dot", line_color="#FF4B4B", opacity=lev['alpha'])

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", height=600,
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Price USD"),
            xaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Liquidation Risk")
        # Cálculo de pressão simplificado
        st.metric("Current Price", f"${current_price:,.2f}")
        st.markdown("---")
        
        st.markdown("#### 🔥 Liquidation Clusters")
        # Tabela visual rápida
        data = {
            "Level": ["100x Shorts", "50x Shorts", "50x Longs", "100x Longs"],
            "Price": [current_price*1.01, current_price*1.02, current_price*0.98, current_price*0.99]
        }
        temp_df = pd.DataFrame(data)
        st.dataframe(temp_df.style.format({"Price": "${:,.2f}"}), use_container_width=True, hide_index=True)

else:
    st.error("Engine Error: Falha ao carregar dados da Exchange.")
