#!/usr/bin/env python3
"""
Worker en background que recolecta precios de Finnhub cada 5 segundos
para construir velas OHLC reales
"""
import time
import threading
from services.finnhub_service import finnhub_service

class FinnhubQuoteWorker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.symbols = ['BTCUSD', 'ETHUSD']
        self.interval = 5
        
    def start(self):
        """Inicia el worker en background"""
        if self.running:
            print("⚠️ Finnhub Quote Worker ya está corriendo")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        print(f"✅ Finnhub Quote Worker iniciado - Recolectando {', '.join(self.symbols)} cada {self.interval}s")
    
    def stop(self):
        """Detiene el worker"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        print("🛑 Finnhub Quote Worker detenido")
    
    def _worker_loop(self):
        """Loop principal del worker"""
        while self.running:
            try:
                for symbol in self.symbols:
                    try:
                        price_data = finnhub_service.get_current_price(symbol)
                        if price_data:
                            print(f"📊 {symbol}: ${price_data['price']:.2f}")
                    except Exception as e:
                        print(f"❌ Error obteniendo precio de {symbol}: {e}")
                
                time.sleep(self.interval)
                
            except Exception as e:
                print(f"❌ Error en Finnhub Quote Worker: {e}")
                time.sleep(10)

quote_worker = FinnhubQuoteWorker()
