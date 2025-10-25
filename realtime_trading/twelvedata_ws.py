"""
Cliente WebSocket para Twelve Data con reconexión automática
"""
import asyncio
import json
import websockets
from websockets import WebSocketClientProtocol
import time
import logging
from typing import Callable, Optional
from .config import settings

logger = logging.getLogger(__name__)


class TwelveDataWSClient:
    """Cliente WebSocket de Twelve Data con manejo de reconexión"""
    
    def __init__(self, on_price_callback: Callable[[str, float, int], None]):
        """
        Args:
            on_price_callback: función(symbol, price, timestamp) llamada con cada tick
        """
        self.on_price = on_price_callback
        self.ws: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.reconnect_delay = settings.WS_RECONNECT_DELAY
    
    async def connect(self):
        """Conecta al WebSocket de Twelve Data"""
        url = f"{settings.TWELVEDATA_WS_URL}?apikey={settings.TWELVEDATA_API_KEY}"
        
        try:
            self.ws = await websockets.connect(url)
            logger.info("Conectado a Twelve Data WebSocket")
            
            # Suscribirse a símbolo
            subscribe_msg = {
                "action": "subscribe",
                "params": {
                    "symbols": settings.SYMBOLS
                }
            }
            await self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"Suscrito a {settings.SYMBOLS}")
            
            # Reset reconnect delay después de conexión exitosa
            self.reconnect_delay = settings.WS_RECONNECT_DELAY
            
        except Exception as e:
            logger.error(f"Error conectando a Twelve Data: {e}")
            raise
    
    async def listen(self):
        """Escucha mensajes del WebSocket"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    
                    # Mensaje de precio
                    if data.get("event") == "price":
                        symbol = data.get("symbol", "").replace("/", "")  # EUR/USD -> EURUSD
                        price = float(data.get("price", 0))
                        timestamp = int(data.get("timestamp", time.time()))
                        
                        if price > 0:
                            await self.on_price(symbol, price, timestamp)
                    
                    # Mensaje de confirmación de suscripción
                    elif data.get("event") == "subscribe-status":
                        status = data.get("status")
                        logger.debug(f"Suscripción: {status}")
                    
                    # Heartbeat
                    elif data.get("event") == "heartbeat":
                        # print("💓 Heartbeat")
                        pass
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Error decodificando mensaje: {e}")
                except Exception as e:
                    logger.warning(f"Error procesando mensaje: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Conexión WebSocket cerrada")
        except Exception as e:
            logger.error(f"Error en listen: {e}")
    
    async def run(self):
        """Bucle principal con reconexión automática"""
        self.running = True
        
        while self.running:
            try:
                await self.connect()
                await self.listen()
            except Exception as e:
                logger.error(f"Error en WebSocket: {e}")
            
            if self.running:
                # Backoff exponencial
                logger.info(f"Reconectando en {self.reconnect_delay}s")
                await asyncio.sleep(self.reconnect_delay)
                
                # Incrementar delay (máximo 60s)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, 
                    settings.WS_MAX_RECONNECT_DELAY
                )
    
    async def stop(self):
        """Detiene el cliente WebSocket"""
        self.running = False
        if self.ws:
            await self.ws.close()
        logger.info("Cliente Twelve Data detenido")
