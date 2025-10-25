"""
Utilidades comunes para procesamiento de velas de trading
Compartido entre todos los pipelines (Finnhub, IQ Option, OlympTrade)
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import time

class CandleNormalizer:
    """Normaliza velas de diferentes fuentes a formato estándar"""
    
    @staticmethod
    def normalize(candle: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normaliza una vela al formato estándar del sistema
        
        Formato estándar:
        {
            'time': int (timestamp unix),
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': float
        }
        """
        if source == 'finnhub':
            return {
                'time': int(candle.get('time', candle.get('t', 0))),
                'open': float(candle.get('open', candle.get('o', 0))),
                'high': float(candle.get('high', candle.get('h', 0))),
                'low': float(candle.get('low', candle.get('l', 0))),
                'close': float(candle.get('close', candle.get('c', 0))),
                'volume': float(candle.get('volume', candle.get('v', 0)))
            }
        
        elif source == 'iqoption':
            return {
                'time': int(candle.get('from', candle.get('time', 0))),
                'open': float(candle.get('open', 0)),
                'high': float(candle.get('max', candle.get('high', 0))),
                'low': float(candle.get('min', candle.get('low', 0))),
                'close': float(candle.get('close', 0)),
                'volume': float(candle.get('volume', 0))
            }
        
        elif source == 'olymptrade':
            return {
                'time': int(candle.get('timestamp', candle.get('time', 0))),
                'open': float(candle.get('open', 0)),
                'high': float(candle.get('high', 0)),
                'low': float(candle.get('low', 0)),
                'close': float(candle.get('close', 0)),
                'volume': float(candle.get('volume', 0))
            }
        
        else:
            raise ValueError(f"Fuente desconocida: {source}")
    
    @staticmethod
    def validate(candle: Dict[str, Any]) -> bool:
        """Valida que una vela tenga todos los campos requeridos"""
        required_fields = ['time', 'open', 'high', 'low', 'close']
        
        if not all(field in candle for field in required_fields):
            return False
        
        if candle['time'] <= 0:
            return False
        
        if candle['open'] <= 0 or candle['close'] <= 0:
            return False
        
        if candle['high'] < max(candle['open'], candle['close']):
            return False
        
        if candle['low'] > min(candle['open'], candle['close']):
            return False
        
        return True


class TimeframeHelper:
    """Utilidades para manejar timeframes"""
    
    TIMEFRAMES = {
        'M1': 60,
        'M5': 300,
        'M15': 900,
        'M30': 1800,
        'H1': 3600,
        'H4': 14400,
        'D': 86400,
        'W': 604800
    }
    
    @staticmethod
    def to_seconds(timeframe: str) -> int:
        """Convierte timeframe a segundos"""
        return TimeframeHelper.TIMEFRAMES.get(timeframe, 300)
    
    @staticmethod
    def round_timestamp(timestamp: int, timeframe: str) -> int:
        """Redondea timestamp al inicio del periodo del timeframe"""
        seconds = TimeframeHelper.to_seconds(timeframe)
        return (timestamp // seconds) * seconds
    
    @staticmethod
    def get_start_time(timeframe: str, limit: int) -> int:
        """Calcula timestamp de inicio para obtener N velas"""
        seconds = TimeframeHelper.to_seconds(timeframe)
        return int(time.time()) - (limit * seconds)
    
    @staticmethod
    def is_new_candle(last_time: int, current_time: int, timeframe: str) -> bool:
        """Detecta si es una nueva vela según el timeframe"""
        seconds = TimeframeHelper.to_seconds(timeframe)
        last_period = last_time // seconds
        current_period = current_time // seconds
        return current_period > last_period


class CandleFilter:
    """Filtros para velas"""
    
    @staticmethod
    def remove_duplicates(candles: List[Dict], key: str = 'time') -> List[Dict]:
        """Elimina velas duplicadas por timestamp"""
        seen = set()
        unique_candles = []
        
        for candle in candles:
            if candle[key] not in seen:
                seen.add(candle[key])
                unique_candles.append(candle)
        
        return unique_candles
    
    @staticmethod
    def sort_by_time(candles: List[Dict], ascending: bool = True) -> List[Dict]:
        """Ordena velas por timestamp"""
        return sorted(candles, key=lambda x: x['time'], reverse=not ascending)
    
    @staticmethod
    def filter_by_timerange(candles: List[Dict], start: int, end: int) -> List[Dict]:
        """Filtra velas por rango de tiempo"""
        return [c for c in candles if start <= c['time'] <= end]
    
    @staticmethod
    def limit_candles(candles: List[Dict], limit: int) -> List[Dict]:
        """Limita número de velas (más recientes)"""
        if len(candles) <= limit:
            return candles
        return candles[-limit:]


class SymbolMapper:
    """Mapeo de símbolos entre diferentes brokers"""
    
    MAPPINGS = {
        'finnhub': {
            'BTCUSD': 'BINANCE:BTCUSDT',
            'ETHUSD': 'BINANCE:ETHUSDT',
            'EURUSD': 'OANDA:EUR_USD',
            'EURJPY': 'OANDA:EUR_JPY',
            'GBPUSD': 'OANDA:GBP_USD',
            'USDJPY': 'OANDA:USD_JPY'
        },
        'iqoption': {
            'EURUSD': 'EURUSD',
            'EURUSD-OTC': 'EURUSD-OTC',
            'EURJPY': 'EURJPY',
            'EURJPY-OTC': 'EURJPY-OTC',
            'GBPUSD': 'GBPUSD',
            'USDJPY': 'USDJPY'
        },
        'olymptrade': {
            'EURUSD': 'EUR/USD',
            'EURJPY': 'EUR/JPY',
            'GBPUSD': 'GBP/USD',
            'USDJPY': 'USD/JPY',
            'BTCUSD': 'BTC/USD'
        }
    }
    
    @staticmethod
    def get_broker_symbol(symbol: str, source: str) -> str:
        """Obtiene el símbolo según el broker"""
        mappings = SymbolMapper.MAPPINGS.get(source, {})
        return mappings.get(symbol, symbol)
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """Normaliza símbolo al formato estándar (sin barras, sin sufijos)"""
        symbol = symbol.replace('/', '').replace('-OTC', '')
        return symbol.upper()
