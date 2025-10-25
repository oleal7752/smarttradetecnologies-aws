"""
Estrategia TENDENCIAL TRADE
Señales basadas en EMA 200 y color de velas (verde/roja)
Con sistema de Gale automático
"""

from typing import List, Dict, Optional
import numpy as np
from strategy_engine import Strategy, Candle, Signal, calculate_ema


class TendencialTradeStrategy(Strategy):
    """
    Estrategia TENDENCIAL TRADE
    
    Reglas CALL:
    - Vela verde (close > open)
    - Precio por ENCIMA de EMA 200
    - Genera señal en cada vela verde consecutiva
    
    Reglas PUT:
    - Vela roja (close < open)
    - Precio por DEBAJO de EMA 200
    - Genera señal en cada vela roja consecutiva
    
    Sistema Gale:
    - Si operación pierde (vela contraria), entra en ciclo Gale
    - Etiquetas: G1, G2, G3... hasta recuperar
    """
    
    def __init__(self, params: Dict = None):
        default_params = {
            'ema_period': 200,
            'min_confidence': 0.65
        }
        if params:
            default_params.update(params)
            
        super().__init__('TENDENCIAL TRADE', default_params)
        self.min_candles = max(250, self.params['ema_period'] + 50)
        
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula EMA 200"""
        closes = np.array([c.close for c in candles])
        opens = np.array([c.open for c in candles])
        
        ema_200 = calculate_ema(closes, self.params['ema_period'])
        
        return {
            'ema_200': ema_200,
            'closes': closes,
            'opens': opens
        }
    
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera señal basada en EMA 200 y color de vela"""
        ema_200 = indicators['ema_200']
        closes = indicators['closes']
        opens = indicators['opens']
        
        current_ema = ema_200[-1]
        current_close = closes[-1]
        current_open = opens[-1]
        
        if np.isnan(current_ema):
            return None
        
        is_green_candle = current_close > current_open
        is_red_candle = current_close < current_open
        
        price_above_ema = current_close > current_ema
        price_below_ema = current_close < current_ema
        
        if is_green_candle and price_above_ema:
            candle_size = abs(current_close - current_open)
            confidence = min(0.95, self.params['min_confidence'] + (candle_size / current_close) * 10)
            
            return Signal(
                symbol='',
                direction='CALL',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'ema_200': float(current_ema),
                    'price': float(current_close),
                    'candle_type': 'verde',
                    'trend': 'alcista',
                    'distance_from_ema': float(current_close - current_ema)
                },
                strategy_name=self.name
            )
            
        elif is_red_candle and price_below_ema:
            candle_size = abs(current_close - current_open)
            confidence = min(0.95, self.params['min_confidence'] + (candle_size / current_close) * 10)
            
            return Signal(
                symbol='',
                direction='PUT',
                timeframe='',
                timestamp=candles[-1].time,
                confidence=confidence,
                indicators={
                    'ema_200': float(current_ema),
                    'price': float(current_close),
                    'candle_type': 'roja',
                    'trend': 'bajista',
                    'distance_from_ema': float(current_ema - current_close)
                },
                strategy_name=self.name
            )
            
        return None
