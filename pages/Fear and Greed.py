import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import time

# Standard AlphaTerminal Configuration
st.set_page_config(page_title="Fear & Greed Official", layout="wide")

# Custom CSS for Institutional Styling and Perfectly Uniform Legend
st.markdown(
    """
<style>
    .main { background-color: #0F0F0F; }
    div[data-testid='stMetric'] {
        background-color: #161616;
        padding: 16px;
        border-radius: 6px;
        border: 1px solid #2A2A2A;
    }
    .stDataFrame { background-color: #161616; border-radius: 6px; }
    
    /* Legend Styles - Uniform height for all 5 lines */
    .legend-container {
        padding-top: 60px; /* Alinhamento vertical com o gráfico */
        padding-left: 20px;
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin-bottom: 12px;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        color: #C7D0DB;
    }
    .legend-line {
        width: 30px;
        height: 2.5px; /* Espessura padronizada para TODAS as linhas */
        margin-right: 12px;
        border-radius: 1px;
    }
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_data(ttl=3600, show_spinner=False)
def get_fng_data(limit=365):
    url = f"https://api.alternative.me/fng/?limit={limit}"
    max_retries = 3
    base_timeout = 10 
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=base_timeout)
            r.raise_for_status() 
            
            data = r.json()
            if "data" not in data:
                continue 
                
            df = pd.DataFrame(data["data"])
            df["value"] = df["value"].astype(int)
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="s")
            
            return df.sort_values("timestamp")
            
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2) 
                continue
            else:
                st.cache_data.clear()
                return None
                
    return None

def state_from_value(value: int):
    # Mapping logic enforcing Alpha Institutional Palette
    if value <= 25:
        return "Extreme Fear", "#00FFAA"
    elif value <= 40:
        return "Fear", "#00CC88"
    elif value <= 59:
        return "Neutral", "#FFCC00"
    elif value <= 74:
        return "Greed", "#FF6600"
    else:
        return "Extreme Greed", "#FF0000"

df_hist = get_fng_data(limit=365)

if df_hist is not None:
    # Data Preparation
    df_hist["details"] = df_hist["value"].apply(lambda v: state_from_value(int(v)))
    df_hist["state_label"] = df_hist["details"].apply(lambda x: x[0])
    df_hist["state_color"] = df_hist["details"].apply(lambda x: x[1])
    df_hist["date_label"] = df_hist["timestamp"].dt.strftime("%Y-%m-%d")

    current_row = df_hist.iloc[-1]
    prev_row = df_hist.iloc[-2] if len(df_hist) > 1 else current_row
    
    selected_val = int(current_row["value"])
    selected_status = current_row["state_label"]
    selected_color = current_row["state_color"]
    selected_delta = selected_val - int(prev_row["value"])

    st.title("Fear & Greed Index | Institutional Terminal")

    # --- TOP ROW: GAUGE & METRICS ---
    col1, col2 = st.columns([2, 1])
    with col1:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=selected_val,
            title={"text": f"{current_row['date_label']} | {selected_status}", "font": {"color": selected_color, "size": 22}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "white"},
                "bar": {"color": selected_color},
                "bgcolor": "rgba(0,0,0,0)",
                "steps": [
                    {"range": [0, 25], "color": "rgba(0, 255, 170, 0.15)"},
                    {"range": [25, 40], "color": "rgba(0, 204, 136, 0.12)"},
                    {"range": [40, 59], "color": "rgba(255, 204, 0, 0.1)"},
                    {"range": [59, 74], "color": "rgba(255, 102, 0, 0.12)"},
                    {"range": [74, 100], "color": "rgba(255, 0, 0, 0.15)"},
                ],
            }
        ))
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", font={"color": "white"}, height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        st.markdown("### Sentiment Delta")
        st.metric(label="Current Score", value=f"{selected_val} pts", delta=selected_delta)
        st.markdown("---")
        history_table = df_hist.tail(7)[["date_label", "value", "state_label"]].copy()
        history_table.columns = ["Date", "Score", "Classification"]
        # Updated to .map for newer pandas compatibility while maintaining exact logic
        st.dataframe(history_table.iloc[::-1].style.map(lambda v: f"color: {state_from_value(int(v))[1]}", subset=["Score"]), use_container_width=True, hide_index=True)

    # --- BOTTOM ROW: CHART + UPDATED BRIGHTNESS ZONES ---
    st.markdown("---")
    st.markdown("### Historical Sentiment Analysis")

    chart_col, legend_col = st.columns([8, 1])

    with chart_col:
        fig_hist = go.Figure()
        
        # High-Performance Density Interpolation Logic [CORRIGIDO]
        # Isolamos APENAS as colunas numéricas ('timestamp' e 'value') para evitar o TypeError nas colunas de texto
        df_dense = df_hist[['timestamp', 'value']].set_index('timestamp').resample('2h').interpolate(method='linear').reset_index()
        
        # Reconstruímos as cores da linha perfeitamente após o cálculo matemático
        df_dense["state_color"] = df_dense["value"].apply(lambda v: state_from_value(int(v))[1])
        
        # Group points by consecutive colors to build unified segments (prevents plot crashing)
        df_dense['color_block'] = (df_dense['state_color'] != df_dense['state_color'].shift()).cumsum()
        
        for block_id, group in df_dense.groupby('color_block'):
            # Append the first row of the next segment to eliminate microscopic visual gaps
            next_group = df_dense[df_dense['color_block'] == block_id + 1]
            segment = pd.concat([group, next_group.head(1)]) if not next_group.empty else group
            
            fig_hist.add_trace(go.Scatter(
                x=segment["timestamp"], y=segment["value"],
                mode="lines", line=dict(color=group.iloc[0]["state_color"], width=2.5),
                hoverinfo="skip", showlegend=False
            ))

        # Accuracy layer for hover consistency (snapping to original data points only)
        fig_hist.add_trace(go.Scatter(
            x=df_hist["timestamp"], y=df_hist["value"],
            mode="markers", marker=dict(color="rgba(0,0,0,0)", size=7),
            customdata=df_hist["state_label"],
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Value: %{y}<br>State: %{customdata}<extra></extra>",
            name="Sentiment"
        ))

        # Highlight current signal with a colored circle
        fig_hist.add_trace(go.Scatter(
            x=[current_row["timestamp"]],
            y=[current_row["value"]],
            mode="markers",
            marker=dict(color=selected_color, size=10, symbol="circle"),
            showlegend=False,
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Value: %{y}<br>State: "
                          + selected_status + "<extra></extra>",
        ))
        
        # Define visual zones mapped to Alpha Colors
        zones = [
            (0, 25, "#00FFAA", 0.2),
            (25, 40, "#00CC88", 0.04),
            (40, 59, "#FFCC00", 0.04),
            (59, 74, "#FF6600", 0.04),
            (74, 100, "#FF0000", 0.2)
        ]
        
        for y0, y1, color, op in zones:
            fig_hist.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=op, line_width=0)
        
        fig_hist.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=450, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], showgrid=True, gridcolor="#222222"),
            hovermode="x unified"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with legend_col:
        # Ordered items reflecting standard alpha logic
        st.markdown('<div class="legend-container">', unsafe_allow_html=True)
        legend_items = [
            ("Extreme Fear", "#00FFAA"),
            ("Fear", "#00CC88"),
            ("Neutral", "#FFCC00"),
            ("Greed", "#FF6600"),
            ("Extreme Greed", "#FF0000")
        ]
        for label, color in legend_items:
            st.markdown(f'''
                <div class="legend-item">
                    <div class="legend-line" style="background-color: {color};"></div>
                    {label}
                </div>
            ''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("API connection failed.")
