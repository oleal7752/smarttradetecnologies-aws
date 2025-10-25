"""
Pipeline específico para Finnhub API
Maneja obtención y procesamiento de datos de cripto (BTC/ETH) para VISUALIZACIÓN
"""
import os
import finnhub
import time
from typing import List, Dict, Optional
from services.candle_pipeline_base import CandlePipelineBase
from services.candle_utils import SymbolMapper, TimeframeHelper

class FinnhubCandlePipeline(CandlePipelineBase):
    """Pipeline para datos REALES de Finnhub (solo visualización)"""
    
    def __init__(self):
        super().__init__(source='finnhub')
        self.api_key = os.getenv('FINNHUB_API_KEY')
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY no configurado")
        self.client = finnhub.Client(api_key=self.api_key)
        self.symbol_mapper = SymbolMapper()
    
    def _timeframe_to_resolution(self, timeframe: str) -> str:
        """Convierte timeframe al formato de Finnhub"""
        mapping = {
            'M1': '1',
            'M5': '5',
            'M15': '15',
            'M30': '30',
            'H1': '60',
            'H4': '240',
            'D': 'D',
            'W': 'W'
        }
        return mapping.get(timeframe, '5')
    
    def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """Obtiene velas desde Finnhub API"""
        try:
            finnhub_symbol = self.symbol_mapper.get_broker_symbol(symbol, 'finnhub')
            resolution = self._timeframe_to_resolution(timeframe)
            
            end_time = int(time.time())
            start_time = TimeframeHelper.get_start_time(timeframe, limit)
            
            print(f"🔍 Finnhub: {finnhub_symbol} | {resolution} | {start_time} → {end_time}")
            
            response = self.client.stock_candles(
                finnhub_symbol,
                resolution,
                start_time,
                end_time
            )
            
            if response['s'] == 'no_data':
                print(f"⚠️ Finnhub: No data para {symbol}")
                return None
            
            candles = []
            for i in range(len(response['t'])):
                candle = {
                    't': response['t'][i],
                    'o': response['o'][i],
                    'h': response['h'][i],
                    'l': response['l'][i],
                    'c': response['c'][i],
                    'v': response['v'][i] if 'v' in response else 0
                }
                candles.append(candle)
            
            print(f"✅ Finnhub: {len(candles)} velas REALES de {symbol}")
            return candles[-limit:] if len(candles) > limit else candles
            
        except Exception as e:
            print(f"❌ Finnhub Error para {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene precio actual desde Finnhub"""
        try:
            finnhub_symbol = self.symbol_mapper.get_broker_symbol(symbol, 'finnhub')
            quote = self.client.quote(finnhub_symbol)
            
            if quote and 'c' in quote:
                return {
                    'symbol': symbol,
                    'price': quote['c'],
                    'change': quote.get('d', 0),
                    'percent_change': quote.get('dp', 0),
                    'high': quote.get('h', 0),
                    'low': quote.get('l', 0),
                    'open': quote.get('o', 0),
                    'previous_close': quote.get('pc', 0),
                    'timestamp': int(time.time())
                }
            return None
            
        except Exception as e:
            print(f"❌ Finnhub Quote Error: {e}")
            return None
