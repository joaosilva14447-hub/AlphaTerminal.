import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Configuração Master
st.set_page_config(page_title="04 SSR Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_ssr_safe_engine():
    try:
        # 1. Fetch BTC Data
        btc_raw = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if btc_raw.empty:
            return pd.DataFrame(), "Erro: Yahoo Finance não devolveu dados do BTC."

        # Extração limpa (Lida com MultiIndex)
        if isinstance(btc_raw.columns, pd.MultiIndex):
            price_btc = btc_raw['Close']['BTC-USD']
        else:
            price_btc = btc_raw['Close']
            
        btc = pd.DataFrame({'price': price_btc})
        btc['mcap'] = btc['price'] * 19700000 
        btc.index = pd.to_datetime(btc.index).tz_localize(None)
        
        # 2. Fetch DefiLlama Stablecoin Data
        url = "https://stablecoins.llama.fi/stablecoincharts/all"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame(), f"Erro API DefiLlama: Status {response.status_code}"
            
        raw_stables = response.json()
        stable_list = []
        for entry in raw_stables:
            stable_list.append({
                'date': datetime.fromtimestamp(int(entry['date'])).strftime('%Y-%m-%d'),
                'stable_mcap': entry['totalCirculatingUSD']
            })
        
        stables_df = pd.DataFrame(stable_list)
        stables_df['date'] = pd.to_datetime(stables_df['date'])
        stables_df.set_index('date', inplace=True)

        # 3. Join e Cálculo (Filtro 2017+)
        data = btc.join(stables_df, how='inner')
        data = data[data.index >= '2017-01-01'].copy()
        
        if data.empty:
            return pd.DataFrame(), "Erro: Cruzamento de dados resultou em tabela vazia."

        # SSR = BTC Market Cap / Stablecoin Market Cap
        data['ssr_raw'] = data['mcap'] / data['stable_mcap']
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        # 4. Motor Z-Score
        window = 350
        data['mean'] = data['log_ssr'].rolling(window=window, min_periods=30).mean()
        data['std'] = data['log_ssr'].rolling(window=window, min_periods=30).std()
        
        # Inversão: Z+ (Aqua) = OVERSOLD (Buying Power)
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['z']), None
    except Exception as e:
        return pd.DataFrame(), f"Erro Crítico: {str(e)}"

# Execução do Motor
data, error_msg = fetch_ssr_safe_engine()

if error_msg:
    st.error(error_msg)
    st.info("Tenta atualizar a página ou verifica a tua conexão à internet.")
elif not data.empty:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓡𝓮𝓪𝓵 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Matriz de Sentimento Granular
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0:
        status, s_color = "💎 EXTREME OVERSOLD (HIGH BUYING POWER)", "#00FBFF"
    elif 1.51 <= last_z < 2.0:
        status, s_color = "🔹 OVERSOLD (BUYING PRESSURE)", "rgba(0, 251, 255, 0.8)"
    elif 1.0 <= last_z <= 1.50:
        status, s_color = "🔹 SLIGHT OVERSOLD", "rgba(0, 251, 255, 0.5)"
    elif last_z <= -2.0:
        status, s_color = "🔴 EXTREME OVERBOUGHT (LOW BUYING POWER)", "#3D5AFE"
    elif -1.99 <= last_z <= -1.51:
        status, s_color = "🔸 OVERBOUGHT (SELL PRESSURE)", "rgba(61, 90, 254, 0.8)"
    elif -1.50 <= last_z <= -1.0:
        status, s_color = "🔸 SLIGHT OVERBOUGHT", "rgba(61, 90, 254, 0.5)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("ON-CHAIN SSR Z", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.warning("Aguardando resposta das APIs de liquidez on-chain...")
