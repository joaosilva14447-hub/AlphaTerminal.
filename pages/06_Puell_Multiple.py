@st.cache_data(ttl=3600)
def fetch_puell_pro_clean_engine():
    try:
        # 1. Download de Dados via CoinGecko (API Pública)
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max&interval=daily"
        response = requests.get(url).json()
        
        # Extração de Preços
        prices = response['prices']
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        if df.empty: return pd.DataFrame()
        
        # 2. Lógica de Recompensa de Bloco
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            elif d < pd.Timestamp('2016-07-09'): return 25.0
            elif d < pd.Timestamp('2020-05-11'): return 12.5
            elif d < pd.Timestamp('2024-04-20'): return 6.25
            else: return 3.125
            
        df['reward'] = [get_reward(d) for d in df.index]
        df['issuance_usd'] = df['reward'] * 144 * df['price']
        
        # 3. Cálculo do Puell Multiple (Média 365 dias)
        df['ma_issuance'] = df['issuance_usd'].rolling(window=365).mean()
        df['puell_raw'] = df['issuance_usd'] / df['ma_issuance']
        
        # 4. Normalização Z-Score (Janela 350 dias)
        df['log_p'] = np.log(df['puell_raw'].replace(0, np.nan)).ffill()
        window = 350
        df['mean'] = df['log_p'].rolling(window=window).mean()
        df['std'] = df['log_p'].rolling(window=window).std()
        
        # Inversão Alpha para o Gráfico
        df['z'] = ((df['mean'] - df['log_p']) / df['std']).clip(-3.5, 3.5)
        
        return df.dropna()
        
    except Exception as e:
        st.error(f"Erro Crítico de API: {e}")
        return pd.DataFrame()
