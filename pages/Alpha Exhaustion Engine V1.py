import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
st.set_page_config(page_title="Alpha Exhaustion Engine V1", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid="stExpander"] {
        background-color: #161616;
        border: 1px solid #2A2A2A;
    }
    button[kind="primary"] {
        background-color: #FF9F43 !important; /* Laranja Tático para Reversão */
        color: #0F0F0F !important;
        font-weight: 800 !important;
        border: none !important;
        letter-spacing: 1px;
    }
    button[kind="primary"]:hover { background-color: #E68A00 !important; }
</style>
""", unsafe_allow_html=True)

TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- 2. DATA PIPELINE ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _resample_ohlcv(df, rule):
    df.index = pd.to_datetime(df.index).tz_localize(None)
    agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    return df.resample(rule).agg(agg_dict).dropna()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if not df.empty:
        return _flatten_columns(df)
    return pd.DataFrame()

# --- 3. CORE MATHEMATICS (EXHAUSTION ENGINE) ---
def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std().replace(0, np.nan)

def calculate_reversion_signals(df, timeframe, full_history=False):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    # 1. Rolling VWAP (Centro de Gravidade Institucional)
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    rolling_vwap = (typical_price * data['Volume']).rolling(20).sum() / data['Volume'].rolling(20).sum().replace(0, np.nan)
    
    # VWAP Distance Z-Score
    dist_vwap = (data['Close'] - rolling_vwap) / rolling_vwap
    dist_z = _rolling_zscore(dist_vwap, z_win)
    
    # 2. RSI Estatístico (Exaustão de Momentum)
    delta = data['Close'].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs.fillna(0)))
    rsi_z = _rolling_zscore(rsi, z_win)
    
    # 3. Bollinger 3rd Standard Deviation Stretch
    basis = data['Close'].rolling(20).mean()
    dev = data['Close'].rolling(20).std()
    upper_3 = basis + 3 * dev
    lower_3 = basis - 3 * dev
    
    bb_stretch = np.where(data['Close'] > upper_3, (data['Close'] - upper_3)/dev,
                 np.where(data['Close'] < lower_3, (data['Close'] - lower_3)/dev, 0))
    
    # 4. Cálculo da TENSÃO DO ELÁSTICO (0 a 100%)
    raw_tension = abs(dist_z.fillna(0)) * 0.4 + abs(rsi_z.fillna(0)) * 0.4 + abs(bb_stretch) * 0.2
    tension_score = 100 * np.tanh(raw_tension / 2.5)
    
    # Bias de Reversão: Se o preço está muito acima da VWAP, o Bias é SHORT
    bias = np.where(dist_z > 0, "SHORT (Overbought)", "LONG (Oversold)")
    
    data['Tension'] = tension_score.clip(0, 100)
    data['Bias'] = bias
    data['VWAP'] = rolling_vwap
    data['DistZ'] = dist_z.fillna(0)
    data['RSIZ'] = rsi_z.fillna(0)
    data['Upper3'] = upper_3
    data['Lower3'] = lower_3
    
    if full_history:
        return data.dropna()
    else:
        return data.iloc[-1:]

# --- 4. VISUAL ENGINE ---
def style_reversion_matrix(res_df):
    def tension_color(val):
        alpha = min(val / 100, 0.8)
        return f'background-color: rgba(255, 159, 67, {alpha}); color: white; font-weight: bold;'
    
    def bias_color(val):
        if "SHORT" in val: return 'color: #FF5C5C; font-weight: bold;'
        return 'color: #00FFAA; font-weight: bold;'

    return res_df.style.map(tension_color, subset=['Tension %']).map(bias_color, subset=['Target Bias']).format({
        'Tension %': '{:.1f}%', 'Price': '${:.2f}', 'VWAP Dist Z': '{:+.2f}', 'RSI Z': '{:+.2f}'
    })

def build_exhaustion_radar(res_df):
    fig = go.Figure()
    # Quadrantes de Reversão
    fig.add_shape(type="rect", x0=1.5, y0=1.5, x1=4, y1=4, fillcolor="rgba(255, 92, 92, 0.08)", line_width=0) # Danger Zone (Short)
    fig.add_shape(type="rect", x0=-4, y0=-4, x1=-1.5, y1=-1.5, fillcolor="rgba(0, 255, 170, 0.08)", line_width=0) # Capitulation (Long)

    # Cores baseadas no Bias
    colors = np.where(res_df['Target Bias'].str.contains("SHORT"), "#FF5C5C", "#00FFAA")

    fig.add_trace(go.Scatter(
        x=res_df['VWAP Dist Z'], y=res_df['RSI Z'],
        mode='markers+text', text=res_df['Asset'], textposition="top center",
        marker=dict(size=res_df['Tension %'] / 5, color=colors, line=dict(width=1, color='white')),
        hovertemplate="<b>%{text}</b><br>VWAP Dist Z: %{x:.2f}<br>RSI Z: %{y:.2f}<br>Tension: %{marker.size:.1f}%<extra></extra>"
    ))
    
    fig.update_layout(
        title="Rubber Band Radar (Exhaustion Zones)",
        xaxis=dict(title="Distance from VWAP (Z-Score)", range=[-4, 4], gridcolor="#222", zerolinecolor="white"),
        yaxis=dict(title="RSI Extremes (Z-Score)", range=[-4, 4], gridcolor="#222", zerolinecolor="white"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=500, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

# --- 5. MAIN DASHBOARD ---
st.title("⚡ Alpha Exhaustion Engine")
st.caption("Mean Reversion Quantitative Model | Rubber Band Tension Tracker")

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #FF9F43; letter-spacing: 2px;'>⚙️ REVERSION CENTER</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    
    watchlist_raw = st.text_area("📡 ACTIVE WATCHLIST (CSV)", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA, AMZN", height=90)
    tf = st.selectbox("⏱️ TIMEFRAME RESOLUTION", ["1h", "4h", "1d"], index=2)
    
    st.markdown("<hr style='border-color: #2A2A2A;'>", unsafe_allow_html=True)
    btn = st.button("EXECUTE EXHAUSTION SCAN", type="primary", use_container_width=True)

if 'rev_results' not in st.session_state: st.session_state['rev_results'] = pd.DataFrame()

if btn:
    results = []
    watchlist = [s.strip().upper() for s in watchlist_raw.split(",") if s.strip()]
    
    with st.spinner("Calculating Rubber Band Tension..."):
        for symbol in watchlist:
            try:
                period = "720d" if tf != '1d' else "10y"
                interval = "60m" if tf != "1d" else "1d"
                hist = fetch_market_data(symbol, period, interval)
                
                if tf == "4h" and not hist.empty:
                    hist = _resample_ohlcv(hist, '4h')
                
                if len(hist) > TF_LOOKBACKS.get(tf, 126) + 20:
                    last_row = calculate_reversion_signals(hist, tf, full_history=False)
                    results.append({
                        "Asset": symbol, "Price": last_row['Close'].values[0],
                        "Tension %": last_row['Tension'].values[0], 
                        "Target Bias": last_row['Bias'].values[0],
                        "VWAP Dist Z": last_row['DistZ'].values[0],
                        "RSI Z": last_row['RSIZ'].values[0]
                    })
            except Exception as e:
                continue

    if results:
        st.session_state['rev_results'] = pd.DataFrame(results).sort_values("Tension %", ascending=False)
    else:
        st.warning("Insufficient data.")

if not st.session_state['rev_results'].empty:
    res_df = st.session_state['rev_results']
    
    # --- HTML CARDS ADAPTADOS PARA REVERSÃO ---
    top_target = res_df.iloc[0]
    is_short = "SHORT" in top_target['Target Bias']
    target_color = "#FF5C5C" if is_short else "#00FFAA"
    
    st.markdown(f"""
    <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px;">
        <div style="flex: 1; background-color: #111; padding: 20px; border-radius: 8px; border: 1px solid {target_color}; border-bottom: 4px solid {target_color}; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Top Reversion Target</p>
            <h2 style="color: {target_color}; margin: 5px 0 0 0; font-size: 28px;">{top_target['Asset']} <span style="font-size: 16px;">({top_target['Tension %']:.1f}%)</span></h2>
        </div>
        <div style="flex: 1; background-color: #161616; padding: 20px; border-radius: 8px; border: 1px solid #2A2A2A; text-align: center; min-width: 200px;">
            <p style="color: #888; font-size: 13px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Action required</p>
            <h2 style="color: {target_color}; margin: 5px 0 0 0; font-size: 28px; letter-spacing: 2px;">PREPARE TO {top_target['Target Bias'].split(' ')[0]}</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Rubber Band Tension Matrix")
    st.dataframe(style_reversion_matrix(res_df), use_container_width=True, height=300)
    
    st.divider()
    
    st.markdown("""
    <div style="padding: 12px 20px; background-color: #161616; border-left: 4px solid #FF9F43; border-radius: 4px; margin-bottom: -15px;">
        <span style="color: #EAF2FF; font-weight: bold; font-size: 16px;">🎯 SNAPBACK RADAR:</span>
        <span style="color: #A0AEC0; font-size: 14px;"> <b>Cima Direita (Vermelho):</b> Extrema Sobrecompra (Alvo Short) &nbsp;|&nbsp; <b>Baixo Esquerda (Verde):</b> Pânico Extremo (Alvo Long)</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.plotly_chart(build_exhaustion_radar(res_df), use_container_width=True, config={'displayModeBar': False})
