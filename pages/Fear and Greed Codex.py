# --- AJUSTE NO GAUGE (Dentro do with col1) ---
gauge_fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=current_val,
    title={"text": f"Current Sentiment: {current_status}", "font": {"color": color, "size": 24}},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": "white"},
        "bar": {"color": "white", "thickness": 0.2}, # Ponteiro limpo
        "bgcolor": "rgba(255,255,255,0.03)",
        "steps": [
            {"range": [0, 20], "color": "#FF4B4B", "thickness": 1}, # Sólido como pedido
            {"range": [80, 100], "color": "#00E5FF", "thickness": 1} # Sólido como pedido
        ],
    },
))

# --- AJUSTE NO HISTÓRICO (Cálculo de SMA) ---
df_hist["sma7"] = df_hist["value"].rolling(window=7).mean()

# No Trace do F&G (Linha principal)
fig_hist.add_trace(go.Scatter(
    x=df_hist["timestamp"],
    y=df_hist["sma7"],
    mode="lines",
    name="7D Trend (SMA)",
    line=dict(color="rgba(199,208,219,0.3)", width=1, dash="dot"), # Linha de tendência suave
))
