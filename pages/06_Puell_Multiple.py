# --- Lógica de Sinais Alpha (Hedge Fund Standard) ---
last_z = data['z'].iloc[-1]

# Matriz de Status Dinâmico
if last_z >= 2.0:
    status = "💎 MINER CAPITULATION (BUY)"
    s_color = AQUA
elif 1.0 <= last_z < 2.0:
    status = "🔹 REVENUE STRESS"
    s_color = "#99f9ff" # Aqua suavizado
elif last_z <= -2.0:
    status = "🔴 MINER EUPHORIA (SELL)"
    s_color = BLUE
elif -2.0 < last_z <= -1.0:
    status = "🔸 REVENUE EXPANSION"
    s_color = "#7c8efc" # Blue suavizado
else:
    status = "⚡ NEUTRAL"
    s_color = "#FFFFFF"

# Dashboard de Métricas
st.markdown(f"<h1>✦ 𝓑𝓲𝓽𝓬𝓸𝓲𝓷: 𝓟𝓾𝓮𝓵𝓵 𝓜𝓾𝓵𝓽𝓲𝓹𝓵𝓮 𝓩-𝓢𝓬𝓸𝓻𝓮 ✦</h1>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 1, 1.8])
c1.metric("LIVE BTC PRICE", f"${data['price'].iloc[-1]:,.2f}")
c2.metric("PUELL Z-SCORE", f"{last_z:.2f} SD")

# Injeção de Sinal com Cor Dinâmica em HTML Puro (Evita erros de renderização)
c3.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <span style="color: {s_color}; font-size: 26px; font-weight: bold; font-family: 'Courier New', monospace; text-shadow: 0px 0px 10px {s_color}44;">
            {status}
        </span>
    </div>
""", unsafe_allow_html=True)

# --- Construção do Gráfico Alpha ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.65, 0.35])

# Painel 1: Preço
fig.add_trace(go.Scatter(x=data.index, y=data['price'], name="Price", line=dict(color='white', width=2)), row=1, col=1)

# Painel 2: Oscilador Z-Score
fig.add_trace(go.Scatter(x=data.index, y=data['z'], name="Z-Score", line=dict(color='white', width=1.5)), row=2, col=1)

# Linhas de Fronteira Institucionais
for val, color, dash in [(-3, BLUE, "dot"), (-2, BLUE, "dash"), 
                         (3, AQUA, "dot"), (2, AQUA, "dash"), (0, "rgba(255,255,255,0.1)", "solid")]:
    fig.add_hline(y=val, line=dict(color=color, width=1.5, dash=dash), row=2, col=1)

# Preenchimento de Zonas Extremas (Shading)
fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] >= 2.0, data['z'], 2.0), fill='tonexty', fillcolor=f'rgba(0, 251, 255, 0.2)', line=dict(width=0), showlegend=False), row=2, col=1)
fig.add_trace(go.Scatter(x=data.index, y=np.where(data['z'] <= -2.0, data['z'], -2.0), fill='tonexty', fillcolor=f'rgba(61, 90, 254, 0.2)', line=dict(width=0), showlegend=False), row=2, col=1)

fig.update_layout(template="plotly_dark", paper_bgcolor="#0F0F0F", plot_bgcolor="#0F0F0F", height=900, margin=dict(l=60, r=60, t=50, b=60), showlegend=False)
fig.update_yaxes(type="log", row=1, col=1, showgrid=False)
fig.update_yaxes(row=2, col=1, showgrid=False, autorange='reversed', range=[-3.5, 3.5])

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
