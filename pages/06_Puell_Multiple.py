@st.cache_data(ttl=3600)
def fetch_puell_pro_clean_engine():
    try:
        # 1. Método Alternativo de Download (Mais estável em 2026)
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(period="max")
        
        if df.empty: 
            return pd.DataFrame()

        # 2. Extração Direta e Limpeza Total
        # O .history() traz colunas simples, mas vamos garantir
        data = pd.DataFrame()
        data['price'] = df['Close']
        data.index = pd.to_datetime(df.index).tz_localize(None)

        # 3. Lógica de Recompensa (Protocolo Bitcoin)
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            elif d < pd.Timestamp('2016-07-09'): return 25.0
            elif d < pd.Timestamp('2020-05-11'): return 12.5
            elif d < pd.Timestamp('2024-04-20'): return 6.25
            else: return 3.125 
            
        data['reward'] = [get_reward(d) for d in data.index]
        data['issuance_usd'] = data['reward'] * 144 * data['price']
        
        # 4. Ajuste de Emissão e Cálculo do Puell
        # Usamos 365 dias para a média móvel da emissão (Padrão Puell)
        data['ma_issuance'] = data['issuance_usd'].rolling(window=365).mean()
        data['puell_raw'] = data['issuance_usd'] / data['ma_issuance']
        
        # 5. Normalização Z-Score (Janela 350 dias para capturar ciclos macro)
        # Substituímos zeros e infs por NaN e limpamos
        data['puell_raw'] = data['puell_raw'].replace([np.inf, -np.inf, 0], np.nan)
        data['log_p'] = np.log(data['puell_raw']).ffill()
        
        window = 350
        data['mean'] = data['log_p'].rolling(window=window).mean()
        data['std'] = data['log_p'].rolling(window=window).std()
        
        # Cálculo do Z: (Média - Atual) / Desvio
        # Nota: Invertemos para o padrão Alpha (Capitulação no Topo do Gráfico)
        data['z'] = ((data['mean'] - data['log_p']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna(subset=['z', 'price'])
        
    except Exception as e:
        # Se falhar, o Streamlit vai mostrar o erro exato nos logs
        print(f"CRITICAL ERROR: {e}")
        return pd.DataFrame()
