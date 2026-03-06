import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master do Terminal
st.set_page_config(page_title="04 SSR Terminal (2017+)", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_ssr_2017_engine():
    try:
        # 1. Download de dados BTC e USDT
        tickers = ["BTC-USD", "USDT-USD"]
        df = yf.download(tickers, period="max", interval="1d", progress=False)
        
        if df.empty: return pd.DataFrame()

        # Tratamento MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            price_btc = df['Close']['BTC-USD']
            vol_usdt = df['Volume']['USDT-USD']
        else:
            price_btc = df['Close']
            vol_usdt = df['Volume']

        # Criar Dataset alinhado
        data = pd.DataFrame({'price': price_btc, 'usdt_vol': vol_usdt})
        
        # --- FILTRO TEMPORAL 2017 ---
        # Iniciamos em 2017-01-01 para garantir foco no ciclo solicitado
        data = data[data.index >= '2017-01-01'].copy()
        
        # Substituir zeros no volume para evitar erros de divisão
        data['usdt_vol'] = data['usdt_vol'].replace(0, np.nan).ffill()
        
        # 2. CÁLCULO SSR (Reativo)
        # SSR = Preço BTC / Volume USDT (Média de 7 dias para fluidez)
        data['ssr_raw'] = data['price'] / data['usdt_vol'].rolling(window=7, min_periods=1).mean()
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        # --- MOTOR Z-SCORE EXPANSIVO (Sinal Imediato) ---
        # Usamosexpanding() para que o sinal comece logo após 14 dias de dados
        window_limit = 350
        data['mean'] = data['log_ssr'].expanding(min_periods=14).mean()
        data['std'] = data['log_ssr'].expanding(min_periods=14).std()
        
        # Após atingir 350 dias, estabiliza na janela institucional fixa
        data.loc[data.index[window_limit:], 'mean'] = data['log_ssr'].rolling(window=window_limit).mean()
        data.loc[data.index[window_limit:], 'std'] = data['log_ssr'].rolling(window=window_limit).std()
        
        # 3. Inversão de Paridade: (Média - Atual) 
        # Buying Power = Aqua (Cima) | Sell Pressure = Blue (Baixo)
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['z'])
    except Exception as e:
        st.error(f"Engine Alert: {str(e)}")
        return pd.DataFrame()

data = fetch_ssr_2017_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #00FBFF;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento Granular
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 HIGH BUYING POWER", "#00FBFF"
    elif last_z <= -2.0: status, s_color = "🔴 LOW BUYING POWER", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SSR Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Multipainel
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # Subplot 1: Preço (Log Scale)
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="BTC", line=dict(color='white', width=2)), row=1, col=1)
    
    # Subplot 2: SSR Z-Score (Reativo 2017+)
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
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
