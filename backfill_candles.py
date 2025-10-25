"""
Backfill simple: trae N velas M5 desde IQ Option y las guarda en Redis con candles_store.
Ajusta la importación de tu cliente IQ_Option según tu proyecto.
"""

import os, time
from candles_store import store_batch

# IMPORTANTE: ajusta este import a tu cliente real
# from iqoptionapi.stable_api import IQ_Option

SYMBOLS = os.getenv("IQ_SYMBOLS", "EURUSD-OTC,GBPUSD-OTC,USDJPY-OTC,EURJPY-OTC").split(",")
TIMEFRAME = "M5"
COUNT = int(os.getenv("BACKFILL_COUNT", "200"))

def fetch_from_iq(symbol: str, count: int = COUNT):
    # Reemplaza esta función para usar tu cliente real (ya logueado)
    # Debe devolver una lista de dicts con open/high/low/close/from/to/volume
    raise NotImplementedError("Implementa fetch_from_iq con tu cliente existente")

def main():
    for sym in SYMBOLS:
        print(f"[BACKFILL] {sym} {TIMEFRAME} solicitando {COUNT} velas...")
        candles = fetch_from_iq(sym.strip(), COUNT)
        info = store_batch(sym.strip(), TIMEFRAME, candles)
        print(f"[BACKFILL] {sym} -> {info}")

if __name__ == "__main__":
    main()