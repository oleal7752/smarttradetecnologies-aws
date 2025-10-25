"""
Twelve Data Service - Servicio para datos forex del mercado real
Proporciona datos EURUSD sin restricciones de horario OTC
"""

import os
import time
from twelvedata import TDClient

class TwelveDataService:
    def __init__(self):
        self.api_key = os.getenv('TWELVEDATA_API_KEY')
        self.client = None
        self.connected = False
        
    def connect(self):
        """Conectar al servicio de Twelve Data"""
        try:
            if not self.api_key:
                print("❌ No se encontró TWELVEDATA_API_KEY en variables de entorno")
                return False
            
            self.client = TDClient(apikey=self.api_key)
            self.connected = True
            print("✅ Twelve Data conectado exitosamente")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a Twelve Data: {e}")
            self.connected = False
            return False
    
    def get_candles(self, symbol, timeframe, limit):
        """
        Obtener velas históricas del mercado real
        
        Args:
            symbol: Par forex (ej: 'EURUSD', 'EUR/USD')
            timeframe: 'M1', 'M5', 'M15', 'M30', 'H1', etc
            limit: Número de velas a obtener
        
        Returns:
            Lista de velas en formato estándar
        """
        if not self.connected:
            if not self.connect():
                return []
        
        try:
            # Convertir formato de símbolo para Twelve Data
            # EURUSD, EUR-USD, EUR_USD → EUR/USD
            symbol_clean = symbol.replace('-', '').replace('_', '').replace('/', '')
            
            # Agregar '/' si no existe (formato forex de Twelve Data: EUR/USD)
            if len(symbol_clean) == 6:
                td_symbol = f"{symbol_clean[:3]}/{symbol_clean[3:]}"
            else:
                td_symbol = symbol
            
            # Convertir timeframe al formato de Twelve Data
            timeframe_map = {
                'M1': '1min',
                'M5': '5min',
                'M15': '15min',
                'M30': '30min',
                'H1': '1h',
                'H4': '4h',
                'D1': '1day'
            }
            
            td_timeframe = timeframe_map.get(timeframe, '5min')
            
            # Obtener datos de Twelve Data usando el símbolo formateado
            print(f"🔍 Twelve Data: Solicitando {td_symbol} intervalo {td_timeframe} (limit={limit})")
            
            ts = self.client.time_series(
                symbol=td_symbol,
                interval=td_timeframe,
                outputsize=limit,
                timezone='America/New_York'  # UTC-4 para datos correctos
            )
            
            # Obtener datos como JSON
            data = ts.as_json()
            
            if not data:
                print(f"⚠️  Twelve Data: Sin datos para {td_symbol} {timeframe}")
                return []
            
            # Convertir al formato interno
            candles = []
            # Los datos pueden venir como tupla o dict con 'values'
            values = data if isinstance(data, (list, tuple)) else data.get('values', [])
            
            for item in values:
                # CRÍTICO: Twelve Data con timezone='America/New_York' devuelve hora local UTC-4
                from datetime import datetime, timezone, timedelta
                dt = datetime.strptime(item['datetime'], '%Y-%m-%d %H:%M:%S')
                # Interpretar como America/New_York (UTC-4) y convertir a timestamp Unix UTC
                dt_utc4 = dt.replace(tzinfo=timezone(timedelta(hours=-4)))
                timestamp = int(dt_utc4.timestamp())
                
                candles.append({
                    'time': timestamp,
                    'open': float(item['open']),
                    'high': float(item['high']),
                    'low': float(item['low']),
                    'close': float(item['close']),
                    'volume': float(item.get('volume', 0))
                })
            
            # Invertir orden (más reciente primero)
            candles.reverse()
            
            print(f"✅ Twelve Data: {len(candles)} velas obtenidas para {symbol} {timeframe}")
            return candles
            
        except Exception as e:
            # Logging seguro sin exponer detalles sensibles
            error_type = type(e).__name__
            print(f"❌ Error obteniendo velas de Twelve Data: {error_type}")
            return []
    
    def get_quote(self, symbol):
        """Obtener cotización en tiempo real"""
        if not self.connected:
            if not self.connect():
                return None
        
        try:
            # Formatear símbolo
            if '-' in symbol:
                symbol = symbol.replace('-', '')
            if '/' not in symbol and len(symbol) == 6:
                symbol = f"{symbol[:3]}/{symbol[3:]}"
            
            quote = self.client.quote(symbol=symbol).as_json()
            
            if not quote or 'price' not in quote:
                print(f"⚠️  Twelve Data: Sin cotización para {symbol}")
                return None
            
            return {
                'symbol': symbol,
                'price': float(quote['price']),
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo cotización de Twelve Data: {e}")
            return None

# Instancia global
twelvedata_service = TwelveDataService()
