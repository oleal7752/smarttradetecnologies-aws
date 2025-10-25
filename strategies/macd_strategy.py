"""
Estrategia MACD (Moving Average Convergence Divergence)
Señales basadas en cruces de líneas MACD
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal, calculate_macd


class MACDStrategy(Strategy):
    """
    Estrategia basada en MACD Crossover
    - CALL cuando MACD cruza hacia arriba la línea de señal
    - PUT cuando MACD cruza hacia abajo la línea de señal
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'min_histogram': 0.0001,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
            
        super().__init__('MACD Crossover', default_params)
        self.min_candles = max(50, self.params['slow_period'] * 3)
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula el indicador MACD"""
        closes = np.array([c.close for c in candles])
        macd_data = calculate_macd(
            closes,
            self.params['fast_period'],
            self.params['slow_period'],
            self.params['signal_period']
        )
        
        return {
            'macd': macd_data['macd'],
            'signal': macd_data['signal'],
            'histogram': macd_data['histogram'],
            'closes': closes
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en cruce de MACD"""
        macd = indicators['macd']
        signal = indicators['signal']
        histogram = indicators['histogram']
        
        current_hist = histogram[-1]
        prev_hist = histogram[-2]
        
        if np.isnan(current_hist) or np.isnan(prev_hist):
            return None
        
        min_hist = self.params['min_histogram']
        
        if prev_hist < 0 and current_hist > 0 and abs(current_hist) > min_hist:
            confidence = min(1.0, abs(current_hist) * 1000)
            confidence = max(self.params['min_confidence'], confidence)
            
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'macd': float(macd[-1]),
                    'signal_line': float(signal[-1]),
                    'histogram': float(current_hist),
                    'prev_histogram': float(prev_hist)
                },
                strategy_name=self.name
            )
            
        elif prev_hist > 0 and current_hist < 0 and abs(current_hist) > min_hist:
            confidence = min(1.0, abs(current_hist) * 1000)
            confidence = max(self.params['min_confidence'], confidence)
            
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'macd': float(macd[-1]),
                    'signal_line': float(signal[-1]),
                    'histogram': float(current_hist),
                    'prev_histogram': float(prev_hist)
                },
                strategy_name=self.name
            )
            
        return None
