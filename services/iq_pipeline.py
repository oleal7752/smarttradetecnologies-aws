"""
Pipeline específico para IQ Option API
Maneja obtención y procesamiento de datos para TRADING de opciones binarias
"""
import os
from typing import List, Dict, Optional
from services.candle_pipeline_base import CandlePipelineBase
from services.candle_utils import SymbolMapper, TimeframeHelper

class IQCandlePipeline(CandlePipelineBase):
    """Pipeline para IQ Option (trading de binarias)"""
    
    def __init__(self, iq_instance=None):
        super().__init__(source='iqoption')
        self.iq = iq_instance
        self.symbol_mapper = SymbolMapper()
    
    def set_iq_instance(self, iq_instance):
        """Establece instancia de IQ Option WebSocket"""
        self.iq = iq_instance
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convierte timeframe al formato de IQ Option (minutos)"""
        mapping = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240
        }
        return mapping.get(timeframe, 5)
    
    def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """Obtiene velas desde IQ Option WebSocket"""
        if not self.iq or not self.iq.check_connect():
            print(f"⚠️ IQ Option: No conectado, no se pueden obtener velas de {symbol}")
            return None
        
        try:
            minutes = self._timeframe_to_minutes(timeframe)
            
            end_time = int(TimeframeHelper.get_start_time(timeframe, 0))
            start_time = TimeframeHelper.get_start_time(timeframe, limit)
            
            candles_data = self.iq.get_candles(symbol, minutes, limit, end_time)
            
            if not candles_data:
                print(f"⚠️ IQ Option: No hay velas para {symbol} {timeframe}")
                return None
            
            candles = []
            for candle in candles_data:
                candles.append({
                    'from': int(candle.get('from', candle.get('time', 0))),
                    'open': float(candle.get('open', 0)),
                    'max': float(candle.get('max', candle.get('high', 0))),
                    'min': float(candle.get('min', candle.get('low', 0))),
                    'close': float(candle.get('close', 0)),
                    'volume': float(candle.get('volume', 0))
                })
            
            print(f"✅ IQ Option: {len(candles)} velas de {symbol}")
            return candles
            
        except Exception as e:
            print(f"❌ IQ Option Error para {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene precio actual desde IQ Option"""
        if not self.iq or not self.iq.check_connect():
            return None
        
        try:
            price_data = self.iq.get_digital_current_profit(symbol, 1)
            
            if price_data:
                return {
                    'symbol': symbol,
                    'price': price_data,
                    'timestamp': int(TimeframeHelper.get_start_time('M1', 0))
                }
            return None
            
        except Exception as e:
            print(f"❌ IQ Option Price Error: {e}")
            return None
    
    def get_balance(self) -> Optional[float]:
        """Obtiene balance de la cuenta IQ Option"""
        if not self.iq or not self.iq.check_connect():
            return None
        
        try:
            balance = self.iq.get_balance()
            return float(balance) if balance else None
        except Exception as e:
            print(f"❌ IQ Option Balance Error: {e}")
            return None
    
    def execute_trade(self, symbol: str, amount: float, direction: str, duration: int) -> Optional[Dict]:
        """
        Ejecuta operación en IQ Option
        
        Args:
            symbol: Par de divisas
            amount: Monto a invertir
            direction: 'call' o 'put'
            duration: Duración en minutos
        """
        if not self.iq or not self.iq.check_connect():
            return {'success': False, 'error': 'No conectado a IQ Option'}
        
        try:
            action = direction.lower()
            result = self.iq.buy(amount, symbol, action, duration)
            
            if result:
                return {
                    'success': True,
                    'trade_id': result.get('id'),
                    'amount': amount,
                    'direction': direction,
                    'duration': duration,
                    'timestamp': int(TimeframeHelper.get_start_time('M1', 0))
                }
            else:
                return {'success': False, 'error': 'Error ejecutando trade'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
