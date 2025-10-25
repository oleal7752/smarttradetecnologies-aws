#!/usr/bin/env python3
"""
Script para llenar la base de datos con datos históricos de mercado usando yfinance
"""

import yfinance as yf
from datetime import datetime, timedelta
from database import get_db
from sqlalchemy import text
import sys

# Mapeo de símbolos
SYMBOL_MAP = {
    'GOLD': {
        'ticker': 'GC=F',  # Gold Futures
        'db_symbol': 'XAUUSD-OTC'
    },
    'EURUSD': {
        'ticker': 'EURUSD=X',
        'db_symbol': 'EURUSD-OTC'
    },
    'EURJPY': {
        'ticker': 'EURJPY=X',
        'db_symbol': 'EURJPY-OTC'
    }
}

def download_and_save_candles(symbol_key, days=60):
    """
    Descarga datos históricos de yfinance y los guarda en la base de datos
    
    Args:
        symbol_key: Clave del símbolo (GOLD, EURUSD, EURJPY)
        days: Número de días a descargar (máximo 60 para 5min)
    """
    
    if symbol_key not in SYMBOL_MAP:
        print(f"❌ Símbolo no soportado: {symbol_key}")
        return 0
    
    config = SYMBOL_MAP[symbol_key]
    ticker = config['ticker']
    db_symbol = config['db_symbol']
    
    print(f"\n📊 Descargando {symbol_key} ({ticker})...")
    print(f"   Período: últimos {days} días")
    print(f"   Intervalo: 5 minutos (M5)")
    
    try:
        # Descargar datos de yfinance
        data = yf.download(
            tickers=ticker,
            period=f"{days}d",
            interval="5m",
            progress=False
        )
        
        if data.empty:
            print(f"❌ No se obtuvieron datos para {symbol_key}")
            return 0
        
        print(f"✅ Descargadas {len(data)} velas")
        
        # Guardar en la base de datos
        with get_db() as db:
            # Obtener timestamps existentes de una vez
            all_timestamps = [int(index.timestamp()) for index in data.index]
            timestamps_str = ','.join(map(str, all_timestamps))
            
            existing_query = text(f"""
                SELECT timestamp FROM candles 
                WHERE symbol = :symbol 
                AND timeframe = :timeframe 
                AND source = :source
                AND timestamp IN ({timestamps_str})
            """)
            
            existing_timestamps = set(
                row[0] for row in db.execute(existing_query, {
                    'symbol': db_symbol,
                    'timeframe': 'M5',
                    'source': 'yfinance'
                }).fetchall()
            )
            
            # Preparar datos para inserción
            candles_to_insert = []
            skipped_count = 0
            
            for index, row in data.iterrows():
                timestamp = int(index.timestamp())
                
                if timestamp in existing_timestamps:
                    skipped_count += 1
                    continue
                
                candles_to_insert.append({
                    'symbol': db_symbol,
                    'timeframe': 'M5',
                    'timestamp': timestamp,
                    'open': float(row['Open'].iloc[0]) if hasattr(row['Open'], 'iloc') else float(row['Open']),
                    'high': float(row['High'].iloc[0]) if hasattr(row['High'], 'iloc') else float(row['High']),
                    'low': float(row['Low'].iloc[0]) if hasattr(row['Low'], 'iloc') else float(row['Low']),
                    'close': float(row['Close'].iloc[0]) if hasattr(row['Close'], 'iloc') else float(row['Close']),
                    'volume': float(row['Volume'].iloc[0]) if 'Volume' in row and hasattr(row['Volume'], 'iloc') else 0,
                    'broker': 'yahoo',
                    'source': 'yfinance'
                })
            
            # Insertar todas las velas
            if candles_to_insert:
                insert_query = text("""
                    INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume, broker, source)
                    VALUES (:symbol, :timeframe, :timestamp, :open, :high, :low, :close, :volume, :broker, :source)
                """)
                db.execute(insert_query, candles_to_insert)
                db.commit()
                
            saved_count = len(candles_to_insert)
            print(f"✅ {symbol_key}: {saved_count} velas guardadas, {skipped_count} ya existían")
            return saved_count
            
    except Exception as e:
        print(f"❌ Error descargando {symbol_key}: {e}")
        return 0

def fill_all_symbols(days=60):
    """Llena todos los símbolos con datos históricos"""
    print("=" * 60)
    print("📈 LLENANDO BASE DE DATOS CON DATOS DE MERCADO")
    print("=" * 60)
    
    total_saved = 0
    
    for symbol in SYMBOL_MAP.keys():
        saved = download_and_save_candles(symbol, days)
        total_saved += saved
    
    print("\n" + "=" * 60)
    print(f"✅ COMPLETADO: {total_saved} velas guardadas en total")
    print("=" * 60)

if __name__ == "__main__":
    # Por defecto descarga 60 días (máximo para 5min en yfinance)
    days = 60
    
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
            if days > 60:
                print("⚠️ Máximo 60 días para intervalo 5min, usando 60")
                days = 60
        except ValueError:
            print("⚠️ Argumento inválido, usando 60 días por defecto")
    
    fill_all_symbols(days)
