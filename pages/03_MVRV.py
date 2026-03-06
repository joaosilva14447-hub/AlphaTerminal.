import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master (Paridade Total com ACD/NUPL)
st.set_page_config(page_title="03 MVRV Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_mvrv_data():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # --- LÓGICA MVRV Z-SCORE ---
        # Realized Price Proxy (Média de 365 dias)
        data['realized'] = data['price'].rolling(window=365).mean()
        
        # Diferença absoluta entre Market Value e Realized Value
        data['diff'] = data['price'] - data['realized']
        
        # Normalização Estatística (Z-Score)
        window = 350
        data['std'] = data['diff'].rolling(window=window).std()
        data['z'] = (data['diff'] / data['std']).clip(-3.8, 3.8)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_mvrv_data()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #00FBFF;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓜𝓥𝓡𝓥 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais MVRV
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "🔴 EXTREME OVERVALUATION (TOP)", "#3D5AFE"
    elif last_z <= -1.0: status, s_color = "💎 UNDERVALUATION (ACCUMULATE)", "#00FBFF"

    c1, c2, c3 = st.columns([1, 1, 1.5])
    c1.metric("BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("MVRV Z-SCORE", f"{last_z:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px;'>{status}</h1>", unsafe_allow_html=True)

    # Gráfico Multipainel (DNA Visual do Terminal)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Subplot 1: Preço Log
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Subplot 2: MVRV Oscilador (Sem inversão para o MVRV, mantendo a leitura clássica)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="MVRV Z", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Escala Sincronizadas
    fig.add_hline(y=2.0, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=3.0, line=dict(color="#3D5AFE", width=1.0, dash="dot"), row=2, col=1)
    fig.add_hline(y=-1.0, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.1)", width=1), row=2, col=1)

    # Fills de Convicção (Opacidade 0.4)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[-1.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -1.0, data['z'], -1.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Sincronizado
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    fig.update_yaxes(row=2, col=1, showgrid=False, range=[-3.8, 3.8], tickvals=[-3, -2, -1, 0, 1, 2, 3], title="MVRV Z-Score")
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
