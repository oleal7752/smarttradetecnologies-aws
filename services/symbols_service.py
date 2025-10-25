"""
Symbols Service - Servicio de pares compartido globalmente
Cache de pares disponibles actualizado periódicamente
"""

import threading
import time
from datetime import datetime

class SymbolsService:
    def __init__(self):
        self.cache = {
            'symbols': None,
            'last_update': 0,
            'ttl': 300  # 5 minutos
        }
        self.lock = threading.Lock()
        self.fallback_symbols = {
            "success": True,
            "symbols": {
                "OTC": [
                    {"name": "EURUSD-OTC", "display": "EUR/USD (OTC)"},
                    {"name": "GBPUSD-OTC", "display": "GBP/USD (OTC)"},
                    {"name": "USDJPY-OTC", "display": "USD/JPY (OTC)"},
                    {"name": "AUDUSD-OTC", "display": "AUD/USD (OTC)"},
                    {"name": "USDCAD-OTC", "display": "USD/CAD (OTC)"},
                    {"name": "NZDUSD-OTC", "display": "NZD/USD (OTC)"},
                    {"name": "EURGBP-OTC", "display": "EUR/GBP (OTC)"},
                    {"name": "EURJPY-OTC", "display": "EUR/JPY (OTC)"},
                    {"name": "GBPJPY-OTC", "display": "GBP/JPY (OTC)"},
                    {"name": "AUDJPY-OTC", "display": "AUD/JPY (OTC)"},
                    {"name": "EURAUD-OTC", "display": "EUR/AUD (OTC)"},
                    {"name": "GBPAUD-OTC", "display": "GBP/AUD (OTC)"}
                ],
                "REAL": [
                    {"name": "EURUSD", "display": "EUR/USD"},
                    {"name": "GBPUSD", "display": "GBP/USD"},
                    {"name": "USDJPY", "display": "USD/JPY"},
                    {"name": "AUDUSD", "display": "AUD/USD"},
                    {"name": "USDCAD", "display": "USD/CAD"},
                    {"name": "NZDUSD", "display": "NZD/USD"},
                    {"name": "EURGBP", "display": "EUR/GBP"},
                    {"name": "EURJPY", "display": "EUR/JPY"},
                    {"name": "GBPJPY", "display": "GBP/JPY"},
                    {"name": "AUDJPY", "display": "AUD/JPY"}
                ]
            }
        }
    
    def get_symbols(self, api_client=None):
        """
        Obtener símbolos disponibles
        Usa cache si está fresco, sino actualiza desde API
        """
        current_time = time.time()
        
        with self.lock:
            # Si el cache es válido, retornar
            if self.cache['symbols'] and (current_time - self.cache['last_update']) < self.cache['ttl']:
                print(f"📊 Símbolos desde cache ({int(current_time - self.cache['last_update'])}s antiguo)")
                return self.cache['symbols']
            
            # Cache expirado o vacío, actualizar
            if api_client:
                try:
                    symbols = api_client.get_available_symbols()
                    if symbols and symbols.get('success'):
                        self.cache['symbols'] = symbols
                        self.cache['last_update'] = current_time
                        print(f"✅ Símbolos actualizados desde API")
                        return symbols
                except Exception as e:
                    print(f"❌ Error actualizando símbolos: {e}")
            
            # Si falla o no hay API, usar fallback
            if not self.cache['symbols']:
                print(f"⚠️  Usando símbolos predefinidos (fallback)")
                self.cache['symbols'] = self.fallback_symbols
                self.cache['last_update'] = current_time
            
            return self.cache['symbols']
    
    def invalidate_cache(self):
        """Invalidar cache para forzar actualización"""
        with self.lock:
            self.cache['last_update'] = 0
            print("🔄 Cache de símbolos invalidado")


# Instancia global
symbols_service = SymbolsService()
