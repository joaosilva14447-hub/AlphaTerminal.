import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração de Interface Hedge Fund
st.set_page_config(page_title="ACD Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { 
        background-color: #161616; 
        padding: 20px; 
        border-radius: 5px; 
        border: 1px solid #333; 
    }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120) # Atualização automática a cada 2 minutos
def fetch_acd_live_data():
    try:
        # 1. Download do Ticker para extrair preço em tempo real
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        
        if df.empty: return pd.DataFrame()

        # 2. Extração do Preço Live (Fast Info)
        # Isso corrige o delay do Yahoo Finance que entrega o preço de 'ontem'
        live_price = ticker.fast_info['last_price']
        
        # Injetar o preço live no último candle para cálculos de Z-Score instantâneos
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        df = df[['Close']]
        df.columns = ['close']
        
        # 3. Motor Estatístico ACD (Log Normalization)
        df['log_price'] = np.log(df['close'])
        
        # Janela de Ciclo Macro (350 dias)
        window = 350
        df['mean'] = df['log_price'].rolling(window=window).mean()
        df['std'] = df['log_price'].rolling(window=window).std()
        
        # Cálculo do Z-Score Revertido (Para manter lógica institucional)
        df['z_score'] = (df['mean'] - df['log_price']) / df['std']
        
        # Clipping para evitar deformação visual na escala
        df['z_score'] = df['z_score'].clip(-3.8, 3.8)
        
        return df.dropna()
    except Exception as e:
        st.error(f"Erro na conexão com Live Feed: {e}")
        return pd.DataFrame()

# Execução do Data Engine
data = fetch_acd_live_data()

if not data.empty:
    last_z = data['z_score'].iloc[-1]
    current_price = data['close'].iloc[-1]
    
    # Cabeçalho Principal
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓒𝔂𝓬𝓵𝓮 𝓓𝓮𝓿𝓲𝓪𝓽𝓲𝓸𝓷 ✦</h1>", unsafe_allow_html=True)
    
    # Lógica de Sinais e Cores (Palete Aqua/Blue)
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 OVERSOLD (BOTTOM)", "#00FBFF"
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 SLIGHT OVERSOLD", "rgba(0, 251, 255, 0.6)"
    elif last_z <= -2.0: status, s_color = "🔴 OVERBOUGHT (TOP)", "#3D5AFE"
    elif -1.0 >= last_z > -2.0: status, s_color = "🔸 SLIGHT OVERBOUGHT", "rgba(61, 90, 254, 0.6)"

    # Painel de Métricas Superior
    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("LIVE BTC PRICE", f"${current_price:,.2f}")
    c2.metric("ACD Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 32px;'>{status}</h1>", unsafe_allow_html=True)

    # Construção do Gráfico Multipainel
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.65, 0.35]
    )
    
    # Subplot 1: Preço (Log Scale)
    fig.add_trace(go.Scatter(
        x=data.index, y=data['close'], 
        name="Price", 
        line=dict(color='white', width=2)
    ), row=1, col=1)
    
    # Subplot 2: Oscilador ACD
    fig.add_trace(go.Scatter(
        x=data.index, y=data['z_score'], 
        name="ACD SD", 
        line=dict(color='#888', width=1.5)
    ), row=2, col=1)

    # Linhas de Fronteira Estáticas (Escala 3, 2, 1, 0, -1, -2, -3)
    fig.add_hline(y=-2.0, line=dict(color="#3D5AFE", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=-3.0, line=dict(color="#3D5AFE", width=1.0, dash="dot"), row=2, col=1)
    fig.add_hline(y=2.0, line=dict(color="#00FBFF", width=1.5, dash="dash"), row=2, col=1)
    fig.add_hline(y=3.0, line=dict(color="#00FBFF", width=1.0, dash="dot"), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.1)", width=1), row=2, col=1)

    # Preenchimentos de Convicção (Fills)
    # Overbought Area (Blue)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=np.where(data['z_score'] <= -2.0, data['z_score'], -2.0), 
        fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', 
        line=dict(width=0), showlegend=False
    ), row=2, col=1)

    # Oversold Area (Aqua)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=data.index, 
        y=np.where(data['z_score'] >= 2.0, data['z_score'], 2.0), 
        fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', 
        line=dict(width=0), showlegend=False
    ), row=2, col=1)

    # Layout Final
    fig.update_layout(
        template="plotly_dark", 
        paper_bgcolor="#0F0F0F", 
        plot_bgcolor="#0F0F0F", 
        height=1000, 
        margin=dict(l=60, r=60, t=50, b=60), 
        showlegend=False
    )
    
    fig.update_yaxes(type="log", row=1, col=1, gridcolor="#222", title="BTC Price (Log)")
    fig.update_yaxes(
        row=2, col=1, 
        gridcolor="#222", 
        autorange='reversed', # Lógica de Ciclo: Topo em baixo, Fundo em cima
        range=[-3.8, 3.8], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3],
        title="Cycle Deviation (SD)"
    )
    
    # Renderização
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Footer de Atualização
    st.markdown(f"<p style='text-align: center; color: #444;'>Last update: {data.index[-1].strftime('%Y-%m-%d %H:%M:%S')} UTC</p>", unsafe_allow_html=True)

else:
    st.error("Falha ao carregar dados. Verifique a conexão com o Yahoo Finance.")

