import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração ACD Terminal
st.set_page_config(page_title="ACD Terminal", layout="wide")

# Estética Hedge Fund
st.markdown("<style>.main { background-color: #0F0F0F; } div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }</style>", unsafe_allow_html=True)

@st.cache_data(ttl=120) # Atualiza o cache a cada 2 minutos
def fetch_acd_data():
    try:
        # Download robusto: apanha o histórico + candle atual (live)
        df_raw = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        
        if df_raw.empty: return pd.DataFrame()
        
        # Tratamento de MultiIndex (Garante que o código não dá erro se a API mudar o formato)
        if isinstance(df_raw.columns, pd.MultiIndex):
            df = pd.DataFrame(df_raw['Close'].iloc[:, 0])
        else:
            df = pd.DataFrame(df_raw['Close'])
            
        df.columns = ['close']
        
        # --- Motor de Cálculo ACD ---
        df['log_price'] = np.log(df['close'])
        
        # Janela institucional de 350 dias
        window = 350
        df['mean'] = df['log_price'].rolling(window=window).mean()
        df['std'] = df['log_price'].rolling(window=window).std()
        
        # Z-Score Revertido (Lógica: Fundo em cima, Topo em baixo)
        df['z_score'] = (df['mean'] - df['log_price']) / df['std']
        
        # Clipping de escala para manter a integridade visual
        df['z_score'] = df['z_score'].clip(-3.8, 3.8)
        
        return df.dropna()
    except Exception as e:
        st.error(f"Erro na extração de dados: {e}")
        return pd.DataFrame()

# Execução do Data Feed
data = fetch_acd_data()

if not data.empty:
    last_z = data['z_score'].iloc[-1]
    current_price = data['close'].iloc[-1]
    
    # Hierarquia de Sinais (Palete Aqua/AlphaBlue)
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 OVERSOLD (BOTTOM)", "#00FBFF"
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 SLIGHT OVERSOLD", "rgba(0, 251, 255, 0.6)"
    elif last_z <= -2.0: status, s_color = "🔴 OVERBOUGHT (TOP)", "#3D5AFE"
    elif -1.0 >= last_z > -2.0: status, s_color = "🔸 SLIGHT OVERBOUGHT", "rgba(61, 90, 254, 0.6)"

    st.markdown("<h1 style='text-align: center; color: #3D5AFE; font-family: serif;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓒𝔂𝓬𝓵𝓮 𝓓𝓮𝓿𝓲𝓪𝓽𝓲𝓸𝓷 ✦</h1>", unsafe_allow_html=True)
    
    # Header Metrics com Preço Real-Time
    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("LIVE BTC PRICE", f"${current_price:,.2f}")
    c2.metric("ACD LEVEL (SD)", f"{last_z:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 32px;'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Preço Logarítmico
    fig.add_trace(go.Scatter(x=data.index, y=data['close'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    
    # Indicador ACD (Z-Score)
    fig.add_trace(go.Scatter(x=data.index, y=data['z_score'], name="ACD", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Fronteira e Escala Fixa
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Preenchimentos de Convicção (Fills)
    # Topo (Blue)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z_score'] <= -2.0, data['z_score'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.5)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Fundo (Aqua)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z_score'] >= 2.0, data['z_score'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.5)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Final
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, gridcolor="#222")
    fig.update_yaxes(
        row=2, col=1, 
        gridcolor="#222", 
        autorange='reversed', 
        range=[-3.8, 3.8], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    st.markdown(f"<p style='text-align: center; color: #444;'>Last sync: {data.index[-1].strftime('%Y-%m-%d %H:%M:%S')} | Real-Time Feed Active</p>", unsafe_allow_html=True)
else:
    st.error("Terminal offline: Erro na conexão com a API de dados financeiros.")

