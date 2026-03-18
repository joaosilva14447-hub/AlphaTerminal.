import pandas as pd
import numpy as np
import yfinance as yf

class AlphaSentinelRegime:
    def __init__(self, tickers):
        self.tickers = tickers
        self.results = []

    def get_data(self, ticker, period="1y", interval="1d"):
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        return data

    def calculate_regime(self, df):
        """Define o Estado de Mercado através de Volatilidade e Tendência"""
        # Volatilidade Relativa (ATR / Price)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean()
        
        # Regime Score
        vol_regime = "𝓔𝔁𝓹𝓪𝓷𝓼𝓲𝓸𝓷" if atr.iloc[-1] > atr.rolling(30).mean().iloc[-1] else "𝓒𝓸𝓷𝓽𝓻𝓪𝓬𝓽𝓲𝓸𝓷"
        return vol_regime

    def calculate_alpha_matrix(self, df):
        """A nossa lógica v6 traduzida para Python"""
        close = df['Close']
        volume = df['Volume']
        
        # Momentum Ponderado por Volume
        roc = close.pct_change(14)
        vol_avg = volume.rolling(20).mean()
        vol_weight = np.clip(volume / vol_avg, 0.35, 2.5)
        
        # Core Momentum (Normalizado via RSI)
        mom_core = (roc * vol_weight).ewm(span=5).mean()
        
        # Simulação de RSI para normalização (0-100)
        delta = mom_core.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        normalized_mom = 100 - (100 / (1=rs))
        
        # 𝓣𝓱𝓮 𝓗𝓸𝓸𝓴 (Curvatura)
        curr_mom = normalized_mom.iloc[-1]
        prev_mom = normalized_mom.iloc[-2]
        is_hook_up = curr_mom < 30 and curr_mom > prev_mom
        is_hook_down = curr_mom > 70 and curr_mom < prev_mom
        
        return curr_mom, is_hook_up, is_hook_down

    def run_scan(self):
        print(f"{'='*50}")
        print(f"✦ 𝓐𝓵𝓹𝓱𝓪 𝓢𝓮𝓷𝓽𝓲𝓷𝓮𝓵 𝓡𝓮𝓰𝓲𝓶𝓮 𝓿1.0 ✦")
        print(f"{'='*50}\n")
        
        for ticker in self.tickers:
            try:
                df = self.get_data(ticker)
                if df.empty: continue
                
                regime = self.calculate_regime(df)
                mom_val, hook_up, hook_down = self.calculate_alpha_matrix(df)
                
                # Lógica de Execução Estilizada
                signal = "𝓝𝓮𝓾𝓽𝓻𝓪𝓵"
                if mom_val <= 30 and hook_up and regime == "𝓒𝓸𝓷𝓽𝓻𝓪𝓬𝓽𝓲𝓸𝓷":
                    signal = "𝓢𝓽𝓻𝓸𝓷𝓰 𝓑𝓾𝔂 (𝓑𝓸𝓽𝓽𝓸𝓶)"
                elif mom_val >= 75 and hook_down:
                    signal = "𝓣𝓪𝴴𝓮 𝓟𝓻𝓸𝓯𝓲𝓽"
                elif mom_val < 50 and regime == "𝓔𝔁𝓹𝓪𝓷𝓼𝓲𝓸𝓷":
                    signal = "𝓐𝓬𝓬𝓾𝓶𝓾𝓵𝓪𝓽𝓲𝓷𝓰"

                print(f"Asset: {ticker:<10} | Regime: {regime:<15} | Signal: {signal}")
            except Exception as e:
                print(f"Error scanning {ticker}: {e}")

# --- EXECUÇÃO ---
# Lista Multi-Mercado: Stocks, Crypto, Commodities, Forex
mercado_global = ["MU", "GEV", "BTC-USD", "ETH-USD", "GC=F", "EURUSD=X", "NVDA", "VRT"]
scanner = AlphaSentinelRegime(mercado_global)
scanner.run_scan()
