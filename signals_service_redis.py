#!/usr/bin/env python3
"""
signals_service_redis.py - Mejorado
Genera señales cada 10 segundos con mejor logging
"""
import time, json, uuid, os
from redis import Redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0")
r = Redis.from_url(REDIS_URL, decode_responses=True)

def enqueue_signal(symbol, action, confidence=0.5, meta=None):
    """Genera una señal y la encola en Redis"""
    payload = {
        "id": f"signal_{int(time.time())}_{uuid.uuid4().hex[:6]}",
        "symbol": symbol,
        "action": action,
        "confidence": float(confidence),
        "meta": meta or {},
        "created_at": int(time.time()),
        "candle_unix": int(time.time()) - (int(time.time()) % 300),  # Tiempo de vela alineado
        "timeframe": "M5",
        "price": 1.16712 + ((int(time.time()) % 100 - 50) * 0.00001)  # Precio simulado
    }
    
    r.rpush("signals", json.dumps(payload))
    print(f"[SIGNALS] Enqueued {payload['id']} - {action} {symbol} @ {payload['price']}")
    return payload

def main_loop():
    """Bucle principal que genera señales cada 10 segundos"""
    symbols = ["EURUSD-OTC"]
    idx = 0
    
    print(f"[SIGNALS] Starting signal generator, Redis: {REDIS_URL}")
    
    try:
        while True:
            symbol = symbols[idx % len(symbols)]
            action = "BUY" if (idx % 2 == 0) else "SELL"
            
            enqueue_signal(
                symbol=symbol, 
                action=action, 
                confidence=0.8, 
                meta={"source": "demo", "generator": "signals_service"}
            )
            
            idx += 1
            time.sleep(10)  # Esperar 10 segundos
            
    except KeyboardInterrupt:
        print("\n[SIGNALS] Service stopped by user")
    except Exception as e:
        print(f"[SIGNALS] Error: {e}")

if __name__ == "__main__":
    main_loop()