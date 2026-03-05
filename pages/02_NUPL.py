import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master (Paridade Total com ACD)
st.set_page_config(page_title="NUPL Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_nupl_clean_data():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()

        # Preço Live Único (Evita escalas triplas ou duplicadas)
        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        # Limpeza de Colunas para Série Única
        data = pd.DataFrame(df['Close'])
        data.columns = ['price']
        
        # Lógica NUPL
        data['ma_365'] = data['price'].rolling(window=365).mean()
        data['ratio'] = np.log(data['ma_365'] / data['price'])
        
        # Suavização para paridade de "curva" com o ACD (Remove o ruído visual)
        data['smooth'] = data['ratio'].rolling(window=14).mean()
        
        # Normalização Z-Score
        window = 350
        data['mean'] = data['smooth'].rolling(window=window).mean()
        data['std'] = data['smooth'].rolling(window=window).std()
        data['z'] = ((data['smooth'] - data['mean']) / data['std']).clip(-3.8, 3.8)
        
        return data.dropna()
    except:
        return pd.DataFrame()

data = fetch_nupl_clean_data()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sinais Clean
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 CAPITULATION", "#00FBFF"
    elif last_z <= -2.0: status, s_color = "🔴 EUPHORIA", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("NUPL Z", f"{last_z:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color};'>{status}</h1>", unsafe_allow_html=True)

    # Gráfico Multipainel ( DNA Visual ACD )
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Preço Único (Escala 1)
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="BTC", line=dict(color='white', width=2)), row=1, col=1)
    
    # Oscilador NUPL (Escala 2)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # --- AS 5 LINHAS CLEAN (Exatamente como no ACD) ---
    fig.add_hline(y=-2.0, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=-3.0, line=dict(color="#3D5AFE", width=1.0, dash="dot"), row=2, col=1)
    fig.add_hline(y=2.0, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=3.0, line=dict(color="#00FBFF", width=1.0, dash="dot"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.1)", width=1), row=2, col=1)

    # Fills Minimalistas (Opacidade 0.4)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Sincronizado e Limpo
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    
    # Remoção de ruído das escalas (showgrid=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False, title="BTC Price")
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.8, 3.8], tickvals=[-3, -2, 0, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
