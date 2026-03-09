@st.cache_data(ttl=3600)
def fetch_puell_pro_clean_engine():
    try:
        # 1. Download de Dados com tratamento MultiIndex Robusto
        df = yf.download("BTC-USD", period="max", interval="1d", progress=False)
        if df.empty: return pd.DataFrame()
        
        # Correção Crítica: Achatamos o MultiIndex para garantir que 'Close' é encontrado
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        price = df['Close']
        data = pd.DataFrame({'price': price})
        data.index = pd.to_datetime(data.index).tz_localize(None)

        # 2. Lógica de Recompensa de Bloco (Halvings)
        def get_reward(d):
            if d < pd.Timestamp('2012-11-28'): return 50.0
            elif d < pd.Timestamp('2016-07-09'): return 25.0
            elif d < pd.Timestamp('2020-05-11'): return 12.5
            elif d < pd.Timestamp('2024-04-20'): return 6.25
            else: return 3.125 # Recompensa atual
            
        data['reward'] = [get_reward(d) for d in data.index]
        data['issuance_usd'] = data['reward'] * 144 * data['price']
        
        # 3. Diferenciação e Limpeza de Dados
        vol = data['price'].pct_change().rolling(window=30).std()
        data['adj_issuance'] = data['issuance_usd'] / (1 + vol.fillna(0))
        
        # 4. Cálculo do Rácio (Puell) e Normalização
        data['ma_issuance'] = data['adj_issuance'].rolling(window=365).mean()
        data['puell_raw'] = data['adj_issuance'] / data['ma_issuance']
        
        # Limpeza de zeros para evitar erros de Log
        data['puell_raw'] = data['puell_raw'].replace(0, np.nan).ffill()
        data['log_p'] = np.log(data['puell_raw'])
        
        window = 350
        data['mean'] = data['log_p'].rolling(window=window).mean()
        data['std'] = data['log_p'].rolling(window=window).std()
        
        # Z-Score Alpha: Inversão para manter o padrão Visual
        data['z'] = ((data['mean'] - data['log_p']) / data['std']).clip(-3.5, 3.5)
        
        return data.dropna()
    except Exception as e:
        st.error(f"Erro na Engine de Dados: {e}")
        return pd.DataFrame()
