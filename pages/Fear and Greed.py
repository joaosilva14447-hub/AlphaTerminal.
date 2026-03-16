with col1:
        import numpy as np

        # 1. Calculo da Trigonometria para a Agulha (Needle)
        # O gauge vai de 180 graus (valor 0) a 0 graus (valor 100)
        theta = 180 - (selected_val * 1.8)
        rad = np.deg2rad(theta)
        
        # Coordenadas da ponta da seta (ajustadas ao dominio do Plotly)
        x_ponta = 0.5 + 0.22 * np.cos(rad)
        y_ponta = 0.38 + 0.32 * np.sin(rad)
        
        fig = go.Figure(
            go.Indicator(
                mode="number", # Mudamos para number para usar o Gauge apenas como background
                value=selected_val,
                title={
                    "text": f"Sentiment: {selected_status}",
                    "font": {"color": selected_state_color, "size": 22},
                },
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
                    "bar": {"color": "rgba(0,0,0,0)"}, # Barra invisivel para realçar a seta
                    "bgcolor": "rgba(0,0,0,0)",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(255, 59, 48, 0.15)"},
                        {"range": [25, 50], "color": "rgba(255, 122, 69, 0.12)"},
                        {"range": [50, 55], "color": "rgba(245, 200, 75, 0.10)"},
                        {"range": [55, 75], "color": "rgba(60, 203, 127, 0.12)"},
                        {"range": [75, 100], "color": "rgba(0, 230, 118, 0.15)"},
                    ],
                },
            )
        )

        # 2. Adicionar a Seta (Needle) via Layout Shapes
        fig.update_layout(
            shapes=[
                # Linha da Agulha
                dict(
                    type='line',
                    x0=0.5, y0=0.38, # Centro do arco
                    x1=x_ponta, y1=y_ponta,
                    line=dict(color=selected_state_color, width=4)
                ),
                # Circulo Central (Pivot)
                dict(
                    type='circle',
                    x0=0.48, y0=0.35, x1=0.52, y1=0.41,
                    fillcolor='white',
                    line=dict(color=selected_state_color, width=2),
                )
            ],
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "white"},
            height=450,
            margin=dict(t=80, b=0, l=50, r=50)
        )
        
        # Overlay do arco do gauge (garante que os steps apareçam por trás da seta)
        fig.add_trace(go.Indicator(
            mode="gauge",
            value=selected_val,
            domain={'x': [0.1, 0.9], 'y': [0.1, 0.9]},
            gauge={
                'axis': {'range': [None, 100], 'visible': False},
                'bar': {'color': "rgba(0,0,0,0)"},
                'steps': [
                    {"range": [0, 25], "color": "rgba(255, 59, 48, 0.2)"},
                    {"range": [25, 50], "color": "rgba(255, 122, 69, 0.15)"},
                    {"range": [50, 55], "color": "rgba(245, 200, 75, 0.12)"},
                    {"range": [55, 75], "color": "rgba(60, 203, 127, 0.15)"},
                    {"range": [75, 100], "color": "rgba(0, 230, 118, 0.2)"},
                ],
            }
        ))

        st.plotly_chart(fig, use_container_width=True)
