import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Configuração Master de Elite
st.set_page_config(page_title="04 SSR On-Chain", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600) # Cache de 1h para poupar a API e acelerar o site
def fetch_real_onchain_ssr():
    try:
        # 1. Fetch BTC Data (Price & Market Cap)
        btc = yf.Ticker("BTC-USD").history(period="max", interval="1d")
        # Estimativa de Market Cap (Circulating Supply * Price)
        # Usamos uma constante aproximada de 19.7M BTC para o cálculo do Rácio
        btc['mcap'] = btc['Close'] * 19700000 
        
        # 2. Fetch DefiLlama Stablecoin Total Market Cap (API Gratuita)
        url = "https://stablecoins.llama.fi/stablecoincharts/all"
        response = requests.get(url).json()
        
        stable_data = []
        for entry in response:
            stable_data.append({
                'date': datetime.fromtimestamp(int(entry['date'])).strftime('%Y-%m-%d'),
                'stable_mcap': entry['totalCirculatingUSD']
            })
        
        stables_df = pd.DataFrame(stable_data)
        stables_df['date'] = pd.to_datetime(stables_df['date'])
        stables_df.set_index('date', inplace=True)

        # 3. Fusão de Dados
        data = btc[['Close', 'mcap']].copy()
        data.index = data.index.tz_localize(None)
        data = data.join(stables_df, how='inner') # 'inner' garante que só mostramos onde há dados de ambos

        # --- CÁLCULO SSR REAL ---
        # SSR = BTC Market Cap / Stablecoin Market Cap
        data['ssr_raw'] = data['mcap'] / data['stable_mcap']
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        # 4. Motor Z-Score Reativo (Janela 350)
        window = 350
        data['mean'] = data['log_ssr'].rolling(window=window, min_periods=30).mean()
        data['std'] = data['log_ssr'].rolling(window=window, min_periods=30).std()
        
        # Inversão: Z+ (Aqua/Cima) = SSR Baixo = Buying Power Elevado
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['z'])
    except Exception as e:
        st.error(f"On-Chain API Error: {str(e)}")
        return pd.DataFrame()

data = fetch_real_onchain_ssr()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓡𝓮𝓪𝓵 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento (Paridade com MVRV/NUPL)
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 EXTREME OVERSOLD (BUYING POWER)", "#00FBFF"
    elif last_z <= -2.0: status, s_color = "🔴 EXTREME OVERBOUGHT (SELL PRESSURE)", "#3D5AFE"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['Close'].iloc[-1]:,.2f}")
    c2.metric("ON-CHAIN SSR Z", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 26px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Linhas de Escala 3 SD
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills (0.4 Opacidade)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
