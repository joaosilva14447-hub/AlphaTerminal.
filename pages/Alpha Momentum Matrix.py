import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PAGE SETUP & INSTITUTIONAL THEME ---
# Removido o try/except preguiçoso. O código tem de rodar perfeito ou quebrar alto.
st.set_page_config(page_title="Alpha Momentum Matrix V5.1", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }
    div[data-testid="stExpander"] {
        background-color: #161616;
        border: 1px solid #2A2A2A;
    }
</style>
""", unsafe_allow_html=True)

TF_LOOKBACKS = {"1h": 240, "4h": 180, "1d": 126}

# --- 2. DATA PIPELINE & CACHING (ANTI-BAN) ---
def _flatten_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Função crítica para evitar Data Leakage no 4H
def _resample_ohlcv(df, rule):
    # Garantir que o index é datetime com timezone removido para consistência
    df.index = pd.to_datetime(df.index).tz_localize(None)
    agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    return df.resample(rule).agg(agg_dict).dropna()

# Cache de 5 minutos para poupar recursos da API e tornar o dashboard ultra-rápido
@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if not df.empty:
        return _flatten_columns(df)
    return pd.DataFrame()

# --- 3. CORE MATHEMATICS (V5.1 CONTINUOUS ENGINE) ---
def _rolling_zscore(series, window):
    return (series - series.rolling(window).mean()) / series.rolling(window).std()

def calculate_signals_v5_1(df, timeframe, full_history=False):
    data = df.copy()
    z_win = TF_LOOKBACKS.get(timeframe, 126)
    
    ema20 = data['Close'].ewm(span=20, adjust=False).mean()
    ema200 = data['Close'].ewm(span=200, adjust=False).mean()
    
    # ATR & Squeeze Logic
    tr = pd.concat([(data['High'] - data['Low']), 
                    (data['High'] - data['Close'].shift(1)).abs(), 
                    (data['Low'] - data['Close'].shift(1)).abs()], axis=1).max(axis=1)
    atr20 = tr.ewm(alpha=1/20, adjust=False).mean()
    
    sqz_on = (data['Close'].rolling(20).std() * 2.0 < 1.5 * atr20)
    
    # Squeeze Decay Factor
    fired_counter = (~sqz_on).groupby(sqz_on.cumsum()).cumsum()
    sqz_decay = np.where((~sqz_on) & (fired_counter <= 5), (6 - fired_counter) / 5, 0)
    
    # Normalized Momentum
    mom_raw = (data['Close'] - ema20) / atr20.replace(0, np.nan)
    mom_smooth = mom_raw.ewm(span=5).mean()
    mom_z = _rolling_zscore(mom_smooth, z_win)
    
    # Acceleration (Vulnerabilidade Corrigida: Suavização HFT)
    acc_raw = mom_z.diff().ewm(span=3, adjust=False).mean()
    acc_z = _rolling_zscore(acc_raw, z_win)
    
    # RVOL (Vulnerabilidade Corrigida: Proteção de Inf/NaN)
    vol_mean = data['Volume'].rolling(20).mean().replace(0, np.nan)
    rvol = (data['Volume'] / vol_mean).replace([np.inf, -np.inf, 0], np.nan)
    rvol_z = _rolling_zscore(np.log(rvol), z_win)

    # Adaptive Weighting
    w_mom, w_acc, w_vol = (0.45, 0.40, 0.15) if timeframe != '1d' else (0.55, 0.30, 0.15)
    
    raw = (w_mom * mom_z.clip(-3, 3) + w_acc * acc_z.clip(-3, 3) + w_vol * rvol_z.clip(-3, 3) * np.sign(mom_z.fillna(0)))
    bias = np.where(sqz_decay > 0, np.sign(mom_z.fillna(0)) * 0.25 * sqz_decay, 0)
    
    # Regime Contínuo (Risco Overfit Corrigido: Substituída step-function por Tanh)
    slope_z = _rolling_zscore(ema200.diff(), z_win)
    regime_bias = 0.3 * np.tanh(slope_z.fillna(0) / 2.0)
    
    score = 50.0 + 40.0 * np.tanh((raw + bias + regime_bias) / 2.0)
    
    data['Score'] = score.fillna(50.0)
    data['MomZ'] = mom_z.fillna(0)
    data['AccZ'] = acc_z.fillna(0)
    data['RVOL'] = rvol.fillna(1.0)
    data['Squeeze'] = sqz_on
    data['EMA20'] = ema20
    data['EMA200'] = ema200
    
    if full_history:
        return data.dropna()
    else:
        return data.iloc[-1:]

# --- 4. VISUAL ENGINE ---
def style_matrix(res_df):
    def score_color(val):
        alpha = min(abs(val - 50) / 40, 0.6)
        color = f"rgba(0, 255, 170, {alpha})" if val > 50 else f"rgba(255, 92, 92, {alpha})"
        return f'background-color: {color}; color: white; font-weight: bold;'

    return res_df.style.map(score_color, subset=['Score']).format({
        'Score': '{:.1f}', 'Price': '${:.2f}', 'MomZ': '{:+.2f}', 'AccZ': '{:+.2f}', 'RVOL': '{:.2f}x'
    })

def build_rotation_radar(res_df):
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=3.5, y1=3.5, fillcolor="rgba(0, 255, 170, 0.05)", line_width=0)
    fig.add_shape(type="rect", x0=-3.5, y0=-3.5, x1=0, y1=0, fillcolor="rgba(255, 92, 92, 0.05)", line_width=0)

    fig.add_trace(go.Scatter(
        x=res_df['MomZ'], y=res_df['AccZ'],
        mode='markers+text', text=res_df['Asset'], textposition="top center",
        marker=dict(size=res_df['RVOL'].clip(1, 3) * 12, color=res_df['Score'],
                    colorscale=[[0, '#FF5C5C'], [0.5, '#444'], [1, '#00FFAA']],
                    line=dict(width=1, color='white'), showscale=True),
        hovertemplate="<b>%{text}</b><br>MomZ: %{x:.2f}<br>AccZ: %{y:.2f}<extra></extra>"
    ))
    fig.update_layout(
        title="Alpha Rotation Radar (Continuous Matrix)",
        xaxis=dict(title="Momentum Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        yaxis=dict(title="Smoothed Accel Z-Score", range=[-3.5, 3.5], gridcolor="#222", zerolinecolor="white"),
        paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=500, margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def build_deep_inspection_chart(symbol, df):
    df_plot = df.tail(200)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.25, 0.25])

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'], name="Price", line=dict(color="#EAF2FF", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA20'], name="EMA20", line=dict(color="#00FFAA", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA200'], name="EMA200", line=dict(color="#0055FF", width=1.5)), row=1, col=1)

    sqz_starts = df_plot[df_plot['Squeeze'] & ~df_plot['Squeeze'].shift(1).fillna(False)].index
    sqz_ends = df_plot[~df_plot['Squeeze'] & df_plot['Squeeze'].shift(1).fillna(False)].index
    
    for start in sqz_starts:
        end = sqz_ends[sqz_ends > start]
        end_time = end[0] if len(end) > 0 else df_plot.index[-1]
        for r in [1, 2, 3]:
            fig.add_vrect(x0=start, x1=end_time, fillcolor="rgba(0, 85, 255, 0.1)", line_width=0, row=r, col=1)

    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['MomZ'], name="MomZ", line=dict(color="#00FFAA", width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['AccZ'], name="AccZ", line=dict(color="#0055FF", width=1.5, dash='dot')), row=2, col=1)
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1), row=2, col=1)

    # Cores de Volume dinâmicas para mostrar a direção do fluxo institucional
    close_delta = df_plot['Close'].diff()
    colors = np.where((df_plot['RVOL'] > 1.2) & (close_delta > 0), "#00FFAA", 
                      np.where((df_plot['RVOL'] > 1.2) & (close_delta < 0), "#FF5C5C", "#444"))
    
    fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['RVOL'], name="RVOL", marker_color=colors), row=3, col=1)
    fig.add_hline(y=1, line=dict(color="rgba(255,255,255,0.3)", width=1), row=3, col=1)

    fig.update_layout(
        title=f"🛡️ Deep Inspection: {symbol}", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F",
        height=700, showlegend=False, margin=dict(l=20, r=20, t=60, b=20)
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

# --- 5. MAIN DASHBOARD ---
st.title("🛡️ Alpha Momentum Matrix V5.1")
st.caption("Quantitative Engine Active | Hedged against Data Leakage & Overfitting")

with st.sidebar:
    st.header("Terminal Config")
    watchlist_raw = st.text_area("Watchlist", "BTC-USD, ETH-USD, SOL-USD, GC=F, NQ=F, TSLA, NVDA, AMZN")
    tf = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=2)
    btn = st.button("RUN QUANT SCAN")

if 'results_df' not in st.session_state: st.session_state['results_df'] = pd.DataFrame()

if btn:
    results = []
    watchlist = [s.strip().upper() for s in watchlist_raw.split(",") if s.strip()]
    
    with st.spinner("Processing Matrix..."):
        for symbol in watchlist:
            try:
                # 720d evita o hard limit de 730d do yfinance
                period = "720d" if tf != '1d' else "10y"
                interval = "60m" if tf != "1d" else "1d"
                
                # Fetch usando a cache
                hist = fetch_market_data(symbol, period, interval)
                
                # Resampling crítico para 4H
                if tf == "4h" and not hist.empty:
                    hist = _resample_ohlcv(hist, '4h')
                
                if len(hist) > TF_LOOKBACKS.get(tf, 126) + 20:
                    last_row = calculate_signals_v5_1(hist, tf, full_history=False)
                    results.append({
                        "Asset": symbol, "Price": last_row['Close'].values[0],
                        "Score": last_row['Score'].values[0], "MomZ": last_row['MomZ'].values[0],
                        "AccZ": last_row['AccZ'].values[0], "RVOL": last_row['RVOL'].values[0],
                        "Squeeze": "🔴 ON" if last_row['Squeeze'].values[0] else "🟢 OFF"
                    })
            except Exception as e:
                continue

    if results:
        st.session_state['results_df'] = pd.DataFrame(results).sort_values("Score", ascending=False)
    else:
        st.warning("Insufficient clean data retrieved.")

if not st.session_state['results_df'].empty:
    res_df = st.session_state['results_df']
    
    col1, col2, col3 = st.columns(3)
    top_asset = res_df.iloc[0]
    col1.metric("Top Alpha Pick", top_asset['Asset'], f"{top_asset['Score']:.1f}")
    col2.metric("Market Sentiment", "BULLISH" if res_df['Score'].mean() > 50 else "BEARISH")
    col3.metric("Squeeze Alerts", len(res_df[res_df['Squeeze'] == "🔴 ON"]))
    
    st.divider()
    st.dataframe(style_matrix(res_df), use_container_width=True, height=300)
    st.divider()
    st.plotly_chart(build_rotation_radar(res_df), use_container_width=True, config={'displayModeBar': False})
    st.divider()
    
    st.subheader("Asset Deep Inspection")
    target = st.selectbox("Select asset:", res_df['Asset'].tolist())
    
    if target:
        period = "720d" if tf != '1d' else "5y"
        interval = "60m" if tf != "1d" else "1d"
        target_hist = fetch_market_data(target, period, interval)
        
        if tf == "4h" and not target_hist.empty:
            target_hist = _resample_ohlcv(target_hist, '4h')
            
        if len(target_hist) > 200:
            full_sigs = calculate_signals_v5_1(target_hist, tf, full_history=True)
            st.plotly_chart(build_deep_inspection_chart(target, full_sigs), use_container_width=True, config={'displayModeBar': False})
