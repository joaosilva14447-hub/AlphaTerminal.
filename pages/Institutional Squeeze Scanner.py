import streamlit as st

# Configuração da Página
st.set_page_config(page_title="Institutional Trend Scanner (ADX)", layout="wide")

# Estilos Customizados (CSS)
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
    }
    .stMarkdown {
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# Título e Cabeçalho
st.title("⚖️ Institutional Trend Scanner (ADX)")

# Simulação de Dados (Substitua pela sua lógica de integração com API/CCXT se necessário)
ativo = "BTC-USD"
tf = "15m"
status_trend = "RANGING"
direcao = "BULLISH"
adx_val = 13.72
bg_color = "#00E676" if direcao == "BULLISH" else "#FF5252"

# Layout de Exibição
st.write(f"**Ativo:** {ativo}")
st.write(f"**TF:** {tf}")
st.subheader(status_trend)

col1, col2 = st.columns(2)
with col1:
    st.write(f"**Direção:** {direcao}")
with col2:
    st.write(f"**Força (ADX):** {adx_val}")

# Barra de Progresso (Visualização do ADX)
st.progress(min(adx_val / 100, 1.0))

# --- CORREÇÃO DO ERRO DE INDENTAÇÃO E MARKDOWN ---
# O erro anterior era causado por 'unsafe_html' (incorreto) e falta de alinhamento
st.markdown(f"""
<div style="padding:10px; border-left: 5px solid {bg_color}; background-color: #1E1E1E; border-radius: 4px; margin-top: 20px;">
    <span style="color:white; font-weight: bold;">Sinal Institucional Ativo</span>
</div>
""", unsafe_allow_html=True)

# Rodapé ou Informações Adicionais
st.divider()
st.caption("Alpha Terminal - Institutional Squeeze Scanner v1.0")
