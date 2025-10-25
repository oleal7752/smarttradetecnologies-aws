"""
Configuración del sistema de trading en tiempo real
"""
import os
from typing import Optional

class Settings:
    # Twelve Data API - Se lee en tiempo de ejecución, no en importación
    TWELVEDATA_WS_URL: str = "wss://ws.twelvedata.com/v1/quotes/price"
    
    # Símbolos y timeframes - Solo EURUSD y EURJPY
    SYMBOLS: list = ["EURUSD", "EURJPY"]  # Símbolos internos
    SYMBOL_MAP: dict = {
        "EURUSD": "EUR/USD",
        "EURJPY": "EUR/JPY"
    }
    BASE_INTERVAL_SECONDS: int = 60  # vela base 1m
    SUPPORTED_TIMEFRAMES: list = ["1m", "5m", "15m"]
    
    # WebSocket configuration
    WS_RECONNECT_DELAY: int = 1  # segundos iniciales
    WS_MAX_RECONNECT_DELAY: int = 60  # máximo delay de reconexión
    
    # Chart settings
    MAX_CANDLES_HISTORY: int = 200
    
    @property
    def TWELVEDATA_API_KEY(self) -> str:
        """Lee la API key en tiempo de ejecución desde variables de entorno"""
        return os.environ.get('TWELVEDATA_API_KEY', '')
    
    @classmethod
    def validate(cls):
        """Valida configuración en tiempo de ejecución"""
        api_key = os.environ.get('TWELVEDATA_API_KEY', '')
        if not api_key:
            raise ValueError("TWELVEDATA_API_KEY no configurada en secretos")
        return True

settings = Settings()
