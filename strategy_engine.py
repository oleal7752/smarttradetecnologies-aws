"""
Motor de Estrategias de Trading - STC Trading System
Arquitectura para estrategias automatizadas, backtesting y auto-trading
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from datetime import datetime
import numpy as np
import pandas as pd


@dataclass
class Candle:
    """Representa una vela de trading"""
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    
    def __post_init__(self):
        if isinstance(self.time, datetime):
            self.time = int(self.time.timestamp())


@dataclass
class Signal:
    """Señal de trading generada por una estrategia"""
    symbol: str
    direction: Literal['CALL', 'PUT']
    timeframe: str
    timestamp: int
    confidence: float
    indicators: Dict[str, float]
    strategy_name: str
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'strategy_name': self.strategy_name
        }


@dataclass
class Trade:
    """Representa una operación ejecutada"""
    id: str
    symbol: str
    direction: Literal['CALL', 'PUT']
    amount: float
    duration: int
    entry_price: float
    entry_time: int
    exit_price: Optional[float] = None
    exit_time: Optional[int] = None
    profit: Optional[float] = None
    result: Optional[Literal['WIN', 'LOSS', 'DRAW']] = None
    strategy_name: str = ''
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'direction': self.direction,
            'amount': self.amount,
            'duration': self.duration,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time,
            'profit': self.profit,
            'result': self.result,
            'strategy_name': self.strategy_name
        }


class Strategy(ABC):
    """Clase base abstracta para todas las estrategias de trading"""
    
    def __init__(self, name: str, params: Dict = None):
        self.name = name
        self.params = params or {}
        self.min_candles = 50
        
    @abstractmethod
    def calculate_indicators(self, candles: List[Candle]) -> Dict[str, np.ndarray]:
        """Calcula los indicadores técnicos necesarios para la estrategia"""
        pass
    
    @abstractmethod
    def generate_signal(self, candles: List[Candle], indicators: Dict[str, np.ndarray]) -> Optional[Signal]:
        """Genera una señal de trading basada en los indicadores"""
        pass
    
    def analyze(self, symbol: str, timeframe: str, candles: List[Candle]) -> Optional[Signal]:
        """Analiza las velas y genera una señal si las condiciones se cumplen"""
        if len(candles) < self.min_candles:
            return None
            
        indicators = self.calculate_indicators(candles)
        signal = self.generate_signal(candles, indicators)
        
        if signal:
            signal.symbol = symbol
            signal.timeframe = timeframe
            signal.strategy_name = self.name
            
        return signal
    
    def get_config(self) -> dict:
        """Retorna la configuración de la estrategia"""
        return {
            'name': self.name,
            'params': self.params,
            'min_candles': self.min_candles
        }


class StrategyEngine:
    """Motor principal que gestiona y ejecuta estrategias de trading"""
    
    def __init__(self):
        self.strategies: Dict[str, Strategy] = {}
        self.active_strategies: List[str] = []
        
    def register_strategy(self, strategy: Strategy):
        """Registra una nueva estrategia en el motor"""
        self.strategies[strategy.name] = strategy
        print(f"✅ Estrategia registrada: {strategy.name}")
        
    def activate_strategy(self, strategy_name: str):
        """Activa una estrategia para trading en vivo"""
        if strategy_name in self.strategies and strategy_name not in self.active_strategies:
            self.active_strategies.append(strategy_name)
            print(f"🟢 Estrategia activada: {strategy_name}")
            
    def deactivate_strategy(self, strategy_name: str):
        """Desactiva una estrategia"""
        if strategy_name in self.active_strategies:
            self.active_strategies.remove(strategy_name)
            print(f"🔴 Estrategia desactivada: {strategy_name}")
            
    def analyze_market(self, symbol: str, timeframe: str, candles: List[Candle]) -> List[Signal]:
        """Analiza el mercado con todas las estrategias activas"""
        signals = []
        
        for strategy_name in self.active_strategies:
            strategy = self.strategies.get(strategy_name)
            if strategy:
                signal = strategy.analyze(symbol, timeframe, candles)
                if signal:
                    signals.append(signal)
                    
        return signals
    
    def get_all_strategies(self) -> List[dict]:
        """Retorna información de todas las estrategias registradas"""
        return [
            {
                'name': name,
                'config': strategy.get_config(),
                'active': name in self.active_strategies
            }
            for name, strategy in self.strategies.items()
        ]


def calculate_sma(prices: np.ndarray, period: int) -> np.ndarray:
    """Calcula Simple Moving Average"""
    return pd.Series(prices).rolling(window=period).mean().values


def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Calcula Exponential Moving Average"""
    return pd.Series(prices).ewm(span=period, adjust=False).mean().values


def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Calcula Relative Strength Index"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
            
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
        
    return rsi


def calculate_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, np.ndarray]:
    """Calcula MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Dict[str, np.ndarray]:
    """Calcula Bandas de Bollinger"""
    sma = calculate_sma(prices, period)
    std = pd.Series(prices).rolling(window=period).std().values
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return {
        'upper': upper_band,
        'middle': sma,
        'lower': lower_band
    }


if __name__ == '__main__':
    print("🤖 Strategy Engine - STC Trading System")
    print("Arquitectura de estrategias lista para usar")
