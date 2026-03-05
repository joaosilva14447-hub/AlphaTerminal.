import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração de Interface (Layout ACD)
st.set_page_config(page_title="02 ANUPL Terminal", layout="wide")

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

@st.cache_data(ttl=120)
def fetch_anupl_pro():
    try:
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max", interval="1d")
        if df.empty: return pd.DataFrame()
        
        # Sincronização de Preço Live (Conforme ACD)
        live_price = ticker.fast_info['last_price']
        df.iloc[-1, df.columns.get_loc('Close')] = live_price
        
        df = df[['Close']]
        df.columns = ['close']
        
        # 1. Tua Lógica Original NUPL
        df['realized_proxy'] = df['close'].rolling(window=365).mean()
        df['raw_ratio'] = np.log(df['realized_proxy'] / df['close'])
        
        window = 350
        df['mean'] = df['raw_ratio'].rolling(window=window).mean()
        df['std'] = df['raw_ratio'].rolling(window=window).std()
        df['anupl_z'] = (df['raw_ratio'] - df['mean']) / df['std']
        
        # Teu Clipping Original
        df['anupl_z'] = df['anupl_z'].clip(-3.8, 3.8)
        
        return df.dropna()
    except:
        return pd.DataFrame()

data = fetch_anupl_pro()

if not data.empty:
    last_z = data['anupl_z'].iloc[-1]
    
    st.markdown("<h1 style='text-align: center; color: #3D5AFE;'>✦ 𝓐𝓵𝓹𝓱𝓪 𝓝𝓮𝓽 𝓤𝓷𝓻𝓮𝓪𝓵𝓲𝔃𝓮𝓭 𝓟𝓻𝓸𝓯𝓲𝓽/𝓛𝓸𝓼𝓼 ✦</h1>", unsafe_allow_html=True)

    # Tua Matriz de Sinais Original
    status, s_color = "NEUTRAL", "#FFFFFF"
    if last_z >= 2.0: status, s_color = "💎 EXTREME CAPITULATION", "#00FBFF"
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 CAPITULATION / FEAR", "rgba(0, 251, 255, 0.6)"
    elif last_z <= -2.0: status, s_color = "🔴 EXTREME EUPHORIA", "#3D5AFE"
    elif -1.0 >= last_z > -2.0: status, s_color = "🔸 OPTIMISM / ANXIETY", "rgba(61, 90, 254, 0.6)"

    # Painel de Métricas (Estilo ACD)
    c1, c2, c3 = st.columns([1, 1, 1.2])
    c1.metric("BITCOIN PRICE", f"${data['close'].iloc[-1]:,.2f}")
    c2.metric("SENTIMENT (SD)", f"{last_z:.2f}")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-family: sans-serif;'>{status}</h1>", unsafe_allow_html=True)

    # Estrutura de Plot Multipainel (Copiada do ACD)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    
    # --- SUBPLOT 1: PREÇO (Idêntico ao ACD) ---
    fig.add_trace(go.Scatter(x=data.index, y=data['close'], name="Price", line=dict(color='white', width=2)), row=1, col=1)

    # --- SUBPLOT 2: TEU NUPL ORIGINAL ---
    fig.add_trace(go.Scatter(x=data.index, y=data['anupl_z'], name="Sentiment SD", line=dict(color='#888', width=1.5)), row=2, col=1)

    # Tuas Linhas de Escala e Fills Originais
    for val, color, dash in [(-3, "#3D5AFE", "dot"), (-2, "#3D5AFE", "dash"), (3, "#00FBFF", "dot"), (2, "#00FBFF", "dash")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)
    
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1), row=2, col=1)

    # Teu Preenchimento Original (0.7 opacity)
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl_z'] <= -2.0, data['anupl_z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.7)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['anupl_z'] >= 2.0, data['anupl_z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.7)', line=dict(width=0), showlegend=False), row=2, col=1)

    # Layout Sincronizado
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    
    # Subplot 1: Escala Log (Conforme ACD)
    fig.update_yaxes(type="log", row=1, col=1, gridcolor="#222", title="BTC Price (Log)")
    
    # Subplot 2: Teu NUPL (Mantido conforme original)
    fig.update_yaxes(
        row=2, col=1, gridcolor="#222", 
        autorange='reversed', 
        range=[-3.8, 3.8], 
        tickvals=[-3, -2, -1, 0, 1, 2, 3],
        title="Institutional Sentiment (SD)"
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown(f"<p style='text-align: center; color: #444;'>Last update: {data.index[-1].strftime('%Y-%m-%d %H:%M:%S')} UTC</p>", unsafe_allow_html=True)

else:
    st.error("Erro na carga de dados.")
