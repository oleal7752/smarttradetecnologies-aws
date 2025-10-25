"""
Candle Service - Servicio de velas compartido con persistencia en BD
Guarda velas constantemente para alta disponibilidad e histórico
"""

import psycopg2
from psycopg2.extras import execute_values
import threading
import time
from datetime import datetime
import os

class CandleService:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.cache = {}
        self.lock = threading.Lock()
        
    def get_connection(self):
        """Obtener conexión a PostgreSQL"""
        return psycopg2.connect(self.db_url)
    
    def get_candles(self, symbol, timeframe, limit=200, source='iqoption', live_price=None):
        """
        Obtener velas desde BD (alta disponibilidad)
        Si live_price se proporciona, actualiza la última vela con el precio actual
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = """
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE source = %s AND symbol = %s AND timeframe = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            
            cur.execute(query, (source, symbol, timeframe, limit))
            rows = cur.fetchall()
            
            candles = []
            for row in rows:
                candles.append({
                    'time': row[0],
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5])
                })
            
            cur.close()
            conn.close()
            
            # Retornar en orden cronológico (más antigua primero)
            candles.reverse()
            
            # Si hay precio en vivo, actualizar la última vela
            if live_price and candles:
                last_candle = candles[-1]
                # Actualizar close, high, low con el precio actual
                last_candle['close'] = float(live_price)
                last_candle['high'] = max(last_candle['high'], float(live_price))
                last_candle['low'] = min(last_candle['low'], float(live_price))
            
            print(f"📊 Servidas {len(candles)} velas de BD para {symbol} {timeframe}")
            return candles
            
        except Exception as e:
            print(f"❌ Error obteniendo velas de BD: {e}")
            return []
    
    def save_candles(self, symbol, timeframe, candles, broker='iqoption', source='iqoption'):
        """
        Guardar velas en BD (batch insert)
        Ignora duplicados con ON CONFLICT
        """
        if not candles:
            return 0
        
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            # Preparar datos para insert (incluir source y broker)
            values = [
                (
                    symbol,
                    timeframe,
                    candle['time'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle.get('volume', 0),
                    broker,
                    source
                )
                for candle in candles
            ]
            
            # Batch insert con ON CONFLICT usando el índice correcto (source, symbol, timeframe, timestamp)
            query = """
                INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume, broker, source)
                VALUES %s
                ON CONFLICT (source, symbol, timeframe, timestamp) DO NOTHING
            """
            
            execute_values(cur, query, values)
            conn.commit()
            
            inserted = cur.rowcount
            cur.close()
            conn.close()
            
            print(f"💾 Guardadas {inserted} velas nuevas para {symbol} {timeframe}")
            return inserted
            
        except Exception as e:
            print(f"❌ Error guardando velas: {e}")
            return 0
    
    def update_from_api(self, api_client, symbol, timeframe, limit=200, source='iqoption'):
        """
        Actualizar velas desde API y guardar en BD
        """
        try:
            # Obtener velas desde API
            candles = api_client.get_candles(symbol, timeframe, limit)
            
            if candles:
                # Guardar en BD con la fuente correcta
                self.save_candles(symbol, timeframe, candles, broker=source, source=source)
                return candles
            
            return []
            
        except Exception as e:
            print(f"❌ Error actualizando velas desde API: {e}")
            return []
    
    def get_latest_timestamp(self, symbol, timeframe, source='iqoption'):
        """Obtener timestamp de la última vela guardada"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            
            query = """
                SELECT MAX(timestamp)
                FROM candles
                WHERE source = %s AND symbol = %s AND timeframe = %s
            """
            
            cur.execute(query, (source, symbol, timeframe))
            result = cur.fetchone()
            
            cur.close()
            conn.close()
            
            return result[0] if result[0] else 0
            
        except Exception as e:
            print(f"❌ Error obteniendo último timestamp: {e}")
            return 0


# Instancia global
candle_service = CandleService()
