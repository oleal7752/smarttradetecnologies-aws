"""
Cargador de velas históricas desde Twelve Data API
"""
import aiohttp
import logging
from typing import List, Dict
from datetime import datetime, timezone
from .config import settings

logger = logging.getLogger(__name__)


async def load_historical_candles(symbol: str, interval: str, outputsize: int = 500) -> List[Dict]:
    """
    Carga velas históricas desde Twelve Data API
    
    Args:
        symbol: Par de trading (ej: "EUR/USD")
        interval: Intervalo (ej: "1min", "5min", "15min")
        outputsize: Cantidad de velas a cargar (default: 500)
    
    Returns:
        Lista de velas en orden cronológico (UTC)
    """
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": settings.TWELVEDATA_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if "values" in data:
                        candles = []
                        
                        # Datos vienen más recientes primero, invertir
                        for item in reversed(data["values"]):
                            # Convertir fecha string a timestamp Unix (UTC)
                            # IMPORTANTE: Twelve Data devuelve fechas en UTC, forzar timezone.utc
                            dt = datetime.strptime(item["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            timestamp = int(dt.timestamp())
                            
                            candle = {
                                "time": timestamp,
                                "open": float(item["open"]),
                                "high": float(item["high"]),
                                "low": float(item["low"]),
                                "close": float(item["close"])
                            }
                            candles.append(candle)
                        
                        logger.info(f"Cargadas {len(candles)} velas históricas {interval} para {symbol}")
                        return candles
                    else:
                        logger.warning(f"No se encontraron datos históricos: {data}")
                        return []
                else:
                    logger.warning(f"Error API histórico: {response.status}")
                    return []
                    
    except Exception as e:
        logger.error(f"Error cargando histórico: {e}")
        return []
