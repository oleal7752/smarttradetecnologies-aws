"""
Estrategia Bollinger Bands
Señales basadas en rebotes en las bandas
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal, calculate_bollinger_bands


class BollingerStrategy(Strategy):
    """
    Estrategia basada en Bollinger Bands Bounce
    - CALL cuando el precio toca la banda inferior y rebota
    - PUT cuando el precio toca la banda superior y rebota
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'period': 20,
            'std_dev': 2.0,
            'touch_threshold': 0.0005,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
            
        super().__init__('Bollinger Bands Bounce', default_params)
        self.min_candles = max(50, self.params['period'] * 3)
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula las Bandas de Bollinger"""
        closes = np.array([c.close for c in candles])
        lows = np.array([c.low for c in candles])
        highs = np.array([c.high for c in candles])
        
        bb = calculate_bollinger_bands(closes, self.params['period'], self.params['std_dev'])
        
        return {
            'upper_band': bb['upper'],
            'middle_band': bb['middle'],
            'lower_band': bb['lower'],
            'closes': closes,
            'lows': lows,
            'highs': highs
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en toque de bandas"""
        upper = indicators['upper_band']
        lower = indicators['lower_band']
        middle = indicators['middle_band']
        closes = indicators['closes']
        lows = indicators['lows']
        highs = indicators['highs']
        
        current_close = closes[-1]
        prev_close = closes[-2]
        current_low = lows[-1]
        current_high = highs[-1]
        current_lower = lower[-1]
        current_upper = upper[-1]
        current_middle = middle[-1]
        
        if np.isnan(current_lower) or np.isnan(current_upper):
            return None
        
        threshold = self.params['touch_threshold']
        
        lower_distance = abs(current_low - current_lower) / current_lower
        if lower_distance < threshold and current_close > prev_close:
            distance_from_middle = (current_middle - current_close) / current_middle
            confidence = min(1.0, distance_from_middle * 10)
            confidence = max(self.params['min_confidence'], confidence)
            
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'close': float(current_close),
                    'lower_band': float(current_lower),
                    'middle_band': float(current_middle),
                    'upper_band': float(current_upper),
                    'distance': float(lower_distance)
                },
                strategy_name=self.name
            )
        
        upper_distance = abs(current_high - current_upper) / current_upper
        if upper_distance < threshold and current_close < prev_close:
            distance_from_middle = (current_close - current_middle) / current_middle
            confidence = min(1.0, distance_from_middle * 10)
            confidence = max(self.params['min_confidence'], confidence)
            
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'close': float(current_close),
                    'lower_band': float(current_lower),
                    'middle_band': float(current_middle),
                    'upper_band': float(current_upper),
                    'distance': float(upper_distance)
                },
                strategy_name=self.name
            )
            
        return None
