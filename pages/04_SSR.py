import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master
st.set_page_config(page_title="04 SSR Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_ssr_robust_engine():
    try:
        # Download unificado para garantir sincronia de datas
        tickers = ["BTC-USD", "USDT-USD"]
        df = yf.download(tickers, period="max", interval="1d", progress=False)
        
        if df.empty: return pd.DataFrame()

        # Tratamento de MultiIndex (Yahoo Finance 2024/2026 Format)
        if isinstance(df.columns, pd.MultiIndex):
            price_btc = df['Close']['BTC-USD']
            vol_usdt = df['Volume']['USDT-USD']
        else:
            # Fallback para versões mais antigas ou retornos simples
            price_btc = df['Close'] if 'BTC-USD' not in df else df['Close']['BTC-USD']
            vol_usdt = df['Volume'] if 'USDT-USD' not in df else df['Volume']['USDT-USD']

        # Criar DataFrame limpo e remover NaNs iniciais (onde USDT ainda não existia)
        data = pd.DataFrame({'price': price_btc, 'usdt_vol': vol_usdt}).dropna()
        
        # --- MOTOR DE CÁLCULO SSR ---
        # Evitar divisão por zero se o volume for 0
        data['usdt_vol'] = data['usdt_vol'].replace(0, np.nan).ffill()
        
        # SSR = Preço BTC / Volume USDT (Média de 7 dias para capturar o fluxo de liquidez)
        data['ssr_raw'] = data['price'] / data['usdt_vol'].rolling(window=7).mean()
        
        # 1. Compressão Logarítmica
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        # 2. Z-Score Reativo (Sem smoothing) - Janela 350
        window = 350
        data['mean'] = data['log_ssr'].rolling(window=window, min_periods=30).mean()
        data['std'] = data['log_ssr'].rolling(window=window, min_periods=30).std()
        
        # 3. Inversão de Paridade: (Média - Atual) para Buying Power estar no Topo (Aqua)
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except Exception as e:
        # Debug visual para identificares o erro se persistir
        st.error(f"Engine Alert: {str(e)}")
        return pd.DataFrame()

data = fetch_ssr_robust_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #00FBFF;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento (Paridade total com MVRV)
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 HIGH BUYING POWER", "#00FBFF"
    elif last_z <= -2.0: status, s_color = "🔴 LOW BUYING POWER", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SSR Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Multipainel
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="BTC", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Escala 3 SD
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), 
                             (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills (0.4 Opacidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    
    fig.update_yaxes(
        row=2, col=1, 
        showgrid=False, 
        autorange='reversed', # Aqua em Cima, Blue em Baixo
        range=[-3.3, 3.3], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3]
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
