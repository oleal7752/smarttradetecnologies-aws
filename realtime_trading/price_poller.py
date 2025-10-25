"""
Poller de precios usando Twelve Data API REST
"""
import asyncio
import aiohttp
import time
import logging
from typing import Callable, Optional
from .config import settings

logger = logging.getLogger(__name__)


class TwelveDataPoller:
    """Poller de precios en tiempo real usando API REST de Twelve Data"""
    
    def __init__(self, on_price_callback: Callable[[str, float, int], None], symbols: list = None):
        """
        Args:
            on_price_callback: función(symbol, price, timestamp) llamada con cada tick
            symbols: lista de símbolos a monitorear (default: ["EURUSD", "EURJPY"])
        """
        self.on_price = on_price_callback
        self.running = False
        self.poll_interval = 3  # 3 segundos - OPTIMIZADO para producción (evita saturación)
        self.session: Optional[aiohttp.ClientSession] = None
        # Solo EURUSD y EURJPY - Formato Twelve Data: EURUSD -> EUR/USD
        self.symbols = symbols or ["EURUSD", "EURJPY"]
        self.symbol_map = {
            "EURUSD": "EUR/USD",
            "EURJPY": "EUR/JPY"
        }
    
    async def fetch_price(self, symbol: str) -> Optional[dict]:
        """Obtiene precio actual de un símbolo desde la API de Twelve Data"""
        url = "https://api.twelvedata.com/price"
        
        # Convertir símbolo al formato Twelve Data
        symbol_td = self.symbol_map.get(symbol, symbol)
        
        params = {
            "symbol": symbol_td,
            "apikey": settings.TWELVEDATA_API_KEY
        }
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {"symbol": symbol, "price": data.get('price')}
                else:
                    logger.warning(f"Error API Twelve Data ({symbol}): {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching price ({symbol}): {e}")
            return None
    
    async def run(self):
        """Bucle principal de polling - requests en PARALELO para verdadero tick-a-tick"""
        self.running = True
        logger.info(f"Iniciando poller de precios para {len(self.symbols)} símbolos (cada {self.poll_interval}s)")
        
        # Contador de errores por símbolo (para back-off)
        error_counts = {symbol: 0 for symbol in self.symbols}
        # Timestamp de última reactivación (para cooldown)
        last_retry_time = {symbol: 0 for symbol in self.symbols}
        
        while self.running:
            try:
                current_time = int(time.time())
                logger.info(f"🔄 Ciclo de polling - {len(self.symbols)} símbolos")
                
                # Procesar todos los símbolos EN PARALELO usando asyncio.gather
                tasks = []
                active_symbols = []
                
                for symbol in self.symbols:
                    # Back-off con cooldown: pausa 60s después de 5 errores, luego reintenta
                    if error_counts[symbol] >= 5:
                        if last_retry_time[symbol] == 0:
                            last_retry_time[symbol] = current_time
                            logger.debug(f"{symbol}: En cooldown por errores")
                            continue
                        
                        time_in_cooldown = current_time - last_retry_time[symbol]
                        if time_in_cooldown < 60:
                            continue
                        else:
                            logger.debug(f"{symbol}: Reactivando")
                            error_counts[symbol] = 0
                            last_retry_time[symbol] = 0
                    
                    # Agregar tarea para este símbolo
                    tasks.append(self.fetch_price(symbol))
                    active_symbols.append(symbol)
                
                # Ejecutar TODAS las requests en paralelo
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Procesar resultados
                    for symbol, result in zip(active_symbols, results):
                        try:
                            if isinstance(result, Exception):
                                error_counts[symbol] += 1
                                logger.error(f"Error polling {symbol}: {result}")
                                continue
                            
                            data = result
                            if data and 'price' in data and data['price'] is not None:
                                try:
                                    price = float(data['price'])
                                    timestamp = int(time.time())
                                    
                                    if price > 0:
                                        await self.on_price(symbol, price, timestamp)
                                        logger.info(f"💰 {symbol}: {price:.5f}")
                                        error_counts[symbol] = 0  # Reset en éxito
                                    else:
                                        logger.warning(f"{symbol}: Precio inválido ({price})")
                                        error_counts[symbol] += 1
                                except (ValueError, TypeError) as e:
                                    logger.error(f"{symbol}: Error convirtiendo precio - {e}")
                                    error_counts[symbol] += 1
                            else:
                                error_counts[symbol] += 1
                                if error_counts[symbol] % 10 == 1:
                                    logger.warning(f"{symbol}: Sin datos de precio (intento {error_counts[symbol]})")
                        
                        except Exception as e:
                            error_counts[symbol] += 1
                            logger.error(f"Error procesando {symbol}: {e}")
                
            except Exception as e:
                logger.error(f"Error crítico en poller: {e}")
            
            # Esperar EXACTAMENTE 1 segundo antes del siguiente ciclo
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Detiene el poller"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Poller de precios detenido")
