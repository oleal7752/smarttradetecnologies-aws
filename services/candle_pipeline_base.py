"""
Clase base abstracta para pipelines de velas
Define la interfaz común para todos los pipelines (Finnhub, IQ Option, OlympTrade)
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import psycopg2
import os
from services.candle_utils import CandleNormalizer, CandleFilter, TimeframeHelper

class CandlePipelineBase(ABC):
    """Clase base para pipelines de velas"""
    
    def __init__(self, source: str):
        self.source = source
        self.normalizer = CandleNormalizer()
        self.filter = CandleFilter()
        self.timeframe_helper = TimeframeHelper()
        self.db_url = os.getenv('DATABASE_URL')
    
    @abstractmethod
    def fetch_candles(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """
        Obtiene velas de la fuente externa
        Debe ser implementado por cada pipeline específico
        """
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene precio actual del símbolo
        Debe ser implementado por cada pipeline específico
        """
        pass
    
    def normalize_candles(self, raw_candles: List[Dict]) -> List[Dict]:
        """Normaliza velas al formato estándar"""
        normalized = []
        for candle in raw_candles:
            try:
                normalized_candle = self.normalizer.normalize(candle, self.source)
                if self.normalizer.validate(normalized_candle):
                    normalized.append(normalized_candle)
            except Exception as e:
                print(f"⚠️ Error normalizando vela: {e}")
        return normalized
    
    def persist_candles(self, symbol: str, timeframe: str, candles: List[Dict]) -> int:
        """
        Persiste velas en PostgreSQL con source específico
        Retorna número de velas insertadas
        """
        if not candles:
            return 0
        
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            inserted = 0
            for candle in candles:
                try:
                    cursor.execute("""
                        INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume, source, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (source, symbol, timeframe, timestamp) DO NOTHING
                    """, (
                        symbol,
                        timeframe,
                        candle['time'],
                        candle['open'],
                        candle['high'],
                        candle['low'],
                        candle['close'],
                        candle.get('volume', 0),
                        self.source
                    ))
                    inserted += cursor.rowcount
                except Exception as e:
                    print(f"⚠️ Error insertando vela: {e}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            if inserted > 0:
                print(f"✅ {self.source.upper()}: {inserted} velas guardadas en DB ({symbol} {timeframe})")
            
            return inserted
            
        except Exception as e:
            print(f"❌ Error persistiendo velas {self.source}: {e}")
            return 0
    
    def get_candles_from_db(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        """Obtiene velas desde PostgreSQL filtrando por source"""
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, open, high, low, close, volume
                FROM candles
                WHERE symbol = %s AND timeframe = %s AND source = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (symbol, timeframe, self.source, limit))
            
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
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
            
            candles = self.filter.sort_by_time(candles, ascending=True)
            
            if candles:
                print(f"✅ {self.source.upper()}: {len(candles)} velas desde DB ({symbol} {timeframe})")
            
            return candles
            
        except Exception as e:
            print(f"❌ Error leyendo desde DB {self.source}: {e}")
            return []
    
    def get_candles(self, symbol: str, timeframe: str, limit: int = 200, use_cache: bool = True) -> List[Dict]:
        """
        Pipeline completo: fetch -> normalize -> persist -> return
        
        Args:
            symbol: Símbolo a obtener
            timeframe: Timeframe de las velas
            limit: Número máximo de velas
            use_cache: Si True, intenta obtener desde DB primero
        
        Returns:
            Lista de velas normalizadas
        """
        if use_cache:
            cached_candles = self.get_candles_from_db(symbol, timeframe, limit)
            if cached_candles:
                return cached_candles
        
        raw_candles = self.fetch_candles(symbol, timeframe, limit)
        if not raw_candles:
            print(f"⚠️ {self.source.upper()}: No se obtuvieron velas de la API para {symbol}")
            return []
        
        normalized = self.normalize_candles(raw_candles)
        
        normalized = self.filter.remove_duplicates(normalized)
        normalized = self.filter.sort_by_time(normalized)
        normalized = self.filter.limit_candles(normalized, limit)
        
        if normalized:
            self.persist_candles(symbol, timeframe, normalized)
        
        return normalized
