"""
Sistema de agregación de velas en tiempo real desde ticks
"""
from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, Optional, List, Dict
import time
import math


@dataclass
class Candle:
    """Estructura de una vela"""
    start_ts: int  # timestamp inicio ventana
    open: float
    high: float
    low: float
    close: float
    final: bool = False  # True cuando la vela se cierra
    volume: int = 0  # tick count como volumen


class CandleStore:
    """
    Almacena y agrega velas desde ticks individuales
    """
    def __init__(self, symbol: str, interval_sec: int = 60, max_history: int = 200):
        self.symbol = symbol
        self.interval_sec = interval_sec
        self.max_history = max_history
        
        # Deque para histórico de velas cerradas
        self.candles: Deque[Candle] = deque(maxlen=max_history)
        
        # Vela actual en construcción
        self.current_candle: Optional[Candle] = None
        self.current_window_start: Optional[int] = None
    
    def _get_window_start(self, ts: int) -> int:
        """Calcula el inicio de la ventana de tiempo para un timestamp"""
        return (ts // self.interval_sec) * self.interval_sec
    
    def add_tick(self, price: float, tick_ts: Optional[int] = None) -> Optional[Candle]:
        """
        Agrega un tick (precio) y retorna la vela cerrada si cambia la ventana.
        
        Returns:
            Candle cerrada si se completó una ventana, None si aún está activa
        """
        if tick_ts is None:
            tick_ts = int(time.time())
        
        window_start = self._get_window_start(tick_ts)
        
        # Si es una nueva ventana
        if window_start != self.current_window_start:
            closed_candle = None
            
            # Cerrar vela anterior si existe
            if self.current_candle is not None:
                self.current_candle.final = True
                self.candles.append(self.current_candle)
                closed_candle = self.current_candle
            
            # Crear nueva vela
            self.current_candle = Candle(
                start_ts=window_start,
                open=price,
                high=price,
                low=price,
                close=price,
                final=False,
                volume=1
            )
            self.current_window_start = window_start
            
            return closed_candle
        
        # Actualizar vela actual
        if self.current_candle:
            self.current_candle.high = max(self.current_candle.high, price)
            self.current_candle.low = min(self.current_candle.low, price)
            self.current_candle.close = price
            self.current_candle.volume += 1
        
        return None
    
    def get_current_candle(self) -> Optional[Candle]:
        """Retorna la vela actual en construcción"""
        return self.current_candle
    
    def get_history(self) -> List[Dict]:
        """Retorna histórico de velas cerradas + vela actual (solo velas válidas)"""
        result = []
        
        # Convertir velas cerradas
        for c in self.candles:
            # Validar que todos los valores sean numéricos y no null
            if all([
                c.start_ts is not None,
                c.open is not None and c.open > 0,
                c.high is not None and c.high > 0,
                c.low is not None and c.low > 0,
                c.close is not None and c.close > 0
            ]):
                result.append({
                    "time": c.start_ts,  # Lightweight Charts espera 'time'
                    "open": float(c.open),
                    "high": float(c.high),
                    "low": float(c.low),
                    "close": float(c.close)
                })
        
        # Agregar vela actual si existe y es válida
        if self.current_candle:
            if all([
                self.current_candle.start_ts is not None,
                self.current_candle.open is not None and self.current_candle.open > 0,
                self.current_candle.high is not None and self.current_candle.high > 0,
                self.current_candle.low is not None and self.current_candle.low > 0,
                self.current_candle.close is not None and self.current_candle.close > 0
            ]):
                result.append({
                    "time": self.current_candle.start_ts,
                    "open": float(self.current_candle.open),
                    "high": float(self.current_candle.high),
                    "low": float(self.current_candle.low),
                    "close": float(self.current_candle.close)
                })
        
        return result
    
    def get_candles_count(self) -> int:
        """Retorna cantidad total de velas (cerradas + actual)"""
        count = len(self.candles)
        if self.current_candle:
            count += 1
        return count


class MultiTimeframeAggregator:
    """
    Agrega velas de timeframe base (1m) a timeframes superiores (5m, 15m)
    """
    def __init__(self, base_interval_sec: int = 60):
        self.base_interval_sec = base_interval_sec
        self.stores: Dict[str, CandleStore] = {}
    
    def add_timeframe(self, symbol: str, multiplier: int, max_history: int = 200):
        """
        Agrega un timeframe derivado
        multiplier: 5 para 5m, 15 para 15m, etc
        """
        key = f"{symbol}_{multiplier}m"
        interval_sec = self.base_interval_sec * multiplier
        self.stores[key] = CandleStore(symbol, interval_sec, max_history)
    
    def process_tick(self, symbol: str, price: float, tick_ts: Optional[int] = None) -> Dict[str, Optional[Candle]]:
        """
        Procesa un tick en todos los timeframes
        
        Returns:
            Dict con velas cerradas por timeframe: {"1m": Candle, "5m": None, ...}
        """
        closed_candles = {}
        
        for key, store in self.stores.items():
            if store.symbol == symbol:
                closed = store.add_tick(price, tick_ts)
                timeframe = key.split('_')[1]  # Extrae "1m", "5m", etc
                closed_candles[timeframe] = closed
        
        return closed_candles
