"""Quick test of public API endpoint (no authentication)."""
from bot.client import BinanceFuturesClient

client = BinanceFuturesClient()
info = client.get('/fapi/v1/exchangeInfo', signed=False)
print(f"✅ Successfully connected to Binance Futures Testnet!")
print(f"Trading pairs available: {len(info['symbols'])}")
print(f"Sample pairs: {', '.join([s['symbol'] for s in info['symbols'][:5]])}")
