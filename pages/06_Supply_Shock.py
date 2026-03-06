import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração Master de Elite
st.set_page_config(page_title="05 Supply Shock Terminal", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] { background-color: #161616; padding: 20px; border-radius: 5px; border: 1px solid #333; }
    h1 { font-family: serif; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def fetch_supply_shock_consistent_engine():
    try:
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()

        # Extração Robusta
        price = df['Close']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Close']
        volume = df['Volume']['BTC-USD'] if isinstance(df.columns, pd.MultiIndex) else df['Volume']
        
        data = pd.DataFrame({'price': price, 'volume': volume})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # --- MOTOR ILLIQUIDITY RATIO ---
        data['returns'] = data['price'].pct_change().abs()
        data['vol_ma'] = data['volume'].rolling(window=20).mean()
        
        data['shock_raw'] = data['returns'] / (data['vol_ma'] / data['price'])
        
        # 1. Compressão Logarítmica
        data['log_shock'] = np.log(data['shock_raw'].replace(0, np.nan)).ffill()
        
        # 2. Motor Z-Score (Janela 350 dias)
        window = 350
        data['mean'] = data['log_shock'].rolling(window=window).mean()
        data['std'] = data['log_shock'].rolling(window=window).std()
        
        # --- INVERSÃO ALPHA BLINDADA (PADRONIZAÇÃO) ---
        # Queremos que DOR (Choque de Oferta) = Z Positivo = Aqua (Cima)
        # Queremos que PRAZER (Excesso de Oferta) = Z Negativo = Blue (Baixo)
        data['z'] = ((data['mean'] - data['log_shock']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except Exception as e:
        st.error(f"Engine Alert: {str(e)}")
        return pd.DataFrame()

data = fetch_supply_shock_consistent_engine()

if not data.empty:
    last_z = data['z'].iloc[-1]
    
    # Cores Institucionais
    AQUA = "#00FBFF"
    BLUE = "#3D5AFE"
    WHITE = "#FFFFFF"

    st.markdown(f"<h1 style='text-align: center; color: {BLUE};'>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓔𝔁𝓬𝓱𝓪𝓷𝓰𝓮 𝓢𝓾𝓹𝓹𝓵𝔂 𝓢𝓱𝓸𝓬𝓴 ✦</h1>", unsafe_allow_html=True)

    # --- MATRIZ DE SENTIMENTO GRANULAR (Cores Padronizadas) ---
    status, s_color = "NEUTRAL", WHITE
    if last_z >= 2.0: status, s_color = "💎 EXTREME SCARCITY (BULLISH SHOCK)", AQUA
    elif 1.0 <= last_z < 2.0: status, s_color = "🔹 LOW LIQUIDITY", "rgba(0, 251, 255, 0.7)"
    elif last_z <= -2.0: status, s_color = "🔴 SUPPLY OVERLOAD (DISTRIBUTION)", BLUE
    elif -2.0 < last_z <= -1.0: status, s_color = "🔸 HIGH LIQUIDITY / AGGRESSIVE", "rgba(61, 90, 254, 0.7)"

    c1, c2, c3 = st.columns([1, 1, 1.8])
    c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
    c2.metric("SHOCK Z-SCORE", f"{last_z:.2f} SD")
    c3.markdown(f"<h1 style='text-align: right; color: {s_color}; font-size: 24px; margin-top: -5px;'>{status}</h1>", unsafe_allow_html=True)

    # Plot Construction
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])
    fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

    # Linhas de Escala Standard
    for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                             (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
        fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

    # Fills 0.4 Opacidade
    fig.add_trace(go.Scatter(x=data.index, y=[-2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor='rgba(61, 90, 254, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=[2.0]*len(data), line=dict(width=0), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor='rgba(0, 251, 255, 0.4)', line=dict(width=0), showlegend=False), row=2, col=1)

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=1000, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
    fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
    # INVERSÃO ALPHA: DOR/AQUA EM CIMA
    fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.3, 3.3], tickvals=[-3, -2, -1, 0, 1, 2, 3])
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
