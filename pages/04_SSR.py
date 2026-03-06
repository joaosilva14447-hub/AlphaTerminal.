import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Configuração Master de Elite
st.set_page_config(page_title="04 SSR Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_ssr_ultimate_safe():
    try:
        # 1. Download BTC (A âncora do tempo)
        btc_df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if btc_df.empty:
            return None, "Erro: Yahoo Finance não forneceu dados do BTC."
        
        # Lida com o formato de colunas do yfinance (MultiIndex ou não)
        if isinstance(btc_df.columns, pd.MultiIndex):
            price = btc_df['Close']['BTC-USD']
        else:
            price = btc_df['Close']
            
        data = pd.DataFrame({'price': price})
        data.index = pd.to_datetime(data.index).tz_localize(None)
        data['mcap'] = data['price'] * 19700000 # Estimativa de Circulating Supply

        # 2. Tentar API On-Chain (DefiLlama)
        try:
            url = "https://stablecoins.llama.fi/stablecoincharts/all"
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                raw = res.json()
                stables = pd.DataFrame([{'date': datetime.fromtimestamp(int(e['date'])), 'stable_mcap': e['totalCirculatingUSD']} for e in raw])
                stables.set_index('date', inplace=True)
                stables.index = pd.to_datetime(stables.index).tz_localize(None)
                data = data.join(stables, how='inner')
            else:
                raise Exception("API DefiLlama Off")
        except Exception as e:
            # BACKUP: Se a API falhar, usamos o volume de USDT do Yahoo como proxy de liquidez
            st.warning("⚠️ Ligação On-Chain instável. Ativando Proxy de Liquidez Secundário...")
            usdt = yf.download("USDT-USD", period="max", interval="1d", progress=False)
            usdt_vol = usdt['Volume']['USDT-USD'] if isinstance(usdt.columns, pd.MultiIndex) else usdt['Volume']
            usdt_vol = pd.DataFrame({'stable_mcap': usdt_vol.rolling(window=30).mean() * 10})
            usdt_vol.index = pd.to_datetime(usdt_vol.index).tz_localize(None)
            data = data.join(usdt_vol, how='inner')

        # 3. Cálculo do Sinal (SSR)
        data['ssr_raw'] = data['mcap'] / data['stable_mcap']
        data['log_ssr'] = np.log(data['ssr_raw'])
        
        window = 350
        data['mean'] = data['log_ssr'].rolling(window=window, min_periods=30).mean()
        data['std'] = data['log_ssr'].rolling(window=window, min_periods=30).std()
        
        # Inversão: Buying Power = Aqua (Cima)
        data['z'] = ((data['mean'] - data['log_ssr']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['z']), None
    except Exception as e:
        return None, str(e)

# Execução do Processamento
data, err = fetch_ssr_ultimate_safe()

if err:
    st.error(f"⚠️ Erro de Carregamento: {err}")
    st.info("O ecrã ficou preto porque o motor de dados não conseguiu sincronizar o BTC com as Stablecoins. Tenta atualizar a página.")
elif data is not None:
    last_z = data['z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓡𝓮𝓪𝓵 𝓢𝓽𝓪𝓫𝓵𝓮𝓬𝓸𝓲𝓷 𝓢𝓾𝓹𝓹𝓵𝔂 𝓡𝓪𝓽𝓲𝓸 ✦</h1>", unsafe_allow_html=True)

    # Sentimento Granular
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 EXTREME OVERSOLD (HIGH BUYING POWER)", "#00FBFF"
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 OVERSOLD", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0: status, s_color = "🔴 EXTREME OVERBOUGHT (LOW BUYING POWER)", "#3D5AFE"
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 OVERBOUGHT", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SSR Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='#888', width=1.5)), row=2, col=1)

    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), 
                             (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills 0.4 Opacidade
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
