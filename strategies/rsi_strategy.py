"""
Estrategia RSI (Relative Strength Index)
Señales basadas en condiciones de sobrecompra/sobreventa
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal, calculate_rsi


class RSIStrategy(Strategy):
    """
    Estrategia basada en RSI
    - CALL cuando RSI < oversold (típicamente 30)
    - PUT cuando RSI > overbought (típicamente 70)
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
            
        super().__init__('RSI Oversold/Overbought', default_params)
        self.min_candles = max(50, self.params['rsi_period'] * 3)
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula el indicador RSI"""
        closes = np.array([c.close for c in candles])
        rsi = calculate_rsi(closes, self.params['rsi_period'])
        
        return {
            'rsi': rsi,
            'closes': closes
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en condiciones de RSI"""
        rsi = indicators['rsi']
        current_rsi = rsi[-1]
        prev_rsi = rsi[-2]
        
        if np.isnan(current_rsi) or np.isnan(prev_rsi):
            return None
        
        oversold = self.params['oversold']
        overbought = self.params['overbought']
        
        if current_rsi < oversold and prev_rsi >= current_rsi:
            confidence = (oversold - current_rsi) / oversold
            confidence = max(self.params['min_confidence'], min(1.0, confidence))
            
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'rsi': float(current_rsi),
                    'prev_rsi': float(prev_rsi),
                    'oversold_level': oversold
                },
                strategy_name=self.name
            )
            
        elif current_rsi > overbought and prev_rsi <= current_rsi:
            confidence = (current_rsi - overbought) / (100 - overbought)
            confidence = max(self.params['min_confidence'], min(1.0, confidence))
            
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'rsi': float(current_rsi),
                    'prev_rsi': float(prev_rsi),
                    'overbought_level': overbought
                },
                strategy_name=self.name
            )
            
        return None
