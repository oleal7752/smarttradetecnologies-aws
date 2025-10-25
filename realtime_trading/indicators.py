"""
Indicadores técnicos incrementales
"""
from typing import Optional, List
from collections import deque


class EMA:
    """Exponential Moving Average - Cálculo incremental"""
    
    def __init__(self, period: int):
        self.period = period
        self.multiplier = 2 / (period + 1)
        self.ema: Optional[float] = None
        self.initialized = False
    
    def update(self, price: float) -> Optional[float]:
        """
        Actualiza EMA con nuevo precio
        
        Returns:
            Valor actual de EMA o None si aún no está inicializado
        """
        if self.ema is None:
            # Primera inicialización con el precio
            self.ema = price
            self.initialized = True
        else:
            # Fórmula incremental: EMA = Price(t) * k + EMA(y) * (1 – k)
            self.ema = price * self.multiplier + self.ema * (1 - self.multiplier)
        
        return self.ema
    
    def get_value(self) -> Optional[float]:
        """Retorna el valor actual de EMA"""
        return self.ema


class RSI:
    """Relative Strength Index - Cálculo incremental"""
    
    def __init__(self, period: int = 14):
        self.period = period
        self.prices = deque(maxlen=period + 1)
        self.gains = deque(maxlen=period)
        self.losses = deque(maxlen=period)
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None
    
    def update(self, price: float) -> Optional[float]:
        """
        Actualiza RSI con nuevo precio
        
        Returns:
            Valor RSI (0-100) o None si no hay suficientes datos
        """
        self.prices.append(price)
        
        if len(self.prices) < 2:
            return None
        
        # Calcular cambio
        change = self.prices[-1] - self.prices[-2]
        gain = max(change, 0)
        loss = max(-change, 0)
        
        self.gains.append(gain)
        self.losses.append(loss)
        
        if len(self.gains) < self.period:
            return None
        
        # Primera vez: promedio simple
        if self.avg_gain is None:
            self.avg_gain = sum(self.gains) / self.period
            self.avg_loss = sum(self.losses) / self.period
        else:
            # Promedio móvil suavizado (Wilder's smoothing)
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
        
        if self.avg_loss == 0:
            return 100.0
        
        rs = self.avg_gain / self.avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_value(self) -> Optional[float]:
        """Retorna el último valor calculado de RSI"""
        if len(self.gains) < self.period or self.avg_gain is None:
            return None
        
        if self.avg_loss == 0:
            return 100.0
        
        rs = self.avg_gain / self.avg_loss
        return 100 - (100 / (1 + rs))


class MACD:
    """MACD (Moving Average Convergence Divergence) - Cálculo incremental"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_ema = EMA(fast_period)
        self.slow_ema = EMA(slow_period)
        self.signal_ema = EMA(signal_period)
        self.macd_line: Optional[float] = None
        self.signal_line: Optional[float] = None
        self.histogram: Optional[float] = None
    
    def update(self, price: float) -> Optional[dict]:
        """
        Actualiza MACD con nuevo precio
        
        Returns:
            Dict {macd: float, signal: float, histogram: float} o None
        """
        fast_val = self.fast_ema.update(price)
        slow_val = self.slow_ema.update(price)
        
        if fast_val is None or slow_val is None:
            return None
        
        # MACD line = EMA rápida - EMA lenta
        self.macd_line = fast_val - slow_val
        
        # Línea de señal = EMA del MACD
        signal_val = self.signal_ema.update(self.macd_line)
        
        if signal_val is None:
            return None
        
        self.signal_line = signal_val
        self.histogram = self.macd_line - self.signal_line
        
        return {
            "macd": round(self.macd_line, 5),
            "signal": round(self.signal_line, 5),
            "histogram": round(self.histogram, 5)
        }
    
    def get_value(self) -> Optional[dict]:
        """Retorna los valores actuales de MACD"""
        if self.macd_line is None or self.signal_line is None:
            return None
        
        return {
            "macd": round(self.macd_line, 5),
            "signal": round(self.signal_line, 5),
            "histogram": round(self.histogram, 5)
        }


class IndicatorEngine:
    """Motor que gestiona múltiples indicadores"""
    
    def __init__(self):
        self.indicators = {}
    
    def add_ema(self, name: str, period: int):
        """Agrega un indicador EMA"""
        self.indicators[name] = EMA(period)
    
    def add_rsi(self, name: str, period: int = 14):
        """Agrega un indicador RSI"""
        self.indicators[name] = RSI(period)
    
    def add_macd(self, name: str, fast: int = 12, slow: int = 26, signal: int = 9):
        """Agrega un indicador MACD"""
        self.indicators[name] = MACD(fast, slow, signal)
    
    def update(self, price: float) -> dict:
        """
        Actualiza todos los indicadores con nuevo precio
        
        Returns:
            Dict con valores actuales: {"EMA20": 1.0750, "RSI14": 65.4, "MACD": {...}, ...}
        """
        results = {}
        for name, indicator in self.indicators.items():
            value = indicator.update(price)
            if value is not None:
                results[name] = value
        return results
    
    def get_values(self) -> dict:
        """Retorna valores actuales de todos los indicadores"""
        results = {}
        for name, indicator in self.indicators.items():
            value = indicator.get_value()
            if value is not None:
                results[name] = value
        return results
